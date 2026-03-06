from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group, User
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView

from .audit import log_action, serialize_instance
from .forms import UserCreateInputForm, UserEditInputForm
from .models import UserAccount, cl, course, student
from .permissions import RoleRequiredMixin
from .view_shared import (
    DEFAULT_STUDENT_PASSWORD,
    MANAGED_ROLES,
    clear_teacher_assignments,
    empty_user_form,
    ensure_account_profile,
    flash_form_errors,
    get_managed_roles,
    managed_groups,
    set_account_status,
    sync_teacher_assignments,
    upsert_student_profile_from_data,
    user_form_from_request,
)


def _student_profile_for_user(user_obj, include_inactive=True):
    queryset = student.objects.filter(user=user_obj)
    if not include_inactive:
        queryset = queryset.filter(is_active=True)
    profile = queryset.first()
    if profile is None:
        queryset = student.objects.filter(sno=user_obj.username)
        if not include_inactive:
            queryset = queryset.filter(is_active=True)
        profile = queryset.first()
    return profile


def serialize_user_for_audit(user_obj):
    profile = _student_profile_for_user(user_obj)
    account_profile = ensure_account_profile(user_obj)
    return {
        'id': user_obj.pk,
        'username': user_obj.username,
        'nickname': user_obj.first_name,
        'status': account_profile.status,
        'roles': list(user_obj.groups.filter(name__in=MANAGED_ROLES).values_list('name', flat=True)),
        'student_sno': profile.sno if profile else None,
        'teacher_classes': list(
            user_obj.teacher_class_assignments.values_list('class_obj__classno', flat=True)
        ),
        'teacher_courses': list(
            user_obj.teacher_course_assignments.values_list('course_obj__cno', flat=True)
        ),
    }


def _user_form_context(request, user_obj=None, form_data=None):
    student_profile = _student_profile_for_user(user_obj) if user_obj else None
    account_profile = ensure_account_profile(user_obj) if user_obj else None
    if form_data is None:
        form_data = empty_user_form()
        if user_obj:
            form_data = {
                'username': user_obj.username,
                'nickname': user_obj.first_name,
                'status': account_profile.status if account_profile else UserAccount.STATUS_PENDING,
                'sname': student_profile.sname if student_profile else '',
                'sex': student_profile.sex if student_profile else '',
                'classno': student_profile.classno_id if student_profile and student_profile.classno_id else '',
                'native': student_profile.native if student_profile else '',
                'age': student_profile.age if student_profile and student_profile.age is not None else '',
                'semester': student_profile.semester if student_profile and student_profile.semester is not None else '',
                'home': student_profile.home if student_profile else '',
                'telephone': student_profile.telephone if student_profile else '',
                'create_student': 'on' if student_profile and student_profile.is_active else '',
                'teacher_classes': list(
                    user_obj.teacher_class_assignments.values_list('class_obj_id', flat=True)
                ),
                'teacher_courses': list(
                    user_obj.teacher_course_assignments.values_list('course_obj_id', flat=True)
                ),
            }

    selected_role = ''
    if user_obj:
        selected_role = user_obj.groups.filter(name__in=MANAGED_ROLES).values_list('name', flat=True).first() or ''
    if request.POST.getlist('groups'):
        selected_role = request.POST.getlist('groups')[0]

    return {
        'user_obj': user_obj,
        'groups': managed_groups(ensure_exists=True),
        'classes': cl.objects.filter(is_active=True).order_by('classno'),
        'courses': course.objects.filter(is_active=True).order_by('cno'),
        'status_choices': UserAccount.STATUS_CHOICES,
        'form': form_data,
        'empty_form': empty_user_form(),
        'selected_role': selected_role,
        'student_profile': student_profile,
    }


class UserListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = User
    template_name = 'user_list.html'
    context_object_name = 'users'
    paginate_by = 20
    allowed_roles = ('admin',)

    def get_queryset(self):
        queryset = (
            User.objects.all()
            .prefetch_related(
                'groups',
                'teacher_class_assignments__class_obj',
                'teacher_course_assignments__course_obj',
            )
            .select_related('account_profile')
            .order_by('username')
        )

        keyword = self.request.GET.get('q', '').strip()
        role = self.request.GET.get('role', '').strip()
        status = self.request.GET.get('status', '').strip()

        if keyword:
            queryset = queryset.filter(
                Q(username__icontains=keyword) | Q(first_name__icontains=keyword)
            )
        if role:
            queryset = queryset.filter(groups__name=role).distinct()
        if status:
            queryset = queryset.filter(account_profile__status=status)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rows = []
        for user_obj in context['users']:
            ensure_account_profile(user_obj)
            profile = _student_profile_for_user(user_obj, include_inactive=False)
            rows.append({
                'user': user_obj,
                'status': user_obj.account_profile.status,
                'has_student': bool(profile),
                'teacher_class_count': user_obj.teacher_class_assignments.count(),
                'teacher_course_count': user_obj.teacher_course_assignments.count(),
            })
        context['user_rows'] = rows
        context['roles'] = MANAGED_ROLES
        context['status_choices'] = UserAccount.STATUS_CHOICES
        context['pending_count'] = UserAccount.objects.filter(status=UserAccount.STATUS_PENDING).count()
        context['q'] = self.request.GET.get('q', '').strip()
        context['role'] = self.request.GET.get('role', '').strip()
        context['status'] = self.request.GET.get('status', '').strip()
        return context


class PendingApprovalListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = User
    template_name = 'pending_approval_list.html'
    context_object_name = 'users'
    allowed_roles = ('admin',)

    def get_queryset(self):
        return (
            User.objects.filter(account_profile__status=UserAccount.STATUS_PENDING)
            .prefetch_related('groups')
            .select_related('account_profile')
            .order_by('username')
        )


class UserCreateView(LoginRequiredMixin, RoleRequiredMixin, View):
    template_name = 'user_form.html'
    allowed_roles = ('admin',)

    def get(self, request):
        return render(request, self.template_name, _user_form_context(request))

    def post(self, request):
        form = UserCreateInputForm(request.POST)
        if not form.is_valid():
            flash_form_errors(request, form)
            return render(request, self.template_name, _user_form_context(request, form_data=user_form_from_request(request)))

        username = form.cleaned_data['username'].strip()
        nickname = form.cleaned_data['nickname'].strip()
        selected_role = form.cleaned_data['groups']
        selected_status = form.cleaned_data['status']
        create_student = form.cleaned_data['create_student']
        teacher_classes = form.cleaned_data.get('teacher_classes')
        teacher_courses = form.cleaned_data.get('teacher_courses')
        password1 = form.cleaned_data['final_password']

        if User.objects.filter(username=username).exists():
            messages.error(request, '用户名已存在')
            return render(request, self.template_name, _user_form_context(request, form_data=user_form_from_request(request)))

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    password=password1,
                    first_name=nickname,
                )
                role_group, _ = Group.objects.get_or_create(name=selected_role)
                user.groups.add(role_group)
                set_account_status(user, selected_status, reviewer=request.user)

                if selected_role == 'teacher':
                    sync_teacher_assignments(user, teacher_classes, teacher_courses)
                else:
                    clear_teacher_assignments(user)

                if create_student:
                    student_profile = upsert_student_profile_from_data(form.cleaned_data, user)
                    log_action(request, 'create', student_profile, before=None, after=serialize_instance(student_profile))

                log_action(request, 'create', user, before=None, after=serialize_user_for_audit(user))

            if selected_role == 'student':
                messages.success(request, f'用户创建成功，学生初始密码为 {DEFAULT_STUDENT_PASSWORD}')
            else:
                messages.success(request, '用户创建成功')
            return redirect('user_list')
        except ValueError as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, f'创建失败：{str(exc)}')
        return render(request, self.template_name, _user_form_context(request, form_data=user_form_from_request(request)))


class UserEditView(LoginRequiredMixin, RoleRequiredMixin, View):
    template_name = 'user_form.html'
    allowed_roles = ('admin',)

    def get(self, request, uid):
        user_obj = get_object_or_404(User, id=uid)
        return render(request, self.template_name, _user_form_context(request, user_obj=user_obj))

    def post(self, request, uid):
        user_obj = get_object_or_404(User, id=uid)
        form = UserEditInputForm(request.POST, user=user_obj)
        if not form.is_valid():
            flash_form_errors(request, form)
            return render(
                request,
                self.template_name,
                _user_form_context(request, user_obj=user_obj, form_data=user_form_from_request(request)),
            )

        nickname = form.cleaned_data['nickname'].strip()
        password1 = form.cleaned_data.get('password1') or ''
        selected_role = form.cleaned_data['groups']
        selected_status = form.cleaned_data['status']
        create_student = form.cleaned_data['create_student']
        teacher_classes = form.cleaned_data.get('teacher_classes')
        teacher_courses = form.cleaned_data.get('teacher_courses')
        previous_roles = set(get_managed_roles(user_obj))

        existing_profile = _student_profile_for_user(user_obj)
        active_profile = _student_profile_for_user(user_obj, include_inactive=False)

        if selected_role == 'student' and not (create_student or active_profile):
            messages.error(request, '学生角色必须关联有效学生档案；如为已归档档案，请勾选“创建/恢复学生档案”')
            return render(
                request,
                self.template_name,
                _user_form_context(request, user_obj=user_obj, form_data=user_form_from_request(request)),
            )
        if selected_role != 'student' and active_profile is not None:
            messages.error(request, '当前账号仍关联有效学生档案，请先归档学生档案后再改为非学生角色')
            return render(
                request,
                self.template_name,
                _user_form_context(request, user_obj=user_obj, form_data=user_form_from_request(request)),
            )

        try:
            before_user = serialize_user_for_audit(user_obj)
            before_profile = serialize_instance(existing_profile) if create_student and existing_profile is not None else None

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

                set_account_status(user_obj, selected_status, reviewer=request.user)

                if selected_role == 'teacher':
                    sync_teacher_assignments(user_obj, teacher_classes, teacher_courses)
                else:
                    clear_teacher_assignments(user_obj)

                if create_student:
                    student_profile = upsert_student_profile_from_data(form.cleaned_data, user_obj, existing_profile)
                    profile_action = 'create' if before_profile is None else 'update'
                    log_action(
                        request,
                        profile_action,
                        student_profile,
                        before=before_profile,
                        after=serialize_instance(student_profile),
                    )

                log_action(request, 'update', user_obj, before=before_user, after=serialize_user_for_audit(user_obj))

            messages.success(request, '用户更新成功')
            return redirect('user_list')
        except ValueError as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, f'更新失败：{str(exc)}')

        return render(
            request,
            self.template_name,
            _user_form_context(request, user_obj=user_obj, form_data=user_form_from_request(request)),
        )
