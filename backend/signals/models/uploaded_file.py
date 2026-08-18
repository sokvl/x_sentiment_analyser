from django.db import models


class UploadedFile(models.Model):
    file_id = models.AutoField(primary_key=True)
    display_name = models.CharField(max_length=128)
    file = models.FileField(upload_to='signals/uploaded_files/')
    is_interviewer_visible = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    row_count = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.display_name
