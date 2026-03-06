# SSIMS

基于 Django 的学生信息管理系统，当前覆盖账号审批、学生档案、教务管理、选课与成绩流程、审计日志，以及受限 AI 查询助手。

## 当前状态

- 推荐 Python 版本：`3.13`
- Django 版本：`6.0.3`
- 默认数据库：`SQLite`（`db.sqlite3`）
- 当前最新业务迁移：`xx.0006_selectionhistory_studentimportjob_and_more`
- 本地验证结果：`py -3.13 manage.py test`，`40` 项测试全部通过

## 主要功能

### 账号与权限

- 提供登录、登出、注册、修改密码页面。
- 注册只创建 `pending` 账号，不会自动授予角色。
- 管理员可在用户管理页面审批账号，并设置角色与状态。
- 受管角色为 `admin`、`teacher`、`student`。
- 账号状态为 `pending`、`active`、`disabled`。
- 教师权限按负责班级和负责课程收口，不是全局教师权限。

### 用户管理

- 仅管理员可访问用户列表、待审批列表、用户新增、用户编辑。
- 一个账号只允许一个受管角色。
- `student` 角色必须关联有效学生档案。
- 创建或编辑用户时可同步创建/恢复学生档案。
- 教师账号必须分配至少一个负责班级或课程。

### 学生档案

- 学生新增、编辑、列表筛选、详情查看。
- 学生记录使用归档语义，不做业务硬删除。
- 归档学生时支持三种账号处理方式：
  - 停用账号
  - 设为待审核
  - 解绑账号
- 学号默认可作为学生登录名。
- 学生默认初始密码仍为 `psw123456`。
- 支持 Excel 导入与导出。

### Excel 导入

- 导入文件格式为 `.xlsx`。
- 使用两阶段流程：
  1. 预检
  2. 确认执行
- 支持两种模式：
  - `create`：新增模式
  - `update`：更新模式
- 每次导入都会生成 `StudentImportJob`，保存预检结果、错误行、汇总信息和执行时间。

### 教务管理

- 系部、班级、课程均支持新增、编辑、归档。
- 归档前会检查活跃下游依赖：
  - 系部下仍有有效班级时不能归档
  - 班级下仍有有效学生时不能归档
  - 课程下仍有有效选课记录时不能归档
- 教师查看到的系部、班级、课程列表均受分配范围限制。

### 选课与成绩

`sc` 记录当前是显式状态流，而不是单纯“选课 + 分数”：

- `selection_status`
  - `active`
  - `dropped`
- `grade_status`
  - `pending`
  - `draft`
  - `published`
  - `retake`

支持的动作：

- 选课
- 退课
- 保存成绩草稿
- 发布成绩
- 标记重修
- 查看成绩历史

当前业务规则：

- `(sno, cno)` 唯一，不允许重复记录。
- 成绩范围限制为 `0-100`。
- 已发布成绩会锁定，不能直接修改。
- 已发布成绩不能退课。
- 统计口径只计算“有效选课 + 已发布成绩”。

### 仪表盘、审计与 AI

- 仪表盘按角色展示统计信息。
- 关键新增、修改、归档操作会写入 `AuditLog`。
- AI 助手只对管理员和教师开放。
- AI 助手通过自然语言生成受限 Django ORM 代码。
- 执行前有 AST 校验和关键字过滤，禁止危险调用。

## 关键模型

- `UserAccount`：账号状态、审批信息
- `TeacherClassAssignment`：教师负责班级
- `TeacherCourseAssignment`：教师负责课程
- `student`：学生档案
- `depart` / `cl` / `course`：系部、班级、课程
- `sc`：选课与成绩记录
- `SelectionHistory`：选课/成绩流程历史
- `StudentImportJob`：学生 Excel 导入任务
- `AuditLog`：审计日志

## 路由结构

- `xx/urls_auth.py`：登录、登出、注册、修改密码
- `xx/urls_users.py`：用户列表、审批、创建、编辑
- `xx/urls_students.py`：学生列表、详情、编辑、归档、导入导出
- `xx/urls_academics.py`：系部、班级、课程、选课、成绩
- `xx/urls_misc.py`：仪表盘、审计日志、AI 助手

聚合入口在 `xx/urls.py`，项目入口在 `ssims/urls.py`。

## 目录结构

```text
ssims/
├─ manage.py
├─ README.md
├─ requirements.txt
├─ db.sqlite3
├─ ssims/
│  ├─ settings.py
│  ├─ urls.py
│  ├─ wsgi.py
│  └─ asgi.py
├─ xx/
│  ├─ models.py
│  ├─ forms.py
│  ├─ permissions.py
│  ├─ audit.py
│  ├─ view_shared.py
│  ├─ views_auth.py
│  ├─ views_users.py
│  ├─ views_students.py
│  ├─ views_academics.py
│  ├─ views_misc.py
│  ├─ urls_auth.py
│  ├─ urls_users.py
│  ├─ urls_students.py
│  ├─ urls_academics.py
│  ├─ urls_misc.py
│  ├─ tests.py
│  └─ migrations/
├─ templates/
└─ static/
```

## 本地启动

以下示例为 Windows PowerShell：

### 1. 创建虚拟环境

```powershell
py -3.13 -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. 安装依赖

```powershell
python -m pip install -r requirements.txt
```

### 3. 执行迁移

```powershell
python manage.py migrate
```

### 4. 启动开发服务器

```powershell
python manage.py runserver
```

默认地址：`http://127.0.0.1:8000/`

## 常用命令

```powershell
python manage.py check
python manage.py showmigrations xx
python manage.py test
python manage.py makemigrations
```

如果未激活虚拟环境，可直接使用：

```powershell
py -3.13 manage.py test
```

## 当前测试覆盖

`xx/tests.py` 当前覆盖的主要场景：

- 注册与待审核账号登录限制
- 停用账号登录限制
- 学生、教师登录跳转
- 登出请求方法限制
- 用户创建、编辑、审批队列
- 教师负责班级/课程归属
- 学生档案归档与账号联动
- Excel 导入预检与执行
- Excel 导出范围控制
- 系部、班级、课程归档保护
- 教师权限边界
- 选课、退课、成绩录入、发布、重修
- 已发布 `0` 分统计
- 审计日志与 AI 助手页面权限

## AI 配置

AI 配置当前写在 `ssims/settings.py`：

```python
AI_API_KEY = "your-api-key"
AI_BASE_URL = "your base url"
AI_MODEL = "your model"
```

未配置有效值时，AI 页面无法正常调用外部模型接口。

## 当前配置注意事项

1. `DEBUG = True`，当前配置只适合本地开发。
2. `ALLOWED_HOSTS = []`，如需其他主机名访问需要自行补充。
3. 学生默认密码策略仍然存在，属于需要优先收敛的安全项。
4. AI 助手虽然做了限制，但本质上仍是受限代码执行能力，建议只在受控环境启用。
5. 仓库内已存在 `db.sqlite3`、`venv/`、`__pycache__/` 等本地文件，提交前建议清理版本控制范围。
