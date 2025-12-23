from django.contrib.auth.models import User
from django.db import models


class depart(models.Model):
    dno = models.CharField(max_length=6, primary_key=True, null=False)
    dname = models.CharField(max_length=10, null=False)
    telephone = models.CharField(max_length=6, )


class cl(models.Model):
    classno = models.CharField(max_length=6, primary_key=True, )
    classname = models.CharField(max_length=10, null=False)
    dno = models.ForeignKey(depart, on_delete=models.CASCADE)


class student(models.Model):
    stusex = (
        ('girl', '女'),
        ('boy', '男'),
    )
    sno = models.CharField(max_length=10, primary_key=True, null=False)
    sname = models.CharField(max_length=10, null=False)
    sex = models.CharField(max_length=4, choices=stusex, default='girl')
    native = models.CharField(max_length=20, )
    age = models.IntegerField(null=True)
    classno = models.ForeignKey(cl, on_delete=models.CASCADE)
    entime = models.DateTimeField(null=True, auto_now=True)
    semester = models.IntegerField(null=True)
    home = models.CharField(max_length=40, )
    telephone = models.CharField(max_length=20, )


class course(models.Model):
    coutype = (
        ('crc', '公共课'),
        ('bcim', '专业基础课'),
        ('spc', '专业课'),
        ('ocos', '选修课')
    )
    cno = models.CharField(max_length=3, primary_key=True, null=False)
    cname = models.CharField(max_length=20, null=False)
    lecture = models.FloatField(null=True)
    semester = models.IntegerField(null=True)
    credit = models.FloatField(null=True)
    type = models.CharField(max_length=10, null=True, choices=coutype, default='crc')


class sc(models.Model):
    sno = models.ForeignKey(student, on_delete=models.CASCADE)
    cno = models.ForeignKey(course, on_delete=models.CASCADE)
    grade = models.FloatField(null=True)
