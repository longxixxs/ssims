from datetime import datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import Avg, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView, ListView
from openpyxl import Workbook, load_workbook

from .audit import log_action, serialize_instance
from .forms import StudentAddForm, StudentEditForm
from .models import cl, sc, student
from .permissions import RoleRequiredMixin, StudentSelfOnlyMixin
from .view_shared import DEFAULT_STUDENT_PASSWORD, ensure_student_user_account, flash_form_errors


class StudentListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = student
    template_name = 'student_list.html'
    context_object_name = 'students'
    paginate_by = 10
    allowed_roles = ('admin', 'teacher')

    def get_queryset(self):
        queryset = student.objects.select_related('classno', 'classno__dno')

        sno = self.request.GET.get('sno', '').strip()
        sname = self.request.GET.get('sname', '').strip()
        sex = self.request.GET.get('sex', '').strip()
        classno = self.request.GET.get('classno', '').strip()

        if sno:
            queryset = queryset.filter(sno__icontains=sno)
        if sname:
            queryset = queryset.filter(sname__icontains=sname)
        if sex:
            queryset = queryset.filter(sex=sex)
        if classno:
            queryset = queryset.filter(classno__classno=classno)

        order = self.request.GET.get('order', 'sno')
        direction = self.request.GET.get('direction', 'asc')
        order_map = {
            'sno': 'sno',
            'sname': 'sname',
            'age': 'age',
            'classno': 'classno__classno',
            'semester': 'semester',
        }

        order_field = order_map.get(order, 'sno')
        if direction == 'desc':
            order_field = '-' + order_field

        return queryset.order_by(order_field)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()

        context['classes'] = cl.objects.all()
        context['result_count'] = queryset.count()
        query_params = self.request.GET.copy()
        if 'page' in query_params:
            del query_params['page']
        context['query_string'] = query_params.urlencode()
        context['boy_count'] = queryset.filter(sex='boy').count()
        context['girl_count'] = queryset.filter(sex='girl').count()
        context['class_count'] = queryset.values('classno').distinct().count()
        context['order'] = self.request.GET.get('order', 'sno')
        context['direction'] = self.request.GET.get('direction', 'asc')
        return context


class StudentAddView(LoginRequiredMixin, RoleRequiredMixin, View):
    template_name = 'student_form.html'
    allowed_roles = ('admin',)

    def get(self, request):
        return render(request, self.template_name, {'classes': cl.objects.all()})

    def post(self, request):
        form = StudentAddForm(request.POST)
        if not form.is_valid():
            flash_form_errors(request, form)
            return render(request, self.template_name, {'classes': cl.objects.all()})

        try:
            sno = form.cleaned_data['sno'].strip()
            sname = form.cleaned_data['sname'].strip()
            class_obj = form.cleaned_data['classno']

            if student.objects.filter(sno=sno).exists():
                messages.error(request, f'学号 {sno} 已存在')
                return render(request, self.template_name, {'classes': cl.objects.all()})

            matched_user, account_created = ensure_student_user_account(sno, sname)
            if student.objects.filter(user=matched_user).exists():
                messages.error(request, f'账号 {sno} 已绑定其他学生档案')
                return render(request, self.template_name, {'classes': cl.objects.all()})

            stu = student.objects.create(
                sno=sno,
                user=matched_user,
                sname=sname,
                sex=form.cleaned_data.get('sex') or 'girl',
                native=form.cleaned_data.get('native') or '',
                age=form.cleaned_data.get('age') or None,
                classno=class_obj,
                semester=form.cleaned_data.get('semester') or None,
                home=form.cleaned_data.get('home') or '',
                telephone=form.cleaned_data.get('telephone') or '',
            )
            log_action(request, 'create', stu, before=None, after=serialize_instance(stu))
            if account_created:
                messages.success(request, f'添加成功，学生初始密码为 {DEFAULT_STUDENT_PASSWORD}')
            else:
                messages.success(request, '添加成功')
            return redirect('student_list')
        except Exception as exc:
            messages.error(request, f'添加失败：{str(exc)}')
            return render(request, self.template_name, {'classes': cl.objects.all()})


class StudentEditView(LoginRequiredMixin, RoleRequiredMixin, View):
    template_name = 'student_form.html'
    allowed_roles = ('admin',)

    def get(self, request, sno):
        stu = get_object_or_404(student, sno=sno)
        return render(request, self.template_name, {'stu': stu, 'classes': cl.objects.all()})

    def post(self, request, sno):
        stu = get_object_or_404(student, sno=sno)
        form = StudentEditForm(request.POST)
        if not form.is_valid():
            flash_form_errors(request, form)
            return render(request, self.template_name, {'stu': stu, 'classes': cl.objects.all()})

        try:
            before = serialize_instance(stu)
            stu.sname = form.cleaned_data['sname'].strip()
            stu.sex = form.cleaned_data.get('sex') or 'girl'
            stu.native = form.cleaned_data.get('native') or ''
            stu.age = form.cleaned_data.get('age') or None
            stu.classno = form.cleaned_data['classno']
            stu.semester = form.cleaned_data.get('semester') or None
            stu.home = form.cleaned_data.get('home') or ''
            stu.telephone = form.cleaned_data.get('telephone') or ''
            stu.save()

            log_action(request, 'update', stu, before=before, after=serialize_instance(stu))
            messages.success(request, '修改成功')
            return redirect('student_list')
        except Exception as exc:
            messages.error(request, f'修改失败：{str(exc)}')
            return render(request, self.template_name, {'stu': stu, 'classes': cl.objects.all()})


class StudentDeleteView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ('admin',)
    http_method_names = ['post']

    def post(self, request, sno):
        stu = get_object_or_404(student, sno=sno)
        before = serialize_instance(stu)
        bound_user = stu.user
        stu.delete()
        if bound_user:
            student_group = Group.objects.filter(name='student').first()
            if student_group:
                bound_user.groups.remove(student_group)
        log_action(request, 'delete', stu, before=before, after=None)
        messages.success(request, '删除成功')
        return redirect('student_list')


class StudentDetailView(LoginRequiredMixin, RoleRequiredMixin, StudentSelfOnlyMixin, DetailView):
    model = student
    template_name = 'student_detail.html'
    context_object_name = 'stu'
    pk_url_kwarg = 'sno'
    allowed_roles = ('admin', 'teacher', 'student')

    def get_object(self):
        return get_object_or_404(student, sno=self.kwargs['sno'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stu = self.get_object()

        records = sc.objects.select_related('cno').filter(sno=stu)
        graded_records = records.filter(grade__isnull=False)
        total_credit = graded_records.aggregate(total=Sum('cno__credit'))['total'] or 0
        avg_grade = graded_records.aggregate(avg=Avg('grade'))['avg']
        passed_credit = graded_records.filter(grade__gte=60).aggregate(total=Sum('cno__credit'))['total'] or 0

        context['courses'] = records
        context['total_credit'] = round(total_credit, 1)
        context['passed_credit'] = round(passed_credit, 1)
        context['avg_grade'] = round(avg_grade, 1) if avg_grade else None
        context['graded_count'] = graded_records.count()
        return context


class StudentImportExcelView(LoginRequiredMixin, RoleRequiredMixin, View):
    template_name = 'student_import_excel.html'
    allowed_roles = ('admin',)

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            messages.error(request, '请选择 Excel 文件')
            return redirect('student_import_excel')
        if not file.name.endswith('.xlsx'):
            messages.error(request, '仅支持 .xlsx 文件')
            return redirect('student_import_excel')

        try:
            wb = load_workbook(file)
            ws = wb.active
            headers = [str(cell.value).strip() if cell.value is not None else '' for cell in ws[1]]
            required_headers = [
                'sno', 'sname', 'sex', 'native', 'age',
                'classno', 'semester', 'home', 'telephone',
            ]

            if set(headers) != set(required_headers) or len(headers) != len(required_headers):
                messages.error(request, 'Excel 表头格式不正确，应为：' + ', '.join(required_headers))
                return redirect('student_import_excel')

            success = 0
            created_accounts = 0
            errors = []
            for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                try:
                    data = dict(zip(headers, row))
                    if not data.get('sno'):
                        continue

                    with transaction.atomic():
                        if student.objects.filter(sno=data['sno']).exists():
                            raise ValueError('学号已存在')
                        class_obj = cl.objects.get(classno=data['classno'])

                        matched_user, account_created = ensure_student_user_account(
                            str(data['sno']),
                            str(data.get('sname') or ''),
                        )
                        if student.objects.filter(user=matched_user).exists():
                            raise ValueError('账号已绑定其他学生档案')

                        student.objects.create(
                            sno=data['sno'],
                            user=matched_user,
                            sname=data['sname'],
                            sex=data.get('sex') or 'girl',
                            native=data.get('native') or '',
                            age=data.get('age') or None,
                            classno=class_obj,
                            semester=data.get('semester') or None,
                            home=data.get('home') or '',
                            telephone=data.get('telephone') or '',
                        )
                        success += 1
                        if account_created:
                            created_accounts += 1
                except Exception as exc:
                    errors.append(f"第{idx}行（学号 {data.get('sno', '未知')}）：{str(exc)}")

            if errors:
                error_msg = '；'.join(errors[:5])
                if len(errors) > 5:
                    error_msg += f'...（共{len(errors)}条错误）'
                messages.warning(request, f'成功导入 {success} 条，失败 {len(errors)} 条。{error_msg}')
            else:
                if created_accounts:
                    messages.success(
                        request,
                        f'成功导入 {success} 条学生，自动创建账号 {created_accounts} 个（初始密码 {DEFAULT_STUDENT_PASSWORD}）',
                    )
                else:
                    messages.success(request, f'成功导入 {success} 条学生')
            return redirect('student_list')
        except Exception as exc:
            messages.error(request, f'导入失败：{str(exc)}')
            return redirect('student_import_excel')


class StudentExportExcelView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ('admin', 'teacher')

    def get(self, request):
        wb = Workbook()
        ws = wb.active
        ws.title = '学生信息'
        headers = ['sno', 'sname', 'sex', 'native', 'age', 'classno', 'semester', 'home', 'telephone']
        ws.append(headers)

        for stu in student.objects.select_related('classno').all():
            ws.append([
                stu.sno,
                stu.sname,
                stu.sex,
                stu.native or '',
                stu.age or '',
                stu.classno.classno,
                stu.semester or '',
                stu.home or '',
                stu.telephone or '',
            ])

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = (
            f'attachment; filename=students_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
        wb.save(response)
        return response

