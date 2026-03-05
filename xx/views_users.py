from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group, User
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView

from .forms import UserCreateInputForm, UserEditInputForm
from .models import cl, student
from .permissions import RoleRequiredMixin
from .view_shared import (
    DEFAULT_STUDENT_PASSWORD,
    MANAGED_ROLES,
    empty_user_form,
    flash_form_errors,
    get_managed_roles,
    managed_groups,
    upsert_student_profile_from_data,
    user_form_from_request,
)


class UserListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = User
    template_name = 'user_list.html'
    context_object_name = 'users'
    paginate_by = 20
    allowed_roles = ('admin',)

    def get_queryset(self):
        queryset = User.objects.all().prefetch_related('groups').order_by('username')

        keyword = self.request.GET.get('q', '').strip()
        role = self.request.GET.get('role', '').strip()

        if keyword:
            queryset = queryset.filter(
                Q(username__icontains=keyword) | Q(first_name__icontains=keyword)
            )
        if role:
            queryset = queryset.filter(groups__name=role).distinct()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        users = list(context['users'])

        usernames = [u.username for u in users]
        student_set = set(
            student.objects.filter(user__username__in=usernames).values_list('user__username', flat=True)
        )
        context['user_rows'] = [{'user': u, 'has_student': u.username in student_set} for u in users]
        context['roles'] = MANAGED_ROLES
        context['q'] = self.request.GET.get('q', '').strip()
        context['role'] = self.request.GET.get('role', '').strip()
        return context


class UserCreateView(LoginRequiredMixin, RoleRequiredMixin, View):
    template_name = 'user_form.html'
    allowed_roles = ('admin',)

    def get(self, request):
        return render(request, self.template_name, {
            'user_obj': None,
            'groups': managed_groups(ensure_exists=True),
            'classes': cl.objects.all(),
            'empty_form': empty_user_form(),
            'student_profile': None,
            'selected_role': '',
        })

    def post(self, request):
        form = UserCreateInputForm(request.POST)
        if not form.is_valid():
            flash_form_errors(request, form)
            return self._render_with_data(request)

        username = form.cleaned_data['username'].strip()
        nickname = form.cleaned_data['nickname'].strip()
        selected_role = form.cleaned_data['groups']
        create_student = form.cleaned_data['create_student']
        password1 = form.cleaned_data['final_password']

        if User.objects.filter(username=username).exists():
            messages.error(request, '用户名已存在')
            return self._render_with_data(request)

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    password=password1,
                    first_name=nickname,
                )
                role_group, _ = Group.objects.get_or_create(name=selected_role)
                user.groups.add(role_group)
                if create_student:
                    upsert_student_profile_from_data(form.cleaned_data, user)

            if selected_role == 'student':
                messages.success(request, f'用户创建成功，学生初始密码为 {DEFAULT_STUDENT_PASSWORD}')
            else:
                messages.success(request, '用户创建成功')
            return redirect('user_list')
        except ValueError as exc:
            messages.error(request, str(exc))
            return self._render_with_data(request)
        except Exception as exc:
            messages.error(request, f'创建失败：{str(exc)}')
            return self._render_with_data(request)

    def _render_with_data(self, request):
        form_data = user_form_from_request(request)
        return render(request, self.template_name, {
            'user_obj': None,
            'groups': managed_groups(ensure_exists=True),
            'classes': cl.objects.all(),
            'form': form_data,
            'empty_form': empty_user_form(),
            'selected_role': request.POST.getlist('groups')[0] if request.POST.getlist('groups') else '',
            'student_profile': None,
        })


class UserEditView(LoginRequiredMixin, RoleRequiredMixin, View):
    template_name = 'user_form.html'
    allowed_roles = ('admin',)

    def get(self, request, uid):
        user_obj = get_object_or_404(User, id=uid)
        student_profile = student.objects.filter(user=user_obj).first()
        if student_profile is None:
            student_profile = student.objects.filter(sno=user_obj.username).first()

        return render(request, self.template_name, {
            'user_obj': user_obj,
            'groups': managed_groups(ensure_exists=True),
            'classes': cl.objects.all(),
            'selected_role': user_obj.groups.filter(name__in=MANAGED_ROLES).values_list('name', flat=True).first() or '',
            'student_profile': student_profile,
            'empty_form': empty_user_form(),
        })

    def post(self, request, uid):
        user_obj = get_object_or_404(User, id=uid)
        form = UserEditInputForm(request.POST, user=user_obj)
        if not form.is_valid():
            flash_form_errors(request, form)
            return self._render_with_data(request, user_obj)

        nickname = form.cleaned_data['nickname'].strip()
        password1 = form.cleaned_data.get('password1') or ''
        selected_role = form.cleaned_data['groups']
        create_student = form.cleaned_data['create_student']
        previous_roles = set(get_managed_roles(user_obj))

        existing_profile = student.objects.filter(user=user_obj).first()
        if existing_profile is None:
            existing_profile = student.objects.filter(sno=user_obj.username).first()

        if selected_role == 'student' and not (create_student or existing_profile):
            messages.error(request, '学生角色必须关联学生档案')
            return self._render_with_data(request, user_obj)

        try:
            with transaction.atomic():
                user_obj.first_name = nickname
                if password1:
                    user_obj.set_password(password1)
                elif selected_role == 'student' and previous_roles != {'student'}:
                    user_obj.set_password(DEFAULT_STUDENT_PASSWORD)
                user_obj.save()

                user_obj.groups.clear()
                role_group, _ = Group.objects.get_or_create(name=selected_role)
                user_obj.groups.add(role_group)

                if create_student:
                    upsert_student_profile_from_data(form.cleaned_data, user_obj, existing_profile)

            messages.success(request, '用户更新成功')
            return redirect('user_list')
        except ValueError as exc:
            messages.error(request, str(exc))
            return self._render_with_data(request, user_obj)
        except Exception as exc:
            messages.error(request, f'更新失败：{str(exc)}')
            return self._render_with_data(request, user_obj)

    def _render_with_data(self, request, user_obj):
        return render(request, self.template_name, {
            'user_obj': user_obj,
            'groups': managed_groups(ensure_exists=True),
            'classes': cl.objects.all(),
            'form': user_form_from_request(request),
            'selected_role': request.POST.getlist('groups')[0] if request.POST.getlist('groups') else '',
            'student_profile': student.objects.filter(user=user_obj).first() or student.objects.filter(sno=user_obj.username).first(),
            'empty_form': empty_user_form(),
        })
