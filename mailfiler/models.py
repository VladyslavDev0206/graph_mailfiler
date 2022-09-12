from unittest.util import _MAX_LENGTH
from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()

# Create your models here.

class DropBox(models.Model):
    title = models.CharField(max_length=30)
    document = models.FileField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    class Meta:
        verbose_name_plural = 'Drop Boxes'

class Mail(models.Model):
    immutableId = models.CharField(max_length=266)
    subject = models.CharField(max_length=266)
    bodyPreview = models.CharField(max_length=266)
    sender = models.CharField(max_length=266)
    receivedDateTime = models.DateField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    @classmethod
    def create(cls, immutableId, subject, bodyPreview, sender, receivedDateTime):
        mail = cls(immutableId=immutableId, subject=subject, bodyPreview=bodyPreview, sender=sender, receivedDateTime=receivedDateTime)
        # do something with the book
        return mail