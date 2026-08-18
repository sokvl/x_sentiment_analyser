import csv
import io

from django.conf import settings
from django.core.cache import cache
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from stocknlp.permissions import ActionPermissionsMixin, IsOwner, IsOwnerOrHasInterviewerKey
from ..models import UploadedFile
from ..serializers import UploadedFileSerializer
from ..services.csv_service import CSVProcessingService
from ..utils import get_data_manager


class UploadedFileViewSet(ActionPermissionsMixin, viewsets.ModelViewSet):
    """
    Curated CSV files that feed the signal-generation pipeline. Owner can
    upload/manage anything; the interviewer key can only list/preview/run
    files the owner has explicitly flagged as `is_interviewer_visible`.
    """
    queryset = UploadedFile.objects.all()
    serializer_class = UploadedFileSerializer
    http_method_names = ['get', 'post', 'patch', 'delete']

    action_permission_classes = {
        'list': [IsOwnerOrHasInterviewerKey],
        'retrieve': [IsOwnerOrHasInterviewerKey],
        'create': [IsOwner],
        'partial_update': [IsOwner],
        'destroy': [IsOwner],
        'preview': [IsOwnerOrHasInterviewerKey],
        'run': [IsOwnerOrHasInterviewerKey],
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        if IsOwner().has_permission(self.request, self):
            return queryset
        return queryset.filter(is_interviewer_visible=True)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        try:
            size = instance.file.size
            if size > settings.MAX_CSV_FILE_SIZE_BYTES:
                raise ValueError(
                    f"File too large ({size} bytes). "
                    f"Maximum allowed is {settings.MAX_CSV_FILE_SIZE_BYTES} bytes.",
                )

            with instance.file.open('rb') as f:
                content = f.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(content))
            fieldnames = reader.fieldnames or []
            missing = [
                col for col in CSVProcessingService.REQUIRED_COLUMNS
                if col not in fieldnames
            ]
            if missing:
                raise ValueError(f"Missing required columns: {', '.join(missing)}")

            row_count = sum(1 for _ in reader)
            if row_count > settings.MAX_CSV_ROWS:
                raise ValueError(f"Too many rows. Maximum allowed is {settings.MAX_CSV_ROWS}.")
        except ValueError as e:
            instance.delete()
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        instance.row_count = row_count
        instance.save(update_fields=['row_count'])

        return Response(self.get_serializer(instance).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        instance = self.get_object()
        try:
            n = int(request.query_params.get('rows', 20))
        except (TypeError, ValueError):
            return Response({'error': 'rows must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)

        with instance.file.open('rb') as f:
            reader = csv.DictReader(io.TextIOWrapper(f, encoding='utf-8'))
            rows = [row for _, row in zip(range(n), reader)]
            fieldnames = reader.fieldnames

        return Response({'fieldnames': fieldnames, 'rows': rows})

    @action(detail=True, methods=['get'])
    def run(self, request, pk=None):
        instance = self.get_object()
        model_id = request.query_params.get('model_id')

        cache_key = f"signals:file_output:{instance.file_id}:{model_id or 'default'}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        data_manager, error = get_data_manager()
        if not data_manager:
            return Response(
                {'error': 'DataManager not initialized', 'details': error},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            service = CSVProcessingService()
            with instance.file.open('rb') as f:
                results, errors = service.process(f, model_id=model_id)
            payload = {'results': results, 'errors': errors}
            cache.set(cache_key, payload, timeout=settings.CACHE_TTL_FILE_OUTPUT)
            return Response(payload)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {'error': 'Error processing CSV file', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
