from rest_framework import serializers
from ..models import UploadedFile

class UploadedFileSerializer(serializers.ModelSerializer):
    """Serializer for the UploadedFile model."""
    class Meta:
        model = UploadedFile
        fields = [
            'file_id', 'display_name', 'file',
            'is_interviewer_visible', 'uploaded_at', 'row_count',
        ]
        read_only_fields = ['file_id', 'uploaded_at', 'row_count']
