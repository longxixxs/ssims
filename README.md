# SSIMS 学生信息管理系统

基于 Django 的单体 Web 系统，包含用户与权限、学生档案、教务（系部/班级/课程/选课/成绩）、审计日志与 AI 查询助手。

## 1. 技术栈与运行基线

- Python：`3.11.5`
- Django：`5.2.7`
- 默认数据库：`SQLite`（`db.sqlite3`）
- 自动化测试：`31` 项（`python manage.py test`）

## 2. 功能清单

### 2.1 认证与账号

- 登录 / 登出 / 注册 / 修改密码
- 角色模型：`admin`、`teacher`、`student`
- 注册仅创建待审核账号（不分配角色），管理员审核后才能进入业务页面

### 2.2 用户管理（管理员）

- 账号列表、搜索、按角色筛选
- 创建账号、编辑账号、分配单一受管角色
- 支持在创建/编辑时同步创建学生档案（仅 `student` 角色允许）

### 2.3 学生管理

- 学生信息 CRUD、筛选、排序、详情
- Excel 导入 / 导出
- 学生账号策略：
  - 登录名默认使用学号（`sno`）
  - 初始密码固定为 `psw123456`
  - 学生首次登录后可在“修改密码”页自行修改
- 删除学生档案时，会移除绑定账号的 `student` 角色，避免角色残留

### 2.4 教务管理

- 系部、班级、课程管理
- 学生选课（数据库唯一约束防重复）
- 成绩录入与修改（范围 `0-100`）
- 仪表盘统计（学生数、课程数、均分、近期记录等）

### 2.5 审计与 AI 助手

- 关键增删改记录到审计日志
- AI 查询助手支持自然语言转 ORM 查询并执行
- 代码执行前有 AST + 关键字双重安全校验，限制危险调用

## 3. 核心业务规则

1. 每个账号仅允许一个受管角色（`admin/teacher/student`）。
2. `student` 角色必须关联学生档案。
3. 注册账号默认无角色，登录会提示“待审核”。
4. 学生默认凭据为 `学号 + psw123456`。
5. 选课记录唯一键为 `(sno, cno)`，不允许重复选课。
6. 成绩只能在 `0-100`。
7. 用户管理与审计页面仅管理员可访问。

## 4. 架构说明（按业务域拆分）

### 4.1 路由层

- 聚合入口：`xx/urls.py`
- 分域路由：
  - `xx/urls_auth.py`
  - `xx/urls_users.py`
  - `xx/urls_students.py`
  - `xx/urls_academics.py`
  - `xx/urls_misc.py`

### 4.2 视图层

- 分域实现：
  - `xx/views_auth.py`
  - `xx/views_users.py`
  - `xx/views_students.py`
  - `xx/views_academics.py`
  - `xx/views_misc.py`
- 共享逻辑：`xx/view_shared.py`
- 兼容导出层：`xx/views.py`（集中 re-export）

### 4.3 校验与权限

- 统一输入校验：`xx/forms.py`
- 权限与角色判断：`xx/permissions.py`
- 审计写入：`xx/audit.py`

## 5. 快速开始

### 5.1 获取代码

```bash
git clone https://github.com/longxixxs/ssims.git
cd ssims
```

### 5.2 创建虚拟环境并安装依赖

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS / Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### 5.3 配置（可选）

如需启用 AI 助手，请在 `ssims/settings.py` 设置：

```python
AI_API_KEY = "your-api-key"
AI_BASE_URL = "your-base-url"
AI_MODEL = "your-model"
```

### 5.4 初始化数据库并启动

```bash
python manage.py migrate
python manage.py runserver
```

访问地址：

- 首页：`http://127.0.0.1:8000/`
- 登录：`/login/`
- 注册：`/register/`

## 6. 测试与质量检查

```bash
python manage.py check
python manage.py test
```

当前测试基线（本地）：

- `Found 31 test(s).`
- `Ran 31 tests ... OK`

测试覆盖矩阵（按 `xx/tests.py`）：

| 测试类 | 覆盖功能 |
| --- | --- |
| `AuthAndPasswordTests` | 登录、注册待审核、登出方法限制、改密、学生默认密码登录 |
| `UserManagementTests` | 用户列表权限、创建/编辑用户、学生角色与档案联动 |
| `StudentManagementTests` | 学生 CRUD、删除后角色清理、导入导出、学生自访问限制 |
| `AcademicCrudAndPermissionTests` | 系部/班级/课程 CRUD、教师只读权限 |
| `SelectionAndGradeTests` | 选课、防重复、成绩录入与范围校验 |
| `FormPageSmokeTests` | 管理员表单页面可达性 |
| `DashboardAuditAndChatTests` | 仪表盘、审计权限与筛选、聊天助手权限和流程 |

## 7. 常见问题

### 7.1 为什么注册后不能直接登录业务页？

注册只会创建“待审核”账号，不会自动授予角色；管理员分配角色后才能正常进入业务页面。

### 7.2 学生默认账号密码是什么？

- 用户名：学号（例如 `S0001`）
- 密码：`psw123456`

仅当该学号已由系统创建/绑定学生账号时可直接登录。建议登录后立即修改密码。

## 8. 目录结构

```text
ssims/
├─ ssims/                 # Django 项目配置（settings/urls/wsgi/asgi）
├─ xx/                    # 主业务应用
│  ├─ urls*.py            # 按域拆分路由
│  ├─ views_*.py          # 按域拆分视图
│  ├─ view_shared.py      # 共享业务逻辑
│  ├─ forms.py            # 表单与输入校验
│  ├─ models.py           # 数据模型
│  ├─ permissions.py      # 权限控制
│  └─ tests.py            # 自动化测试
├─ templates/             # 页面模板
├─ static/                # 静态资源
├─ manage.py
└─ requirements.txt
```

## 9. 开发注意事项

- 当前配置 `DEBUG=True`，仅适合本地开发/教学场景。
- 不要提交敏感信息（API Key、生产密码等）。
- 建议将 `db.sqlite3`、`__pycache__/`、`.venv/` 排除在版本控制之外。

## 10. 许可证

项目遵循 `LICENSE` 文件中的许可条款。
