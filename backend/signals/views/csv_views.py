import os
import tempfile
import threading
import time
import uuid

from django.conf import settings
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from stocknlp.permissions import IsOwnerOrHasInterviewerKey
from ..services.csv_service import CSVProcessingService, CSVProcessingTimeout
from ..utils import get_data_manager, log_and_get_safe_message


def _job_cache_key(job_id):
    return f'csv_job:{job_id}'


def _run_csv_job(job_id, file_path, model_id):
    cache.set(
        _job_cache_key(job_id),
        {'status': 'running', 'results': None, 'errors': None, 'error': None},
        timeout=settings.CSV_JOB_CACHE_TTL,
    )

    try:
        service = CSVProcessingService()
        deadline = time.monotonic() + settings.CSV_JOB_TIMEOUT_SECONDS
        with open(file_path, 'rb') as f:
            results, errors = service.process(f, model_id=model_id, deadline=deadline)
        cache.set(
            _job_cache_key(job_id),
            {'status': 'succeeded', 'results': results, 'errors': errors, 'error': None},
            timeout=settings.CSV_JOB_CACHE_TTL,
        )
    except CSVProcessingTimeout as e:
        results, errors = getattr(e, 'partial', ({}, []))
        cache.set(
            _job_cache_key(job_id),
            {'status': 'timed_out', 'results': results, 'errors': errors, 'error': str(e)},
            timeout=settings.CSV_JOB_CACHE_TTL,
        )
    except ValueError as e:
        cache.set(
            _job_cache_key(job_id),
            {'status': 'failed', 'results': None, 'errors': None, 'error': str(e)},
            timeout=settings.CSV_JOB_CACHE_TTL,
        )
    except Exception as e:
        message = log_and_get_safe_message(e, 'CSV processing failed')
        cache.set(
            _job_cache_key(job_id),
            {'status': 'failed', 'results': None, 'errors': None, 'error': message},
            timeout=settings.CSV_JOB_CACHE_TTL,
        )
    finally:
        try:
            os.remove(file_path)
        except OSError:
            pass


class ProcessCSVView(APIView):
    """
    Upload a CSV of tweets for batch LLM evaluation. Processing happens in a
    background thread; poll ProcessCSVJobStatusView with the returned job_id.
    """
    permission_classes = [IsOwnerOrHasInterviewerKey]

    def post(self, request):
        file = request.FILES.get('file')
        model_id = request.data.get('model_id')
        if not file or not file.name.endswith('.csv'):
            return Response(
                {'error': 'Invalid file format. Please upload a CSV file.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if file.size > settings.MAX_CSV_FILE_SIZE_BYTES:
            return Response(
                {
                    'error': f"File too large ({file.size} bytes). "
                             f"Maximum allowed is {settings.MAX_CSV_FILE_SIZE_BYTES} bytes.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        data_manager, error = get_data_manager()
        if not data_manager:
            return Response(
                {'error': 'DataManager not initialized', 'details': error},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        job_id = str(uuid.uuid4())
        fd, temp_path = tempfile.mkstemp(suffix='.csv')
        with os.fdopen(fd, 'wb') as dest:
            for chunk in file.chunks():
                dest.write(chunk)

        cache.set(
            _job_cache_key(job_id),
            {'status': 'pending', 'results': None, 'errors': None, 'error': None},
            timeout=settings.CSV_JOB_CACHE_TTL,
        )
        threading.Thread(
            target=_run_csv_job, args=(job_id, temp_path, model_id), daemon=True,
        ).start()

        return Response({'job_id': job_id}, status=status.HTTP_202_ACCEPTED)


class ProcessCSVJobStatusView(APIView):
    """
    Poll the status/result of a CSV processing job started via ProcessCSVView.
    """
    permission_classes = [IsOwnerOrHasInterviewerKey]

    def get(self, request, job_id):
        job = cache.get(_job_cache_key(job_id))
        if job is None:
            return Response(
                {'error': 'Unknown or expired job_id.'}, status=status.HTTP_404_NOT_FOUND,
            )
        return Response(job, status=status.HTTP_200_OK)
