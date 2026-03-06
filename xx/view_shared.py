from django.contrib.auth import get_user_model
from django.contrib import messages
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import (
    UserAccount,
    TeacherClassAssignment,
    TeacherCourseAssignment,
    cl,
    course,
    student,
)

MANAGED_ROLES = ('admin', 'teacher', 'student')
DEFAULT_STUDENT_PASSWORD = 'psw123456'
User = get_user_model()


def get_managed_roles(user):
    if not user or not user.is_authenticated:
        return []
    if user.is_superuser:
        return ['admin']
    return list(user.groups.filter(name__in=MANAGED_ROLES).values_list('name', flat=True))


def validate_password_or_raise(password, user=None):
    try:
        validate_password(password, user=user)
    except ValidationError as exc:
        raise ValueError('；'.join(exc.messages))


def managed_groups(ensure_exists=False):
    if ensure_exists:
        for group_name in MANAGED_ROLES:
            Group.objects.get_or_create(name=group_name)
    return Group.objects.filter(name__in=MANAGED_ROLES).order_by('name')


def ensure_account_profile(user, default_status=None):
    if user is None:
        return None

    if default_status is None:
        default_status = (
            UserAccount.STATUS_ACTIVE if get_managed_roles(user) else UserAccount.STATUS_PENDING
        )
    profile, created = UserAccount.objects.get_or_create(
        user=user,
        defaults={'status': default_status},
    )
    if created:
        sync_user_active_flag(user, profile.status)
    return profile


def sync_user_active_flag(user, status):
    expected = status != UserAccount.STATUS_DISABLED
    if user.is_active != expected:
        user.is_active = expected
        user.save(update_fields=['is_active'])


def set_account_status(user, status, reviewer=None, notes=''):
    profile = ensure_account_profile(user, default_status=status)
    profile.status = status
    profile.notes = notes
    profile.reviewed_by = reviewer
    profile.reviewed_at = timezone.now()
    profile.save(update_fields=['status', 'notes', 'reviewed_by', 'reviewed_at', 'updated_at'])
    sync_user_active_flag(user, status)
    return profile


def get_account_status(user):
    profile = ensure_account_profile(user)
    return profile.status if profile else UserAccount.STATUS_PENDING


def sync_teacher_assignments(user, class_qs=None, course_qs=None):
    class_ids = []
    course_ids = []
    if class_qs:
        class_ids = [obj.pk for obj in class_qs]
    if course_qs:
        course_ids = [obj.pk for obj in course_qs]

    TeacherClassAssignment.objects.filter(teacher=user).exclude(class_obj_id__in=class_ids).delete()
    TeacherCourseAssignment.objects.filter(teacher=user).exclude(course_obj_id__in=course_ids).delete()

    for class_id in class_ids:
        TeacherClassAssignment.objects.get_or_create(teacher=user, class_obj_id=class_id)
    for course_id in course_ids:
        TeacherCourseAssignment.objects.get_or_create(teacher=user, course_obj_id=course_id)


def clear_teacher_assignments(user):
    TeacherClassAssignment.objects.filter(teacher=user).delete()
    TeacherCourseAssignment.objects.filter(teacher=user).delete()


def ensure_student_user_account(sno, display_name=''):
    user = User.objects.filter(username=sno).first()
    student_group, _ = Group.objects.get_or_create(name='student')

    if user is None:
        user = User.objects.create_user(
            username=sno,
            password=DEFAULT_STUDENT_PASSWORD,
            first_name=display_name or sno,
        )
        user.groups.add(student_group)
        ensure_account_profile(user, default_status=UserAccount.STATUS_ACTIVE)
        sync_user_active_flag(user, UserAccount.STATUS_ACTIVE)
        return user, True

    managed_roles = set(get_managed_roles(user))
    if managed_roles and managed_roles != {'student'}:
        raise ValueError(f'学号 {sno} 已存在非学生角色账号，无法自动绑定')

    if 'student' not in managed_roles:
        user.set_password(DEFAULT_STUDENT_PASSWORD)
        user.save(update_fields=['password'])
        user.groups.add(student_group)

    if display_name and not user.first_name:
        user.first_name = display_name
        user.save(update_fields=['first_name'])

    set_account_status(user, UserAccount.STATUS_ACTIVE)

    return user, False


def user_form_from_request(request):
    return {
        'username': request.POST.get('username', ''),
        'nickname': request.POST.get('nickname', ''),
        'status': request.POST.get('status', UserAccount.STATUS_ACTIVE),
        'sname': request.POST.get('sname', ''),
        'sex': request.POST.get('sex', ''),
        'classno': request.POST.get('classno', ''),
        'native': request.POST.get('native', ''),
        'age': request.POST.get('age', ''),
        'semester': request.POST.get('semester', ''),
        'home': request.POST.get('home', ''),
        'telephone': request.POST.get('telephone', ''),
        'create_student': request.POST.get('create_student', ''),
        'teacher_classes': request.POST.getlist('teacher_classes'),
        'teacher_courses': request.POST.getlist('teacher_courses'),
    }


def empty_user_form():
    return {
        'username': '',
        'nickname': '',
        'status': UserAccount.STATUS_ACTIVE,
        'sname': '',
        'sex': '',
        'classno': '',
        'native': '',
        'age': '',
        'semester': '',
        'home': '',
        'telephone': '',
        'create_student': '',
        'teacher_classes': [],
        'teacher_courses': [],
    }


def flash_form_errors(request, form):
    for errors in form.errors.values():
        for error in errors:
            messages.error(request, str(error))


def upsert_student_profile_from_data(data, user, existing_profile=None):
    sname = (data.get('sname') or '').strip()
    class_obj = data.get('classno')

    if not sname or class_obj is None:
        raise ValueError('创建学生档案时，姓名和班级不能为空')

    if isinstance(class_obj, str):
        class_obj = cl.objects.get(classno=class_obj)

    if existing_profile is None:
        current_profile = student.objects.filter(user=user).first() or student.objects.filter(sno=user.username).first()
        if current_profile and current_profile.is_active:
            raise ValueError('学生档案已存在')
        existing_profile = current_profile or student(sno=user.username, user=user)
    elif existing_profile.user_id is None:
        existing_profile.user = user

    existing_profile.sno = user.username
    existing_profile.user = user
    existing_profile.sname = sname
    existing_profile.sex = data.get('sex') or 'girl'
    existing_profile.native = data.get('native') or ''
    existing_profile.age = data.get('age') or None
    existing_profile.classno = class_obj
    existing_profile.semester = data.get('semester') or None
    existing_profile.home = data.get('home') or ''
    existing_profile.telephone = data.get('telephone') or ''
    existing_profile.restore()
    existing_profile.save()
    return existing_profile
