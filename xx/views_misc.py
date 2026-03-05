import ast
import builtins
import json
import re
from datetime import date, datetime

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Count, Max, Min, Q, Sum
from django.db.models.query import QuerySet
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import ListView

from .models import AuditLog, cl, course, depart, sc, student
from .permissions import RoleRequiredMixin, is_student


class DashboardView(LoginRequiredMixin, RoleRequiredMixin, View):
    template_name = 'dashboard.html'
    allowed_roles = ('admin', 'teacher', 'student')

    def get(self, request):
        if is_student(request.user):
            stu = student.objects.filter(user=request.user).select_related('classno').first()
            if stu is None:
                stu = student.objects.filter(sno=request.user.username).select_related('classno').first()
            records = sc.objects.select_related('cno').filter(sno=stu).order_by('-id') if stu else sc.objects.none()
            graded_records = records.filter(grade__isnull=False)

            total_credit = graded_records.aggregate(total=Sum('cno__credit'))['total'] or 0
            passed_credit = graded_records.filter(grade__gte=60).aggregate(total=Sum('cno__credit'))['total'] or 0
            avg_grade = graded_records.aggregate(avg=Avg('grade'))['avg']

            return render(request, self.template_name, {
                'stu': stu,
                'recent_sc': records[:10],
                'course_count': records.count(),
                'graded_count': graded_records.count(),
                'avg_grade': round(avg_grade, 1) if avg_grade else None,
                'total_credit': round(total_credit, 1),
                'passed_credit': round(passed_credit, 1),
            })

        depart_stat = student.objects.values('classno__dno__dname').annotate(total=Count('sno')).order_by('-total')
        depart_course_stat = sc.objects.values('sno__classno__dno__dname').annotate(
            total=Count('sno', distinct=True)
        ).order_by('-total')
        avg_grade = sc.objects.filter(grade__isnull=False).aggregate(avg=Avg('grade'))['avg']
        recent_sc = sc.objects.select_related('sno', 'cno').order_by('-id')[:10]

        return render(request, self.template_name, {
            'student_total': student.objects.count(),
            'course_total': course.objects.count(),
            'class_total': cl.objects.count(),
            'depart_total': depart.objects.count(),
            'avg_grade': round(avg_grade, 1) if avg_grade else None,
            'depart_stat': depart_stat,
            'depart_course_stat': depart_course_stat,
            'recent_sc': recent_sc,
        })


class AuditLogListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = AuditLog
    template_name = 'audit_list.html'
    context_object_name = 'logs'
    paginate_by = 20
    allowed_roles = ('admin',)

    def get_queryset(self):
        queryset = AuditLog.objects.select_related('actor').order_by('-created_at')

        action = self.request.GET.get('action', '').strip()
        model_name = self.request.GET.get('model', '').strip()
        actor = self.request.GET.get('actor', '').strip()

        if action:
            queryset = queryset.filter(action=action)
        if model_name:
            queryset = queryset.filter(model_name=model_name)
        if actor:
            queryset = queryset.filter(actor_name__icontains=actor)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query_params = self.request.GET.copy()
        if 'page' in query_params:
            del query_params['page']
        context['query_string'] = query_params.urlencode()
        context['model_names'] = (
            AuditLog.objects.order_by('model_name')
            .values_list('model_name', flat=True)
            .distinct()
        )
        context['action_choices'] = AuditLog.ACTION_CHOICES
        return context


class SecurityError(Exception):
    pass


class CodeValidator:
    FORBIDDEN_CALL_NAMES = {
        'eval', 'exec', 'compile', 'open', 'input', 'print',
        '__import__', 'getattr', 'setattr', 'delattr',
        'globals', 'locals', 'vars', 'dir', 'type', 'super',
    }

    FORBIDDEN_METHOD_ATTRS = {
        'delete', 'update', '_update', '_raw_delete',
        'create', 'bulk_create', 'bulk_update',
        'get_or_create', 'update_or_create',
        'save',
        'raw', 'extra',
        'system', 'popen', 'spawn', 'fork',
        'execute',
    }

    @staticmethod
    def validate_ast(code: str) -> bool:
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            raise SecurityError(f'代码语法错误: {exc}')

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                raise SecurityError('禁止使用 import / from')
            if isinstance(node, ast.Try):
                raise SecurityError('禁止使用 try / except')
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                raise SecurityError('禁止定义函数或类或 lambda')
            if isinstance(node, (ast.For, ast.While)):
                raise SecurityError('禁止使用循环语句')
            if isinstance(node, ast.Subscript):
                if isinstance(node.value, ast.Name) and node.value.id == '__builtins__':
                    raise SecurityError('禁止访问 __builtins__ 下标')
            if isinstance(node, ast.Attribute):
                if isinstance(node.attr, str) and node.attr.startswith('__'):
                    raise SecurityError('禁止访问双下划线属性')
            if isinstance(node, ast.Name):
                if node.id in {'__builtins__', '__loader__', '__spec__'}:
                    raise SecurityError(f'禁止使用变量: {node.id}')
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in CodeValidator.FORBIDDEN_CALL_NAMES:
                        raise SecurityError(f'禁止调用函数: {node.func.id}')
                if isinstance(node.func, ast.Attribute):
                    attr = node.func.attr
                    if isinstance(attr, str) and attr.startswith('_'):
                        raise SecurityError('禁止调用下划线开头方法')
                    if attr in CodeValidator.FORBIDDEN_METHOD_ATTRS:
                        raise SecurityError(f'禁止调用方法: {attr}')
                    if isinstance(attr, str) and attr.startswith('__'):
                        raise SecurityError('禁止调用双下划线方法')

        return True


class AICodeExecutor:
    def __init__(self):
        self.safe_builtins = {
            'list', 'dict', 'tuple', 'set',
            'str', 'int', 'float', 'bool',
            'len', 'range', 'enumerate', 'zip',
            'sorted', 'filter', 'map', 'sum',
            'all', 'any', 'min', 'max', 'abs', 'round',
        }

    def execute_ai_code(self, code_string: str, context=None):
        try:
            self._validate_code_safety(code_string)
            exec_globals = self._create_safe_environment()
            if context:
                exec_globals.update(context)
            exec(code_string, exec_globals)
            result = exec_globals.get('result')
            return self._serialize_result(result)
        except Exception as exc:
            return {'error': f'执行失败: {str(exc)}'}

    def _validate_code_safety(self, code: str):
        forbidden_patterns = [
            r'__import__',
            r'open\s*\(',
            r'eval\s*\(',
            r'exec\s*\(',
            r'compile\s*\(',
            r'__builtins__',
        ]
        for pattern in forbidden_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                raise SecurityError(f'检测到不安全代码: {pattern}')

        CodeValidator.validate_ast(code)

    def _create_safe_environment(self):
        safe_builtins_dict = {}
        for name in self.safe_builtins:
            if hasattr(builtins, name):
                safe_builtins_dict[name] = getattr(builtins, name)

        return {
            '__builtins__': safe_builtins_dict,
            'Q': Q,
            'Avg': Avg,
            'Sum': Sum,
            'Count': Count,
            'Max': Max,
            'Min': Min,
            'student': student,
            'cl': cl,
            'depart': depart,
            'course': course,
            'sc': sc,
        }

    def _serialize_result(self, result):
        if result is None:
            return {'type': 'none', 'data': '无结果'}
        if isinstance(result, list) and all(isinstance(r, dict) and 'title' in r and 'data' in r for r in result):
            serialized = []
            for r in result:
                if isinstance(r['data'], QuerySet):
                    r['data'] = list(r['data'][:100])
                r['data'] = make_json_safe(r['data'])
                serialized.append(r)
            return {'type': 'multi', 'data': serialized}
        if isinstance(result, QuerySet):
            data = list(result[:100])
            data = make_json_safe(data)
            return {'type': 'queryset', 'count': result.count(), 'data': data}
        if isinstance(result, (list, dict, tuple)):
            return {'type': type(result).__name__, 'data': make_json_safe(result)}
        if isinstance(result, (str, int, float, bool)):
            return {'type': type(result).__name__, 'data': result}
        return {'type': 'other', 'data': str(result)}


CODE_GENERATION_PROMPT = """
你是一个Django ORM代码生成专家。根据用户需求生成可执行的Python代码。
可用的模型：
class depart(models.Model):
    dno = models.CharField(max_length=6, primary_key=True,null=False)
    dname = models.CharField(max_length=10, null=False)
    telephone = models.CharField(max_length=6,)

class cl(models.Model):
    classno = models.CharField(max_length=6,primary_key=True,)
    classname = models.CharField(max_length=10,null=False)
    dno = models.ForeignKey(depart, on_delete=models.CASCADE)
class student(models.Model):
    stusex = (
        ('girl', '女'),
        ('boy', '男'),
    )
    sno = models.CharField(max_length=10, primary_key=True,null=False)
    sname = models.CharField(max_length=10, null=False)
    sex = models.CharField(max_length=4,choices=stusex, default='girl')
    native = models.CharField(max_length=20,)
    age = models.IntegerField(null=True)
    classno = models.ForeignKey(cl, on_delete=models.CASCADE)
    entime = models.DateTimeField(null=True,auto_now=True)
    semester = models.IntegerField(null=True)
    home = models.CharField(max_length=40,)
    telephone = models.CharField(max_length=20, )
class course(models.Model):
    coutype = (
        ('crc', '公共课'),
        ('bcim', '专业基础课'),
        ('spc', '专业课'),
        ('ocos', '选修课')
    )
    cno = models.CharField(max_length=3, primary_key=True,null=False)
    cname = models.CharField(max_length=20, null=False)
    lecture = models.FloatField(null=True)
    semester = models.IntegerField(null=True)
    credit = models.FloatField(null=True)
    type = models.CharField(max_length=10,null = True,choices=coutype,default='crc')
class sc(models.Model):
    sno = models.ForeignKey(student, on_delete=models.CASCADE)
    cno = models.ForeignKey(course, on_delete=models.CASCADE)
    grade = models.FloatField(null=True)
生成要求：
如果返回多个模型的数据，请使用列表，每个元素包含 title 和 data
严格按照上面给出的模型以及字段名来进行编写代码，不允许假设，不允许更改。
1. 只使用Django ORM查询，不要使用原始SQL
2. 查询结果必须赋值给变量 `result`
3. 代码必须安全，不能包含文件操作、系统调用等
4. 优先使用values()获取字典格式数据
5. 不需要异常处理，直接写查询并赋值 result
6. 不允许出现 import / from / print / try / except
7. 不允许定义函数或类
8. 可以直接使用：student, cl, depart, course, sc, Q, Count, Avg, Sum
10.你可以使用跨表的多表查询
11.course 模型 type 字段合法取值：
- "crc" → 公共课
- "bcim" → 专业基础课
- "spc" → 专业课
- "ocos" → 选修课
前者是具体的值，后者是前者的含义
示例：
用户：查询所有男生信息
代码：
result = student.objects.filter(sex='boy').values('sno', 'sname', 'age')
用户：统计每个班级的学生人数
代码：
result = list(student.objects.values('classno__classname').annotate(count=Count('sno')))

现在请为以下需求生成代码：
用户需求：{user_query}
"""


def get_ai_response(messages):
    url = f"{settings.AI_BASE_URL}/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.AI_API_KEY}",
    }
    payload = {"model": settings.AI_MODEL, "messages": messages}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 401:
            raise RuntimeError("AI接口返回 401 未认证：请检查 DeepSeek API Key 是否配置正确、是否带在 Authorization 头里。")
        if not response.ok:
            raise RuntimeError(f"AI接口返回非成功状态码 {response.status_code}，内容: {response.text[:200]}")
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as exc:
        raise RuntimeError(f"AI调用失败: {str(exc)}")


def extract_code_from_response(text: str) -> str:
    if not text:
        return ""

    code_match = re.search(r'```(?:python|py)?\s*\r?\n(.*?)\r?\n```', text, re.DOTALL | re.IGNORECASE)
    if code_match:
        return code_match.group(1).strip()

    lines = text.splitlines()
    code_lines = []
    in_code = False
    for line in lines:
        if line.strip().startswith("```") and in_code:
            break
        if any(k in line for k in ['result =', 'result=', 'def ', 'class ', 'import ', 'from ']):
            in_code = True
        if in_code:
            if re.match(r'^\s*(解释|说明|注意|结果|输出|AI回复|以下是)\s*[:：]?\s*$', line.strip()):
                break
            if line.strip() and not line.lstrip().startswith('#'):
                code_lines.append(line)
    return '\n'.join(code_lines).strip() if code_lines else text.strip()


def format_execution_result(result):
    if 'error' in result:
        return json.dumps([{"error": result['error']}], ensure_ascii=False)
    if result.get('type') == 'multi' and isinstance(result.get('data'), list):
        formatted_data = []
        for tbl in result['data']:
            if isinstance(tbl, dict) and 'title' in tbl and 'data' in tbl:
                formatted_data.append({'title': tbl['title'], 'data': tbl['data']})
        return json.dumps([{'type': 'multi', 'data': formatted_data}], ensure_ascii=False)
    if result.get('type') == 'queryset' and isinstance(result.get('data'), list):
        return json.dumps([{
            'type': 'queryset',
            'count': result.get('count', len(result['data'])),
            'data': result['data'],
        }], ensure_ascii=False)
    if result.get('type') in ('list', 'dict', 'tuple'):
        return json.dumps([{'type': result['type'], 'data': result['data']}], ensure_ascii=False)
    if result.get('type') in ('str', 'int', 'float', 'bool'):
        return json.dumps([{'type': result['type'], 'data': result['data']}], ensure_ascii=False)
    return json.dumps([{'type': 'other', 'data': str(result.get('data'))}], ensure_ascii=False)


def make_json_safe(obj):
    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [make_json_safe(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(make_json_safe(v) for v in obj)
    if isinstance(obj, (datetime, date)):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    if hasattr(obj, '__dict__'):
        return {k: make_json_safe(v) for k, v in obj.__dict__.items() if not k.startswith('_')}
    return obj


@login_required
def chat_view(request):
    if is_student(request.user):
        messages.error(request, '无权限访问')
        return redirect('dashboard')
    if not request.user.groups.filter(name__in=['admin', 'teacher']).exists() and not request.user.is_superuser:
        messages.error(request, '无权限访问')
        return redirect('dashboard')

    if request.GET.get("clear") == "1":
        request.session["chat_messages"] = [
            {
                "role": "system",
                "content": """你是一个Django ORM代码生成助手。根据用户需求生成可直接执行的Python代码。
    代码应该简洁、安全，并且将结果赋值给变量`result`。
    可用的模型：student, cl, depart, course, sc。
    使用Django ORM进行查询，不要使用原始SQL。"""
            },
            {
                "role": "assistant",
                "content": "你好我是你的AI助手，我可以帮助你完成查询工作！"
            }
        ]
        request.session.modified = True
        return redirect('chat')

    if "chat_messages" not in request.session:
        request.session["chat_messages"] = [{
            "role": "system",
            "content": """你是一个Django ORM代码生成助手。根据用户需求生成可直接执行的Python代码。
代码应该简洁、安全，并且将结果赋值给变量`result`。
可用的模型：student, cl, depart, course, sc。
使用Django ORM进行查询，不要使用原始SQL。"""
        }]

    executor = AICodeExecutor()
    if request.method == "POST":
        user_input = request.POST.get("message", "").strip()
        if not user_input:
            return render(request, "chat.html", {"messages": request.session["chat_messages"]})
        request.session["chat_messages"].append({"role": "user", "content": user_input})
        try:
            prompt = CODE_GENERATION_PROMPT.format(user_query=user_input)
            ai_response = get_ai_response([
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_input},
            ])
            code = extract_code_from_response(ai_response)
            if 'cno__cname' in code:
                code = code.replace(
                    "values('cno__cname')",
                    "values_list('cno__cname', flat=True)",
                )
            execution_result = executor.execute_ai_code(code)
            if 'error' in execution_result:
                reply = f"执行错误:\n{execution_result['error']}\n\n生成的代码:\n```python\n{code}\n```"
            else:
                reply = format_execution_result(execution_result)
        except Exception as exc:
            reply = f"处理失败:\n{str(exc)}\n\nAI回复:\n{ai_response if 'ai_response' in locals() else '无'}"
        request.session["chat_messages"].append({"role": "assistant", "content": reply})
        request.session.modified = True
    return render(request, "chat.html", {"messages": request.session["chat_messages"]})

