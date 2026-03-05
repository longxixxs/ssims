from django.contrib.auth.models import User
from django.db import models


class depart(models.Model):
    dno = models.CharField(max_length=6, primary_key=True, null=False)
    dname = models.CharField(max_length=10, null=False)
    telephone = models.CharField(max_length=15, blank=True)


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
    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.CASCADE, related_name='student_profile')
    sname = models.CharField(max_length=10, null=False)
    sex = models.CharField(max_length=4, choices=stusex, default='girl')
    native = models.CharField(max_length=20, blank=True)
    age = models.IntegerField(null=True, blank=True)
    classno = models.ForeignKey(cl, on_delete=models.CASCADE)
    entime = models.DateTimeField(null=True, auto_now_add=True)
    semester = models.IntegerField(null=True, blank=True)
    home = models.CharField(max_length=40, blank=True)
    telephone = models.CharField(max_length=20, blank=True)


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

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['sno', 'cno'], name='uniq_student_course'),
        ]


class AuditLog(models.Model):
    ACTION_CREATE = 'create'
    ACTION_UPDATE = 'update'
    ACTION_DELETE = 'delete'
    ACTION_CHOICES = (
        (ACTION_CREATE, '新增'),
        (ACTION_UPDATE, '修改'),
        (ACTION_DELETE, '删除'),
    )

    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=64)
    object_repr = models.CharField(max_length=200)
    actor = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    actor_name = models.CharField(max_length=150, blank=True)
    ip = models.CharField(max_length=45, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
