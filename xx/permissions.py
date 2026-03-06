from django.contrib import messages
from django.shortcuts import redirect

from .models import TeacherClassAssignment, TeacherCourseAssignment, cl, course, student


def user_has_role(user, roles):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=roles).exists()


def is_student(user):
    return user_has_role(user, ['student'])


def is_teacher(user):
    return user_has_role(user, ['teacher'])


def teacher_class_ids(user):
    if not user or not user.is_authenticated:
        return []
    return list(
        TeacherClassAssignment.objects.filter(teacher=user, class_obj__is_active=True)
        .values_list('class_obj_id', flat=True)
    )


def teacher_course_ids(user):
    if not user or not user.is_authenticated:
        return []
    return list(
        TeacherCourseAssignment.objects.filter(teacher=user, course_obj__is_active=True)
        .values_list('course_obj_id', flat=True)
    )


def teacher_class_queryset(user):
    return cl.objects.filter(pk__in=teacher_class_ids(user), is_active=True).order_by('classno')


def teacher_course_queryset(user):
    return course.objects.filter(pk__in=teacher_course_ids(user), is_active=True).order_by('cno')


def filter_students_for_user(user, queryset=None):
    base_qs = queryset if queryset is not None else student.objects.all()
    if user.is_superuser or user_has_role(user, ['admin']):
        return base_qs
    if is_teacher(user):
        return base_qs.filter(classno_id__in=teacher_class_ids(user))
    return base_qs.none()


def teacher_can_access_student(user, stu):
    return bool(stu and stu.classno_id in teacher_class_ids(user))


def teacher_can_access_course(user, course_obj):
    return bool(course_obj and course_obj.pk in teacher_course_ids(user))


def teacher_can_manage_record(user, record):
    if record is None:
        return False
    return teacher_can_access_student(user, record.sno) and teacher_can_access_course(user, record.cno)


class RoleRequiredMixin:
    allowed_roles = ()

    def dispatch(self, request, *args, **kwargs):
        if user_has_role(request.user, self.allowed_roles):
            return super().dispatch(request, *args, **kwargs)
        messages.error(request, '无权限访问')
        return redirect('/')


class StudentSelfOnlyMixin:
    def dispatch(self, request, *args, **kwargs):
        if is_student(request.user):
            sno = kwargs.get('sno') or request.GET.get('sno')
            own_sno = None
            try:
                profile = request.user.student_profile
            except Exception:
                profile = None
            if profile:
                own_sno = profile.sno
            if own_sno is None:
                own_sno = request.user.username
            if sno and own_sno != sno:
                messages.error(request, '无权限访问')
                return redirect('/')
        return super().dispatch(request, *args, **kwargs)
