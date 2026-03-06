from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.db.models import Avg, Count, Max, Min, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
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
from .models import SelectionHistory, cl, course, depart, sc, student
from .permissions import (
    RoleRequiredMixin,
    StudentSelfOnlyMixin,
    is_teacher,
    teacher_can_access_course,
    teacher_can_access_student,
    teacher_can_manage_record,
    teacher_class_ids,
    teacher_course_queryset,
)
from .view_shared import flash_form_errors


def _official_records(queryset):
    return queryset.filter(
        selection_status=sc.SELECTION_ACTIVE,
        grade_status=sc.GRADE_PUBLISHED,
        grade__isnull=False,
    )


def _log_selection_history(request, record, action, before=None, note=''):
    actor = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
    before = before or {}
    SelectionHistory.objects.create(
        record=record,
        action=action,
        actor=actor,
        actor_name=actor.get_username() if actor else '',
        before_selection_status=before.get('selection_status', ''),
        after_selection_status=record.selection_status,
        before_grade_status=before.get('grade_status', ''),
        after_grade_status=record.grade_status,
        before_grade=before.get('grade'),
        after_grade=record.grade,
        note=note,
    )


def _ensure_teacher_student_access(request, stu):
    if is_teacher(request.user) and not teacher_can_access_student(request.user, stu):
        messages.error(request, '无权限访问')
        return False
    return True


def _ensure_teacher_course_access(request, course_obj):
    if is_teacher(request.user) and not teacher_can_access_course(request.user, course_obj):
        messages.error(request, '无权限访问')
        return False
    return True


class ClassListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = cl
    template_name = 'class_list.html'
    context_object_name = 'classes'
    allowed_roles = ('admin', 'teacher')

    def get_queryset(self):
        queryset = cl.objects.select_related('dno').filter(is_active=True)
        if is_teacher(self.request.user):
            queryset = queryset.filter(classno__in=teacher_class_ids(self.request.user))
        return queryset.annotate(
            student_count=Count('student', filter=Q(student__is_active=True), distinct=True)
        ).order_by('classno')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        class_qs = self.get_queryset()
        student_qs = student.objects.filter(is_active=True)
        if is_teacher(self.request.user):
            student_qs = student_qs.filter(classno_id__in=teacher_class_ids(self.request.user))
        context['student_count'] = student_qs.count()
        context['depart_count'] = class_qs.values('dno').distinct().count()
        context['class_count'] = class_qs.count()
        return context


class ClassAddView(LoginRequiredMixin, RoleRequiredMixin, View):
    template_name = 'class_form.html'
    allowed_roles = ('admin',)

    def get(self, request):
        return render(request, self.template_name, {'departs': depart.objects.filter(is_active=True).order_by('dno')})

    def post(self, request):
        form = ClassAddForm(request.POST)
        if not form.is_valid():
            flash_form_errors(request, form)
            return render(request, self.template_name, {'departs': depart.objects.filter(is_active=True).order_by('dno')})

        try:
            classno = form.cleaned_data['classno'].strip()
            classname = form.cleaned_data['classname'].strip()
            dno_obj = form.cleaned_data['dno']
            existing = cl.objects.filter(classno=classno).first()
            if existing and existing.is_active:
                messages.error(request, '班级编号已存在')
                return render(request, self.template_name, {'departs': depart.objects.filter(is_active=True).order_by('dno')})
            if existing:
                before = serialize_instance(existing)
                existing.classname = classname
                existing.dno = dno_obj
                existing.restore()
                existing.save()
                log_action(request, 'update', existing, before=before, after=serialize_instance(existing))
                messages.success(request, '已恢复并更新班级')
            else:
                c = cl.objects.create(classno=classno, classname=classname, dno=dno_obj)
                log_action(request, 'create', c, before=None, after=serialize_instance(c))
                messages.success(request, '添加成功')
            return redirect('class_list')
        except Exception as exc:
            messages.error(request, f'添加失败：{str(exc)}')
            return render(request, self.template_name, {'departs': depart.objects.filter(is_active=True).order_by('dno')})


class ClassEditView(LoginRequiredMixin, RoleRequiredMixin, View):
    template_name = 'class_form.html'
    allowed_roles = ('admin',)

    def get(self, request, classno):
        c = get_object_or_404(cl, classno=classno, is_active=True)
        return render(request, self.template_name, {'c': c, 'departs': depart.objects.filter(is_active=True).order_by('dno')})

    def post(self, request, classno):
        c = get_object_or_404(cl, classno=classno, is_active=True)
        form = ClassEditForm(request.POST)
        if not form.is_valid():
            flash_form_errors(request, form)
            return render(request, self.template_name, {'c': c, 'departs': depart.objects.filter(is_active=True).order_by('dno')})

        try:
            before = serialize_instance(c)
            c.classname = form.cleaned_data['classname'].strip()
            c.dno = form.cleaned_data['dno']
            c.save()
            log_action(request, 'update', c, before=before, after=serialize_instance(c))
            messages.success(request, '修改成功')
            return redirect('class_list')
        except Exception as exc:
            messages.error(request, f'修改失败：{str(exc)}')
            return render(request, self.template_name, {'c': c, 'departs': depart.objects.filter(is_active=True).order_by('dno')})


class ClassDeleteView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ('admin',)
    http_method_names = ['post']

    def post(self, request, classno):
        c = get_object_or_404(cl, classno=classno, is_active=True)
        if student.objects.filter(classno=c, is_active=True).exists():
            messages.error(request, '该班级下仍有有效学生，不能归档')
            return redirect('class_list')
        before = serialize_instance(c)
        c.archive()
        c.save()
        log_action(request, 'delete', c, before=before, after=serialize_instance(c))
        messages.success(request, '班级已归档')
        return redirect('class_list')


class DepartListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = depart
    template_name = 'depart_list.html'
    context_object_name = 'departs'
    ordering = ['dno']
    allowed_roles = ('admin', 'teacher')

    def get_queryset(self):
        queryset = depart.objects.filter(is_active=True)
        if is_teacher(self.request.user):
            class_ids = teacher_class_ids(self.request.user)
            queryset = queryset.filter(cl__classno__in=class_ids).distinct().annotate(
                active_class_count=Count(
                    'cl',
                    filter=Q(cl__is_active=True, cl__classno__in=class_ids),
                    distinct=True,
                ),
                active_student_count=Count(
                    'cl__student',
                    filter=Q(
                        cl__is_active=True,
                        cl__classno__in=class_ids,
                        cl__student__is_active=True,
                    ),
                    distinct=True,
                ),
            )
        else:
            queryset = queryset.annotate(
                active_class_count=Count('cl', filter=Q(cl__is_active=True), distinct=True),
                active_student_count=Count(
                    'cl__student',
                    filter=Q(cl__is_active=True, cl__student__is_active=True),
                    distinct=True,
                ),
            )
        return queryset.order_by('dno')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        visible_dnos = queryset.values_list('dno', flat=True)
        context['depart_count'] = queryset.count()
        context['phone_count'] = queryset.exclude(telephone='').exclude(telephone__isnull=True).count()

        if is_teacher(self.request.user):
            class_ids = teacher_class_ids(self.request.user)
            active_classes = cl.objects.filter(
                is_active=True,
                dno_id__in=visible_dnos,
                classno__in=class_ids,
            )
            active_students = student.objects.filter(
                is_active=True,
                classno__is_active=True,
                classno__dno_id__in=visible_dnos,
                classno_id__in=class_ids,
            )
        else:
            active_classes = cl.objects.filter(is_active=True, dno_id__in=visible_dnos)
            active_students = student.objects.filter(
                is_active=True,
                classno__is_active=True,
                classno__dno_id__in=visible_dnos,
            )

        context['active_class_total'] = active_classes.count()
        context['active_student_total'] = active_students.count()
        return context


class DepartAddView(LoginRequiredMixin, RoleRequiredMixin, View):
    template_name = 'depart_form.html'
    allowed_roles = ('admin',)

    def render_form(self, request, form_data=None):
        context = {'depart': None}
        if form_data is not None:
            context['form_data'] = form_data
        return render(request, self.template_name, context)

    def get(self, request):
        return self.render_form(request)

    def post(self, request):
        form = DepartAddForm(request.POST)
        if not form.is_valid():
            flash_form_errors(request, form)
            return self.render_form(request, request.POST)

        dno = form.cleaned_data['dno'].strip()
        dname = form.cleaned_data['dname'].strip()
        telephone = form.cleaned_data.get('telephone') or ''
        existing = depart.objects.filter(dno=dno).first()
        if existing and existing.is_active:
            messages.error(request, '系部编号已存在')
            return self.render_form(request, request.POST)

        if existing:
            before = serialize_instance(existing)
            existing.dname = dname
            existing.telephone = telephone
            existing.restore()
            existing.save()
            log_action(request, 'update', existing, before=before, after=serialize_instance(existing))
            messages.success(request, '已恢复并更新系部')
        else:
            d = depart.objects.create(dno=dno, dname=dname, telephone=telephone)
            log_action(request, 'create', d, before=None, after=serialize_instance(d))
            messages.success(request, '添加成功')
        return redirect('depart_list')


class DepartEditView(LoginRequiredMixin, RoleRequiredMixin, View):
    template_name = 'depart_form.html'
    allowed_roles = ('admin',)

    def get(self, request, dno):
        d = get_object_or_404(depart, dno=dno, is_active=True)
        return render(request, self.template_name, {'depart': d})

    def post(self, request, dno):
        d = get_object_or_404(depart, dno=dno, is_active=True)
        form = DepartEditForm(request.POST)
        if not form.is_valid():
            flash_form_errors(request, form)
            return render(request, self.template_name, {'depart': d, 'form_data': request.POST})

        before = serialize_instance(d)
        d.dname = form.cleaned_data['dname'].strip()
        d.telephone = form.cleaned_data.get('telephone') or ''
        d.save()

        log_action(request, 'update', d, before=before, after=serialize_instance(d))
        messages.success(request, '修改成功')
        return redirect('depart_list')


class DepartDeleteView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ('admin',)
    http_method_names = ['post']

    def post(self, request, dno):
        d = get_object_or_404(depart, dno=dno, is_active=True)
        if cl.objects.filter(dno=d, is_active=True).exists():
            messages.error(request, '该系部下仍有有效班级，不能归档')
            return redirect('depart_list')
        before = serialize_instance(d)
        d.archive()
        d.save()
        log_action(request, 'delete', d, before=before, after=serialize_instance(d))
        messages.success(request, '系部已归档')
        return redirect('depart_list')


class CourseListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = course
    template_name = 'course_list.html'
    context_object_name = 'courses'
    allowed_roles = ('admin', 'teacher')

    def get_queryset(self):
        queryset = course.objects.filter(is_active=True)
        if is_teacher(self.request.user):
            queryset = teacher_course_queryset(self.request.user)

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        query_params = self.request.GET.copy()
        if 'order' in query_params:
            del query_params['order']
        selected_type = self.request.GET.get('type', '').strip()
        selected_semester = self.request.GET.get('semester', '').strip()
        context['sort_query_string'] = query_params.urlencode()
        context['current_semester_label'] = selected_semester or '全部'
        context['current_type_label'] = dict(course.coutype).get(selected_type, '全部')
        context['semester_count'] = queryset.exclude(semester__isnull=True).values('semester').distinct().count()
        context['type_count'] = queryset.exclude(type__isnull=True).values('type').distinct().count()
        return context


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
        existing = course.objects.filter(cno=cno).first()
        if existing and existing.is_active:
            messages.error(request, '课程编号已存在')
            return render(request, self.template_name)

        if existing:
            before = serialize_instance(existing)
            existing.cname = cname
            existing.lecture = form.cleaned_data.get('lecture') or None
            existing.semester = form.cleaned_data.get('semester') or None
            existing.credit = form.cleaned_data.get('credit') or None
            existing.type = form.cleaned_data.get('type') or 'crc'
            existing.restore()
            existing.save()
            log_action(request, 'update', existing, before=before, after=serialize_instance(existing))
            messages.success(request, '已恢复并更新课程')
        else:
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
        c = get_object_or_404(course, cno=cno, is_active=True)
        return render(request, self.template_name, {'c': c})

    def post(self, request, cno):
        c = get_object_or_404(course, cno=cno, is_active=True)
        form = CourseEditForm(request.POST)
        if not form.is_valid():
            flash_form_errors(request, form)
            return render(request, self.template_name, {'c': c})

        before = serialize_instance(c)
        c.cname = form.cleaned_data['cname'].strip()
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
        c = get_object_or_404(course, cno=cno, is_active=True)
        if sc.objects.filter(cno=c, selection_status=sc.SELECTION_ACTIVE).exists():
            messages.error(request, '该课程仍有有效选课记录，不能归档')
            return redirect('course_list')
        before = serialize_instance(c)
        c.archive()
        c.save()
        log_action(request, 'delete', c, before=before, after=serialize_instance(c))
        messages.success(request, '课程已归档')
        return redirect('course_list')


class SelectCourseView(LoginRequiredMixin, RoleRequiredMixin, View):
    template_name = 'select_course.html'
    allowed_roles = ('admin', 'teacher')

    def get(self, request, sno):
        stu = get_object_or_404(student.objects.select_related('classno'), sno=sno, is_active=True)
        if not _ensure_teacher_student_access(request, stu):
            return redirect('/')

        selected_courses = sc.objects.filter(sno=stu, selection_status=sc.SELECTION_ACTIVE).values_list('cno_id', flat=True)
        courses = course.objects.filter(is_active=True).exclude(cno__in=selected_courses).order_by('cno')
        if is_teacher(request.user):
            courses = teacher_course_queryset(request.user).exclude(cno__in=selected_courses)
        return render(request, self.template_name, {'stu': stu, 'courses': courses})

    def post(self, request, sno):
        stu = get_object_or_404(student.objects.select_related('classno'), sno=sno, is_active=True)
        if not _ensure_teacher_student_access(request, stu):
            return redirect('/')

        form = SelectCourseForm(request.POST)
        if not form.is_valid():
            messages.error(request, '请选择课程')
            return redirect('select_course', sno=sno)

        course_obj = form.cleaned_data['cno']
        if not _ensure_teacher_course_access(request, course_obj):
            return redirect('/')

        try:
            record = sc.objects.filter(sno=stu, cno=course_obj).first()
            if record is None:
                record = sc.objects.create(sno=stu, cno=course_obj)
                _log_selection_history(request, record, SelectionHistory.ACTION_SELECTED)
                messages.success(request, '选课成功')
            elif record.selection_status == sc.SELECTION_DROPPED:
                before = {
                    'selection_status': record.selection_status,
                    'grade_status': record.grade_status,
                    'grade': record.grade,
                }
                record.selection_status = sc.SELECTION_ACTIVE
                record.grade_status = sc.GRADE_PENDING
                record.grade = None
                record.dropped_at = None
                record.save()
                _log_selection_history(request, record, SelectionHistory.ACTION_SELECTED, before=before, note='重新选课')
                messages.success(request, '已恢复选课记录')
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
        stu = get_object_or_404(student.objects.select_related('classno', 'classno__dno'), sno=sno, is_active=True)
        if not _ensure_teacher_student_access(request, stu):
            return redirect('/')

        records = sc.objects.select_related('cno').filter(sno=stu).order_by('cno__cno')
        official_records = _official_records(records)
        active_records = records.filter(selection_status=sc.SELECTION_ACTIVE)
        total_credit = official_records.aggregate(total=Sum('cno__credit'))['total'] or 0
        avg_credit = active_records.aggregate(avg=Avg('cno__credit'))['avg'] or 0

        return render(request, self.template_name, {
            'stu': stu,
            'records': records,
            'total_credit': round(total_credit, 1),
            'avg_credit': round(avg_credit, 1),
            'published_count': official_records.count(),
            'draft_count': active_records.filter(grade_status=sc.GRADE_DRAFT).count(),
            'pending_count': active_records.filter(grade_status__in=[sc.GRADE_PENDING, sc.GRADE_RETAKE]).count(),
            'dropped_count': records.filter(selection_status=sc.SELECTION_DROPPED).count(),
        })


class UpdateGradeView(LoginRequiredMixin, RoleRequiredMixin, View):
    template_name = 'grade_form.html'
    allowed_roles = ('admin', 'teacher')

    def get(self, request, sno, cno):
        record = get_object_or_404(sc.objects.select_related('sno', 'cno'), sno_id=sno, cno_id=cno)
        if is_teacher(request.user) and not teacher_can_manage_record(request.user, record):
            messages.error(request, '无权限访问')
            return redirect('/')
        if record.selection_status != sc.SELECTION_ACTIVE:
            messages.error(request, '已退课记录不能录入成绩')
            return redirect('student_course', sno=sno)
        history = record.history.all()[:10]
        return render(request, self.template_name, {'record': record, 'history': history})

    def post(self, request, sno, cno):
        record = get_object_or_404(sc.objects.select_related('sno', 'cno'), sno_id=sno, cno_id=cno)
        if is_teacher(request.user) and not teacher_can_manage_record(request.user, record):
            messages.error(request, '无权限访问')
            return redirect('/')
        if record.selection_status != sc.SELECTION_ACTIVE:
            messages.error(request, '已退课记录不能录入成绩')
            return redirect('student_course', sno=sno)
        if record.grade_status == sc.GRADE_PUBLISHED:
            messages.error(request, '已发布成绩已锁定，请先发起重修流程')
            return redirect('student_course', sno=sno)

        form = UpdateGradeForm(request.POST)
        if not form.is_valid():
            flash_form_errors(request, form)
            history = record.history.all()[:10]
            return render(request, self.template_name, {'record': record, 'history': history})

        try:
            before = serialize_instance(record)
            history_before = {
                'selection_status': record.selection_status,
                'grade_status': record.grade_status,
                'grade': record.grade,
            }
            record.grade = form.cleaned_data['grade']
            record.grade_status = sc.GRADE_DRAFT
            record.save()
            log_action(request, 'update', record, before=before, after=serialize_instance(record))
            _log_selection_history(request, record, SelectionHistory.ACTION_GRADE_SAVED, before=history_before)
            messages.success(request, '成绩已保存为草稿')
            return redirect('student_course', sno=sno)
        except Exception as exc:
            messages.error(request, f'成绩保存失败：{str(exc)}')
            history = record.history.all()[:10]
            return render(request, self.template_name, {'record': record, 'history': history})


class PublishGradeView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ('admin', 'teacher')
    http_method_names = ['post']

    def post(self, request, sno, cno):
        record = get_object_or_404(sc.objects.select_related('sno', 'cno'), sno_id=sno, cno_id=cno)
        if is_teacher(request.user) and not teacher_can_manage_record(request.user, record):
            messages.error(request, '无权限访问')
            return redirect('/')
        if record.selection_status != sc.SELECTION_ACTIVE:
            messages.error(request, '已退课记录不能发布成绩')
            return redirect('student_course', sno=sno)
        if record.grade is None:
            messages.error(request, '请先录入成绩')
            return redirect('student_course', sno=sno)

        before = serialize_instance(record)
        history_before = {
            'selection_status': record.selection_status,
            'grade_status': record.grade_status,
            'grade': record.grade,
        }
        record.grade_status = sc.GRADE_PUBLISHED
        record.published_at = timezone.now()
        record.save()
        log_action(request, 'update', record, before=before, after=serialize_instance(record))
        _log_selection_history(request, record, SelectionHistory.ACTION_GRADE_PUBLISHED, before=history_before)
        messages.success(request, '成绩已发布')
        return redirect('student_course', sno=sno)


class MarkRetakeView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ('admin', 'teacher')
    http_method_names = ['post']

    def post(self, request, sno, cno):
        record = get_object_or_404(sc.objects.select_related('sno', 'cno'), sno_id=sno, cno_id=cno)
        if is_teacher(request.user) and not teacher_can_manage_record(request.user, record):
            messages.error(request, '无权限访问')
            return redirect('/')
        if record.selection_status != sc.SELECTION_ACTIVE:
            messages.error(request, '已退课记录不能发起重修')
            return redirect('student_course', sno=sno)
        if record.grade_status != sc.GRADE_PUBLISHED:
            messages.error(request, '仅已发布成绩可以发起重修')
            return redirect('student_course', sno=sno)

        before = serialize_instance(record)
        history_before = {
            'selection_status': record.selection_status,
            'grade_status': record.grade_status,
            'grade': record.grade,
        }
        record.attempt_no += 1
        record.grade = None
        record.grade_status = sc.GRADE_RETAKE
        record.published_at = None
        record.save()
        log_action(request, 'update', record, before=before, after=serialize_instance(record))
        _log_selection_history(request, record, SelectionHistory.ACTION_RETAKE_MARKED, before=history_before)
        messages.success(request, '已发起重修，本次成绩需重新录入并发布')
        return redirect('student_course', sno=sno)


class DropCourseView(LoginRequiredMixin, RoleRequiredMixin, StudentSelfOnlyMixin, View):
    allowed_roles = ('admin', 'teacher', 'student')
    http_method_names = ['post']

    def post(self, request, sno, cno):
        record = get_object_or_404(sc.objects.select_related('sno', 'cno'), sno_id=sno, cno_id=cno)
        if is_teacher(request.user) and not teacher_can_manage_record(request.user, record):
            messages.error(request, '无权限访问')
            return redirect('/')
        if record.selection_status == sc.SELECTION_DROPPED:
            messages.warning(request, '该课程已退课')
            return redirect('student_course', sno=sno)
        if record.grade_status == sc.GRADE_PUBLISHED:
            messages.error(request, '已发布成绩不能退课')
            return redirect('student_course', sno=sno)

        before = serialize_instance(record)
        history_before = {
            'selection_status': record.selection_status,
            'grade_status': record.grade_status,
            'grade': record.grade,
        }
        record.selection_status = sc.SELECTION_DROPPED
        record.grade_status = sc.GRADE_PENDING
        record.grade = None
        record.dropped_at = timezone.now()
        record.published_at = None
        record.save()
        log_action(request, 'update', record, before=before, after=serialize_instance(record))
        _log_selection_history(request, record, SelectionHistory.ACTION_DROPPED, before=history_before)
        messages.success(request, '退课成功')
        return redirect('student_course', sno=sno)


class CourseStudentsView(LoginRequiredMixin, RoleRequiredMixin, View):
    template_name = 'course_students.html'
    allowed_roles = ('admin', 'teacher')

    def get(self, request, cno):
        c = get_object_or_404(course, cno=cno, is_active=True)
        if not _ensure_teacher_course_access(request, c):
            return redirect('/')

        scope = request.GET.get('scope', 'active')
        records = sc.objects.select_related('sno', 'sno__classno', 'sno__classno__dno').filter(cno=c)
        if scope == 'active':
            records = records.filter(selection_status=sc.SELECTION_ACTIVE)
        elif scope == 'dropped':
            records = records.filter(selection_status=sc.SELECTION_DROPPED)

        published_records = _official_records(records)

        stats = published_records.aggregate(
            avg=Avg('grade'),
            max_grade=Max('grade'),
            min_grade=Min('grade'),
            graded=Count('grade'),
        )

        excellent = published_records.filter(grade__gte=90).count()
        good = published_records.filter(grade__gte=80, grade__lt=90).count()
        passed = published_records.filter(grade__gte=60, grade__lt=80).count()
        failed = published_records.filter(grade__lt=60).count()

        return render(request, self.template_name, {
            'course': c,
            'records': records.order_by('sno__sno'),
            'excellent': excellent,
            'good': good,
            'passed': passed,
            'failed': failed,
            'avg': round(stats['avg'], 1) if stats['avg'] is not None else None,
            'max_grade': stats['max_grade'],
            'min_grade': stats['min_grade'],
            'graded': stats['graded'],
            'draft_count': records.filter(selection_status=sc.SELECTION_ACTIVE, grade_status=sc.GRADE_DRAFT).count(),
            'pending_count': records.filter(selection_status=sc.SELECTION_ACTIVE, grade_status__in=[sc.GRADE_PENDING, sc.GRADE_RETAKE]).count(),
            'dropped_count': records.filter(selection_status=sc.SELECTION_DROPPED).count(),
            'scope': scope,
            'total': records.count(),
        })
