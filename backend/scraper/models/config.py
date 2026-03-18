from django.db import models

class Config(models.Model):
    config_id = models.AutoField(primary_key=True, unique=True)
    name = models.CharField(max_length=64)
    active = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')
    config_string = models.JSONField()
