from django.contrib import messages
from django.shortcuts import redirect


def user_has_role(user, roles):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=roles).exists()


def is_student(user):
    return user_has_role(user, ['student'])


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
            if sno and request.user.username != sno:
                messages.error(request, '无权限访问')
                return redirect('/')
        return super().dispatch(request, *args, **kwargs)
