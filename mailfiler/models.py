from email.policy import default
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

class GraphUser(models.Model):
    graph_user_id = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    email = models.CharField(max_length=100)
    timezone = models.CharField(max_length=100)

class Mail(models.Model):
    immutableId = models.CharField(max_length=266)
    subject = models.CharField(max_length=266)
    bodyPreview = models.CharField(max_length=266)
    sender = models.CharField(max_length=266)
    to = models.CharField(max_length=266, default='')
    receivedDateTime = models.DateTimeField()
    user = models.ForeignKey(GraphUser, on_delete=models.CASCADE)
    mail_type = models.CharField(max_length=266, default='inbox')

    @classmethod
    def create(cls, immutableId, subject, bodyPreview, sender, receivedDateTime):
        mail = cls(immutableId=immutableId, subject=subject, bodyPreview=bodyPreview, sender=sender, receivedDateTime=receivedDateTime)
        # do something with the book
        return mail

class Attachment(models.Model):
    immutableId = models.CharField(max_length=266)
    name = models.CharField(max_length=266)
    contentType = models.CharField(max_length=266)
    size = models.IntegerField()
    mail = models.ForeignKey(Mail, on_delete=models.CASCADE)

class Connect(models.Model):
    token_cache = models.CharField(max_length=13000)
    microsoft_user_id = models.CharField(max_length=50)
    user = models.ForeignKey(GraphUser, on_delete=models.CASCADE)
