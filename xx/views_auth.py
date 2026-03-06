from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.shortcuts import redirect, render
from django.views import View

from .models import student
from .view_shared import (
    DEFAULT_STUDENT_PASSWORD,
    ensure_account_profile,
    ensure_student_user_account,
    get_account_status,
    get_managed_roles,
    sync_user_active_flag,
    validate_password_or_raise,
)


class UserLoginView(View):
    template_name = 'login.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        if not username or not password:
            messages.error(request, '用户名和密码不能为空')
            return render(request, self.template_name)

        user = authenticate(request, username=username, password=password)
        if user is None and password == DEFAULT_STUDENT_PASSWORD:
            legacy_student = student.objects.filter(sno=username).first()
            if legacy_student:
                try:
                    ensure_student_user_account(legacy_student.sno, legacy_student.sname)
                except ValueError:
                    pass
                user = authenticate(request, username=username, password=password)

        if user:
            ensure_account_profile(user)
            account_status = get_account_status(user)
            if account_status == 'pending':
                messages.warning(request, '账号待审核，请联系管理员完成审批')
                return redirect('login')
            if account_status == 'disabled':
                messages.error(request, '账号已停用，请联系管理员处理')
                return redirect('login')

            login(request, user)
            roles = get_managed_roles(user)
            if len(roles) > 1:
                messages.error(request, '账号角色配置异常，请联系管理员处理')
                logout(request)
                return redirect('login')
            if not roles:
                messages.error(request, '账号未分配角色，请联系管理员处理')
                logout(request)
                return redirect('login')

            role = roles[0]
            if role == 'student':
                stu = student.objects.filter(user=user).first()
                if stu is None:
                    stu = student.objects.filter(sno=user.username).first()
                if stu:
                    return redirect('student_detail', sno=stu.sno)
                messages.warning(request, '学生档案未创建，请联系管理员完善信息')
                logout(request)
                return redirect('login')

            if role in ('admin', 'teacher'):
                return redirect('dashboard')

            messages.error(request, '账号角色配置异常，请联系管理员处理')
            logout(request)
            return redirect('login')

        candidate = User.objects.filter(username=username).first()
        if candidate and candidate.check_password(password):
            ensure_account_profile(candidate)
            if get_account_status(candidate) == 'disabled':
                messages.error(request, '账号已停用，请联系管理员处理')
                return render(request, self.template_name)

        messages.error(request, '用户名或密码错误')
        return render(request, self.template_name)


class UserLogoutView(LoginRequiredMixin, View):
    http_method_names = ['post']

    def post(self, request):
        logout(request)
        return redirect('login')


class UserRegisterView(View):
    template_name = 'register.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        username = request.POST.get('username', '').strip()
        nickname = request.POST.get('nickname', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        if not all([username, nickname, password1, password2]):
            messages.error(request, '所有字段都不能为空')
            return render(request, self.template_name)
        if password1 != password2:
            messages.error(request, '两次密码不一致')
            return render(request, self.template_name)

        try:
            validate_password_or_raise(password1)
        except ValueError as exc:
            messages.error(request, str(exc))
            return render(request, self.template_name)

        if User.objects.filter(username=username).exists():
            messages.error(request, '用户名已存在')
            return render(request, self.template_name)

        user = User.objects.create_user(
            username=username,
            password=password1,
            first_name=nickname,
        )
        ensure_account_profile(user, default_status='pending')
        sync_user_active_flag(user, 'pending')
        messages.success(request, '注册成功，账号待管理员审核分配角色后方可登录')
        return redirect('login')


class UserPasswordView(LoginRequiredMixin, View):
    template_name = 'password.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        old = request.POST.get('old', '')
        new1 = request.POST.get('new1', '')
        new2 = request.POST.get('new2', '')

        if not request.user.check_password(old):
            messages.error(request, '原密码错误')
            return render(request, self.template_name)
        if new1 != new2:
            messages.error(request, '两次新密码不一致')
            return render(request, self.template_name)
        if len(new1) < 6:
            messages.error(request, '密码长度不能少于6位')
            return render(request, self.template_name)

        try:
            validate_password_or_raise(new1, user=request.user)
        except ValueError as exc:
            messages.error(request, str(exc))
            return render(request, self.template_name)

        request.user.set_password(new1)
        request.user.save()
        logout(request)
        messages.success(request, '密码修改成功，请重新登录')
        return redirect('login')
