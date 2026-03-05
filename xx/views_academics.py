from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.db.models import Avg, Count, Max, Min, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView

from .audit import log_action, serialize_instance
from .forms import (
    ClassAddForm,
    ClassEditForm,
    CourseAddForm,
    CourseEditForm,
    DepartAddForm,
    DepartEditForm,
    SelectCourseForm,
    UpdateGradeForm,
)
from .models import cl, course, depart, sc, student
from .permissions import RoleRequiredMixin, StudentSelfOnlyMixin
from .view_shared import flash_form_errors


class ClassListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = cl
    template_name = 'class_list.html'
    context_object_name = 'classes'
    allowed_roles = ('admin', 'teacher')

    def get_queryset(self):
        return cl.objects.select_related('dno').annotate(
            student_count=Count('student', distinct=True)
        ).order_by('classno')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student_count'] = student.objects.count()
        context['depart_count'] = depart.objects.count()
        context['class_count'] = self.get_queryset().count()
        return context


class ClassAddView(LoginRequiredMixin, RoleRequiredMixin, View):
    template_name = 'class_form.html'
    allowed_roles = ('admin',)

    def get(self, request):
        return render(request, self.template_name, {'departs': depart.objects.all()})

    def post(self, request):
        form = ClassAddForm(request.POST)
        if not form.is_valid():
            flash_form_errors(request, form)
            return render(request, self.template_name, {'departs': depart.objects.all()})

        try:
            classno = form.cleaned_data['classno'].strip()
            classname = form.cleaned_data['classname'].strip()
            dno_obj = form.cleaned_data['dno']
            if cl.objects.filter(classno=classno).exists():
                messages.error(request, '班级编号已存在')
                return render(request, self.template_name, {'departs': depart.objects.all()})
            c = cl.objects.create(classno=classno, classname=classname, dno=dno_obj)
            log_action(request, 'create', c, before=None, after=serialize_instance(c))
            messages.success(request, '添加成功')
            return redirect('class_list')
        except Exception as exc:
            messages.error(request, f'添加失败：{str(exc)}')
            return render(request, self.template_name, {'departs': depart.objects.all()})


class ClassEditView(LoginRequiredMixin, RoleRequiredMixin, View):
    template_name = 'class_form.html'
    allowed_roles = ('admin',)

    def get(self, request, classno):
        c = get_object_or_404(cl, classno=classno)
        return render(request, self.template_name, {'c': c, 'departs': depart.objects.all()})

    def post(self, request, classno):
        c = get_object_or_404(cl, classno=classno)
        form = ClassEditForm(request.POST)
        if not form.is_valid():
            flash_form_errors(request, form)
            return render(request, self.template_name, {'c': c, 'departs': depart.objects.all()})

        try:
            classname = form.cleaned_data['classname'].strip()
            dno_obj = form.cleaned_data['dno']
            before = serialize_instance(c)
            c.classname = classname
            c.dno = dno_obj
            c.save()

            log_action(request, 'update', c, before=before, after=serialize_instance(c))
            messages.success(request, '修改成功')
            return redirect('class_list')
        except Exception as exc:
            messages.error(request, f'修改失败：{str(exc)}')
            return render(request, self.template_name, {'c': c, 'departs': depart.objects.all()})


class ClassDeleteView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ('admin',)
    http_method_names = ['post']

    def post(self, request, classno):
        c = get_object_or_404(cl, classno=classno)
        before = serialize_instance(c)
        c.delete()
        log_action(request, 'delete', c, before=before, after=None)
        messages.success(request, '删除成功')
        return redirect('class_list')


class DepartListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = depart
    template_name = 'depart_list.html'
    context_object_name = 'departs'
    ordering = ['dno']
    allowed_roles = ('admin', 'teacher')


class DepartAddView(LoginRequiredMixin, RoleRequiredMixin, View):
    template_name = 'depart_form.html'
    allowed_roles = ('admin',)

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        form = DepartAddForm(request.POST)
        if not form.is_valid():
            flash_form_errors(request, form)
            return render(request, self.template_name)

        dno = form.cleaned_data['dno'].strip()
        dname = form.cleaned_data['dname'].strip()
        telephone = form.cleaned_data.get('telephone') or ''
        if depart.objects.filter(dno=dno).exists():
            messages.error(request, '系部编号已存在')
            return render(request, self.template_name)

        d = depart.objects.create(dno=dno, dname=dname, telephone=telephone)
        log_action(request, 'create', d, before=None, after=serialize_instance(d))
        messages.success(request, '添加成功')
        return redirect('depart_list')


class DepartEditView(LoginRequiredMixin, RoleRequiredMixin, View):
    template_name = 'depart_form.html'
    allowed_roles = ('admin',)

    def get(self, request, dno):
        d = get_object_or_404(depart, dno=dno)
        return render(request, self.template_name, {'d': d})

    def post(self, request, dno):
        d = get_object_or_404(depart, dno=dno)
        form = DepartEditForm(request.POST)
        if not form.is_valid():
            flash_form_errors(request, form)
            return render(request, self.template_name, {'d': d})

        dname = form.cleaned_data['dname'].strip()
        telephone = form.cleaned_data.get('telephone') or ''

        before = serialize_instance(d)
        d.dname = dname
        d.telephone = telephone
        d.save()

        log_action(request, 'update', d, before=before, after=serialize_instance(d))
        messages.success(request, '修改成功')
        return redirect('depart_list')


class DepartDeleteView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ('admin',)
    http_method_names = ['post']

    def post(self, request, dno):
        d = get_object_or_404(depart, dno=dno)
        before = serialize_instance(d)
        d.delete()
        log_action(request, 'delete', d, before=before, after=None)
        messages.success(request, '删除成功')
        return redirect('depart_list')


class CourseListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = course
    template_name = 'course_list.html'
    context_object_name = 'courses'
    allowed_roles = ('admin', 'teacher')

    def get_queryset(self):
        queryset = course.objects.all()

        cname = self.request.GET.get('cname', '').strip()
        type_ = self.request.GET.get('type', '').strip()
        semester = self.request.GET.get('semester', '').strip()
        order = self.request.GET.get('order', 'cno')
        direction = self.request.GET.get('direction', 'asc')

        if cname:
            queryset = queryset.filter(cname__icontains=cname)
        if type_:
            queryset = queryset.filter(type=type_)
        if semester:
            queryset = queryset.filter(semester=semester)

        allowed_orders = ['cno', 'cname', 'semester', 'credit']
        if order in allowed_orders:
            if direction == 'desc':
                order = '-' + order
            queryset = queryset.order_by(order)

        return queryset


class CourseAddView(LoginRequiredMixin, RoleRequiredMixin, View):
    template_name = 'course_form.html'
    allowed_roles = ('admin',)

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        form = CourseAddForm(request.POST)
        if not form.is_valid():
            flash_form_errors(request, form)
            return render(request, self.template_name)

        cno = form.cleaned_data['cno'].strip()
        cname = form.cleaned_data['cname'].strip()
        if course.objects.filter(cno=cno).exists():
            messages.error(request, '课程编号已存在')
            return render(request, self.template_name)

        c = course.objects.create(
            cno=cno,
            cname=cname,
            lecture=form.cleaned_data.get('lecture') or None,
            semester=form.cleaned_data.get('semester') or None,
            credit=form.cleaned_data.get('credit') or None,
            type=form.cleaned_data.get('type') or 'crc',
        )
        log_action(request, 'create', c, before=None, after=serialize_instance(c))
        messages.success(request, '添加成功')
        return redirect('course_list')


class CourseEditView(LoginRequiredMixin, RoleRequiredMixin, View):
    template_name = 'course_form.html'
    allowed_roles = ('admin',)

    def get(self, request, cno):
        c = get_object_or_404(course, cno=cno)
        return render(request, self.template_name, {'c': c})

    def post(self, request, cno):
        c = get_object_or_404(course, cno=cno)
        form = CourseEditForm(request.POST)
        if not form.is_valid():
            flash_form_errors(request, form)
            return render(request, self.template_name, {'c': c})

        cname = form.cleaned_data['cname'].strip()

        before = serialize_instance(c)
        c.cname = cname
        c.lecture = form.cleaned_data.get('lecture') or None
        c.semester = form.cleaned_data.get('semester') or None
        c.credit = form.cleaned_data.get('credit') or None
        c.type = form.cleaned_data.get('type') or 'crc'
        c.save()

        log_action(request, 'update', c, before=before, after=serialize_instance(c))
        messages.success(request, '修改成功')
        return redirect('course_list')


class CourseDeleteView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ('admin',)
    http_method_names = ['post']

    def post(self, request, cno):
        c = get_object_or_404(course, cno=cno)
        before = serialize_instance(c)
        c.delete()
        log_action(request, 'delete', c, before=before, after=None)
        messages.success(request, '删除成功')
        return redirect('course_list')


class SelectCourseView(LoginRequiredMixin, RoleRequiredMixin, View):
    template_name = 'select_course.html'
    allowed_roles = ('admin', 'teacher')

    def get(self, request, sno):
        stu = get_object_or_404(student, sno=sno)
        selected_courses = sc.objects.filter(sno=stu).values_list('cno_id', flat=True)
        courses = course.objects.exclude(cno__in=selected_courses)
        return render(request, self.template_name, {'stu': stu, 'courses': courses})

    def post(self, request, sno):
        stu = get_object_or_404(student, sno=sno)
        form = SelectCourseForm(request.POST)
        if not form.is_valid():
            messages.error(request, '请选择课程')
            return redirect('select_course', sno=sno)

        course_obj = form.cleaned_data['cno']
        try:
            _, created = sc.objects.get_or_create(sno=stu, cno=course_obj)
            if created:
                messages.success(request, '选课成功')
            else:
                messages.error(request, '已选过该课程')
        except IntegrityError:
            messages.error(request, '已选过该课程')
        except Exception as exc:
            messages.error(request, f'选课失败：{str(exc)}')

        return redirect('student_course', sno=sno)


class StudentCourseView(LoginRequiredMixin, RoleRequiredMixin, StudentSelfOnlyMixin, View):
    template_name = 'student_course.html'
    allowed_roles = ('admin', 'teacher', 'student')

    def get(self, request, sno):
        stu = get_object_or_404(student, sno=sno)
        records = sc.objects.select_related('cno').filter(sno=stu)
        graded_records = records.filter(grade__isnull=False)
        total_credit = graded_records.aggregate(total=Sum('cno__credit'))['total'] or 0
        avg_credit = graded_records.aggregate(avg=Avg('cno__credit'))['avg'] or 0
        return render(request, self.template_name, {
            'stu': stu,
            'records': records,
            'total_credit': round(total_credit, 1),
            'avg_credit': round(avg_credit, 1),
        })


class UpdateGradeView(LoginRequiredMixin, RoleRequiredMixin, View):
    template_name = 'grade_form.html'
    allowed_roles = ('admin', 'teacher')

    def get(self, request, sno, cno):
        record = get_object_or_404(sc, sno_id=sno, cno_id=cno)
        return render(request, self.template_name, {'record': record})

    def post(self, request, sno, cno):
        record = get_object_or_404(sc, sno_id=sno, cno_id=cno)
        form = UpdateGradeForm(request.POST)
        if not form.is_valid():
            flash_form_errors(request, form)
            return render(request, self.template_name, {'record': record})

        try:
            grade_value = form.cleaned_data['grade']
            record.grade = grade_value
            record.save()
            messages.success(request, '成绩录入成功')
            return redirect('student_course', sno=sno)
        except Exception as exc:
            messages.error(request, f'成绩保存失败：{str(exc)}')
            return render(request, self.template_name, {'record': record})


class CourseStudentsView(LoginRequiredMixin, RoleRequiredMixin, View):
    template_name = 'course_students.html'
    allowed_roles = ('admin', 'teacher')

    def get(self, request, cno):
        c = get_object_or_404(course, cno=cno)
        records = sc.objects.select_related('sno', 'sno__classno').filter(cno=c)
        graded_records = records.filter(grade__isnull=False)

        stats = graded_records.aggregate(
            avg=Avg('grade'),
            max_grade=Max('grade'),
            min_grade=Min('grade'),
            graded=Count('grade'),
        )

        excellent = graded_records.filter(grade__gte=90).count()
        good = graded_records.filter(grade__gte=80, grade__lt=90).count()
        passed = graded_records.filter(grade__gte=60, grade__lt=80).count()
        failed = graded_records.filter(grade__lt=60).count()

        return render(request, self.template_name, {
            'course': c,
            'records': records,
            'excellent': excellent,
            'good': good,
            'passed': passed,
            'failed': failed,
            'avg': round(stats['avg'], 1) if stats['avg'] else None,
            'max_grade': stats['max_grade'],
            'min_grade': stats['min_grade'],
            'graded': stats['graded'],
            'total': records.count(),
        })
