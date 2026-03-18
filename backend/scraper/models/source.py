from django.db import models

class Source(models.Model):
    source_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=64, unique=True)
    base_url = models.URLField(blank=True)
    login_required = models.BooleanField(default=False)
    credentials_id = models.IntegerField(blank=True, null=True)
    category = models.CharField(max_length=32)

    def __str__(self):
        return self.name
