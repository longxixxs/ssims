from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.utils import timezone


class ArchiveMixin(models.Model):
    is_active = models.BooleanField(default=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def archive(self):
        self.is_active = False
        self.archived_at = timezone.now()

    def restore(self):
        self.is_active = True
        self.archived_at = None


class depart(ArchiveMixin):
    dno = models.CharField(max_length=6, primary_key=True, null=False)
    dname = models.CharField(max_length=10, null=False)
    telephone = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return f'{self.dname}({self.dno})'


class cl(ArchiveMixin):
    classno = models.CharField(max_length=6, primary_key=True, )
    classname = models.CharField(max_length=10, null=False)
    dno = models.ForeignKey(depart, on_delete=models.PROTECT)

    def __str__(self):
        return f'{self.classname}({self.classno})'


class student(ArchiveMixin):
    stusex = (
        ('girl', '女'),
        ('boy', '男'),
    )
    sno = models.CharField(max_length=10, primary_key=True, null=False)
    user = models.OneToOneField(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='student_profile',
    )
    sname = models.CharField(max_length=10, null=False)
    sex = models.CharField(max_length=4, choices=stusex, default='girl')
    native = models.CharField(max_length=20, blank=True)
    age = models.IntegerField(null=True, blank=True)
    classno = models.ForeignKey(cl, on_delete=models.PROTECT)
    entime = models.DateTimeField(null=True, auto_now_add=True)
    semester = models.IntegerField(null=True, blank=True)
    home = models.CharField(max_length=40, blank=True)
    telephone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f'{self.sname}({self.sno})'


class course(ArchiveMixin):
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

    def __str__(self):
        return f'{self.cname}({self.cno})'


class UserAccount(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_ACTIVE = 'active'
    STATUS_DISABLED = 'disabled'
    STATUS_CHOICES = (
        (STATUS_PENDING, '待审核'),
        (STATUS_ACTIVE, '启用'),
        (STATUS_DISABLED, '停用'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='account_profile')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_user_accounts',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    notes = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.username}:{self.status}'


class TeacherClassAssignment(models.Model):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teacher_class_assignments',
    )
    class_obj = models.ForeignKey(cl, on_delete=models.CASCADE, related_name='teacher_assignments')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['teacher', 'class_obj'], name='uniq_teacher_class_assignment'),
        ]

    def __str__(self):
        return f'{self.teacher.username}:{self.class_obj.classno}'


class TeacherCourseAssignment(models.Model):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teacher_course_assignments',
    )
    course_obj = models.ForeignKey(course, on_delete=models.CASCADE, related_name='teacher_assignments')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['teacher', 'course_obj'], name='uniq_teacher_course_assignment'),
        ]

    def __str__(self):
        return f'{self.teacher.username}:{self.course_obj.cno}'


class sc(models.Model):
    SELECTION_ACTIVE = 'active'
    SELECTION_DROPPED = 'dropped'
    SELECTION_STATUS_CHOICES = (
        (SELECTION_ACTIVE, '已选'),
        (SELECTION_DROPPED, '已退课'),
    )

    GRADE_PENDING = 'pending'
    GRADE_DRAFT = 'draft'
    GRADE_PUBLISHED = 'published'
    GRADE_RETAKE = 'retake'
    GRADE_STATUS_CHOICES = (
        (GRADE_PENDING, '待录入'),
        (GRADE_DRAFT, '草稿'),
        (GRADE_PUBLISHED, '已发布'),
        (GRADE_RETAKE, '重修中'),
    )

    sno = models.ForeignKey(student, on_delete=models.PROTECT)
    cno = models.ForeignKey(course, on_delete=models.PROTECT)
    grade = models.FloatField(null=True, blank=True)
    selection_status = models.CharField(
        max_length=20,
        choices=SELECTION_STATUS_CHOICES,
        default=SELECTION_ACTIVE,
    )
    grade_status = models.CharField(
        max_length=20,
        choices=GRADE_STATUS_CHOICES,
        default=GRADE_PENDING,
    )
    attempt_no = models.PositiveIntegerField(default=1)
    selected_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    dropped_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['sno', 'cno'], name='uniq_student_course'),
            models.CheckConstraint(
                check=Q(grade__isnull=True) | (Q(grade__gte=0) & Q(grade__lte=100)),
                name='sc_grade_between_0_100',
            ),
        ]

    def __str__(self):
        return f'{self.sno_id}-{self.cno_id}'


class SelectionHistory(models.Model):
    ACTION_SELECTED = 'selected'
    ACTION_DROPPED = 'dropped'
    ACTION_GRADE_SAVED = 'grade_saved'
    ACTION_GRADE_PUBLISHED = 'grade_published'
    ACTION_RETAKE_MARKED = 'retake_marked'
    ACTION_CHOICES = (
        (ACTION_SELECTED, '选课'),
        (ACTION_DROPPED, '退课'),
        (ACTION_GRADE_SAVED, '保存成绩'),
        (ACTION_GRADE_PUBLISHED, '发布成绩'),
        (ACTION_RETAKE_MARKED, '标记重修'),
    )

    record = models.ForeignKey(sc, on_delete=models.CASCADE, related_name='history')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='selection_histories',
    )
    actor_name = models.CharField(max_length=150, blank=True)
    before_selection_status = models.CharField(max_length=20, blank=True)
    after_selection_status = models.CharField(max_length=20, blank=True)
    before_grade_status = models.CharField(max_length=20, blank=True)
    after_grade_status = models.CharField(max_length=20, blank=True)
    before_grade = models.FloatField(null=True, blank=True)
    after_grade = models.FloatField(null=True, blank=True)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']


class StudentImportJob(models.Model):
    MODE_CREATE = 'create'
    MODE_UPDATE = 'update'
    MODE_CHOICES = (
        (MODE_CREATE, '新增模式'),
        (MODE_UPDATE, '更新模式'),
    )

    STATUS_PREVIEWED = 'previewed'
    STATUS_APPLIED = 'applied'
    STATUS_CHOICES = (
        (STATUS_PREVIEWED, '已预检'),
        (STATUS_APPLIED, '已导入'),
    )

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='student_import_jobs',
    )
    mode = models.CharField(max_length=20, choices=MODE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PREVIEWED)
    preview_rows = models.JSONField(default=list, blank=True)
    error_rows = models.JSONField(default=list, blank=True)
    summary = models.JSONField(default=dict, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'import:{self.id}:{self.mode}:{self.status}'


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
