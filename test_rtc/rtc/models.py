from django.db import models

# Create your models here.

class Users(models.Model):
    Username = models.CharField(max_length=20)
    Password = models.CharField(max_length=30)
    UserExamId = models.CharField(max_length=6)
    
class Exams(models.Model):
    ExamId = models.CharField(max_length=6)
    ExamFile = models.CharField(max_length=100)