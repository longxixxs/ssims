from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import cl, course, depart, student
from .view_shared import DEFAULT_STUDENT_PASSWORD, MANAGED_ROLES


def _raise_password_error(password, user=None):
    try:
        validate_password(password, user=user)
    except ValidationError as exc:
        raise forms.ValidationError('；'.join(exc.messages))


class UserCreateInputForm(forms.Form):
    username = forms.CharField(max_length=150)
    nickname = forms.CharField(max_length=150)
    password1 = forms.CharField(required=False)
    password2 = forms.CharField(required=False)
    groups = forms.ChoiceField(choices=[(name, name) for name in MANAGED_ROLES])
    create_student = forms.BooleanField(required=False)

    sname = forms.CharField(required=False, max_length=10)
    sex = forms.ChoiceField(required=False, choices=student.stusex)
    classno = forms.ModelChoiceField(
        required=False,
        queryset=cl.objects.all(),
        to_field_name='classno',
    )
    native = forms.CharField(required=False, max_length=20)
    age = forms.IntegerField(required=False, min_value=10, max_value=100)
    semester = forms.IntegerField(required=False, min_value=1, max_value=12)
    home = forms.CharField(required=False, max_length=40)
    telephone = forms.CharField(required=False, max_length=20)

    def clean_groups(self):
        group_names = self.data.getlist('groups')
        if len(group_names) != 1:
            raise forms.ValidationError('角色必须且只能选择一个')
        selected_role = group_names[0]
        if selected_role not in MANAGED_ROLES:
            raise forms.ValidationError('检测到非法角色提交')
        return selected_role

    def clean(self):
        cleaned = super().clean()
        selected_role = cleaned.get('groups')
        create_student = cleaned.get('create_student')
        password1 = cleaned.get('password1') or ''
        password2 = cleaned.get('password2') or ''

        if selected_role == 'student':
            cleaned['final_password'] = DEFAULT_STUDENT_PASSWORD
        else:
            if not (password1 or password2):
                raise forms.ValidationError('密码不能为空，请设置密码')
            if password1 != password2:
                raise forms.ValidationError('两次密码不一致')
            if len(password1) < 6:
                raise forms.ValidationError('密码长度不能少于6位')
            _raise_password_error(password1)
            cleaned['final_password'] = password1

        if selected_role == 'student' and not create_student:
            raise forms.ValidationError('学生角色必须创建学生档案')
        if create_student and selected_role != 'student':
            raise forms.ValidationError('仅学生角色可以创建学生档案')
        if create_student and (not cleaned.get('sname') or not cleaned.get('classno')):
            raise forms.ValidationError('创建学生档案时，姓名和班级不能为空')
        return cleaned


class UserEditInputForm(forms.Form):
    nickname = forms.CharField(max_length=150)
    password1 = forms.CharField(required=False)
    password2 = forms.CharField(required=False)
    groups = forms.ChoiceField(choices=[(name, name) for name in MANAGED_ROLES])
    create_student = forms.BooleanField(required=False)

    sname = forms.CharField(required=False, max_length=10)
    sex = forms.ChoiceField(required=False, choices=student.stusex)
    classno = forms.ModelChoiceField(
        required=False,
        queryset=cl.objects.all(),
        to_field_name='classno',
    )
    native = forms.CharField(required=False, max_length=20)
    age = forms.IntegerField(required=False, min_value=10, max_value=100)
    semester = forms.IntegerField(required=False, min_value=1, max_value=12)
    home = forms.CharField(required=False, max_length=40)
    telephone = forms.CharField(required=False, max_length=20)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user

    def clean_groups(self):
        group_names = self.data.getlist('groups')
        if len(group_names) != 1:
            raise forms.ValidationError('角色必须且只能选择一个')
        selected_role = group_names[0]
        if selected_role not in MANAGED_ROLES:
            raise forms.ValidationError('检测到非法角色提交')
        return selected_role

    def clean(self):
        cleaned = super().clean()
        selected_role = cleaned.get('groups')
        create_student = cleaned.get('create_student')
        password1 = cleaned.get('password1') or ''
        password2 = cleaned.get('password2') or ''

        if password1 or password2:
            if password1 != password2:
                raise forms.ValidationError('两次密码不一致')
            if len(password1) < 6:
                raise forms.ValidationError('密码长度不能少于6位')
            _raise_password_error(password1, user=self._user)

        if create_student and selected_role != 'student':
            raise forms.ValidationError('仅学生角色可以创建学生档案')
        if create_student and (not cleaned.get('sname') or not cleaned.get('classno')):
            raise forms.ValidationError('创建学生档案时，姓名和班级不能为空')
        return cleaned


class StudentAddForm(forms.Form):
    sno = forms.CharField(max_length=10)
    sname = forms.CharField(max_length=10)
    sex = forms.ChoiceField(required=False, choices=student.stusex, initial='girl')
    native = forms.CharField(required=False, max_length=20)
    age = forms.IntegerField(required=False, min_value=10, max_value=100)
    classno = forms.ModelChoiceField(
        queryset=cl.objects.all(),
        to_field_name='classno',
    )
    semester = forms.IntegerField(required=False, min_value=1, max_value=12)
    home = forms.CharField(required=False, max_length=40)
    telephone = forms.CharField(required=False, max_length=20)


class StudentEditForm(forms.Form):
    sname = forms.CharField(max_length=10)
    sex = forms.ChoiceField(required=False, choices=student.stusex, initial='girl')
    native = forms.CharField(required=False, max_length=20)
    age = forms.IntegerField(required=False, min_value=10, max_value=100)
    classno = forms.ModelChoiceField(
        queryset=cl.objects.all(),
        to_field_name='classno',
    )
    semester = forms.IntegerField(required=False, min_value=1, max_value=12)
    home = forms.CharField(required=False, max_length=40)
    telephone = forms.CharField(required=False, max_length=20)


class ClassAddForm(forms.Form):
    classno = forms.CharField(max_length=6)
    classname = forms.CharField(max_length=10)
    dno = forms.ModelChoiceField(queryset=depart.objects.all(), to_field_name='dno')


class ClassEditForm(forms.Form):
    classname = forms.CharField(max_length=10)
    dno = forms.ModelChoiceField(queryset=depart.objects.all(), to_field_name='dno')


class DepartAddForm(forms.Form):
    dno = forms.CharField(max_length=6)
    dname = forms.CharField(max_length=10)
    telephone = forms.CharField(required=False, max_length=15)


class DepartEditForm(forms.Form):
    dname = forms.CharField(max_length=10)
    telephone = forms.CharField(required=False, max_length=15)


class CourseAddForm(forms.Form):
    cno = forms.CharField(max_length=3)
    cname = forms.CharField(max_length=20)
    lecture = forms.FloatField(required=False, min_value=0)
    semester = forms.IntegerField(required=False, min_value=1, max_value=12)
    credit = forms.FloatField(required=False, min_value=0)
    type = forms.ChoiceField(required=False, choices=course.coutype)


class CourseEditForm(forms.Form):
    cname = forms.CharField(max_length=20)
    lecture = forms.FloatField(required=False, min_value=0)
    semester = forms.IntegerField(required=False, min_value=1, max_value=12)
    credit = forms.FloatField(required=False, min_value=0)
    type = forms.ChoiceField(required=False, choices=course.coutype)


class SelectCourseForm(forms.Form):
    cno = forms.ModelChoiceField(queryset=course.objects.all(), to_field_name='cno')


class UpdateGradeForm(forms.Form):
    grade = forms.FloatField(min_value=0, max_value=100)
