from django.db import models

class Content(models.Model):
    """Raw article / tweet text."""
    content_id = models.AutoField(primary_key=True)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['created_at'])]
