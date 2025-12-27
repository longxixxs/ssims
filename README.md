# Django 学生信息管理系统/SSIMS/简单学生信息管理系统

## 📌 项目简介
本项目是一个基于 Django 框架开发的学生信息管理系统，涵盖学生、班级、系部、课程及选课管理等核心业务功能，并集成 AI 辅助查询模块，可根据自然语言自动生成并安全执行 Django ORM 查询语句。

适用于 Django 课程设计、数据库课程设计及综合实训项目。

---

## 🛠 技术栈
- Python 3.13
- Django 5.x
- MySQL
- Django ORM
- HTML / CSS / JavaScript
- Bootstrap（前端样式）
- openpyxl（Excel 导入导出）
- DeepSeek API（AI 查询助手）
---

## 🚀 环境部署与运行

### 1️⃣ 下载项目

点击绿色Code 按钮 

———Download ZIP———

解压压缩包，使用Pycharm 打开SSIMS-master文件夹  

或者使用PyCharm克隆 

```
https://github.com/longxixxs/SSIMS.git
```

### 2️⃣ 创建并激活虚拟环境（推荐）

PyCharm右下角选择新建虚拟环境  选择Python 3.13版本 

### 3️⃣ 安装依赖
依据requirements.txt 下载所需要的依赖包
终端输入
```
pip install -r requirements.txt
```
### 4️⃣ 关键参数配置

请在 settings.py 中配置 MySQL 数据库信息：
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': '数据库名',
        'USER': '用户名',
        'PASSWORD': '密码',
        'HOST': 'localhost',
        'PORT': '3306',
    }
	}
```

```python
AI_API_KEY = "大模型 API"
AI_BASE_URL = "AI大模型调用接口"
AI_MODEL = "你的模型"
```

### 5️⃣ 数据库迁移
终端输入
```
python manage.py makemigrations
python manage.py migrate
```
### 6️⃣ 启动项目
终端输入
```
python manage.py runserver
```
浏览器访问：
```
http://127.0.0.1:8000/
```
### ✨部署运行说明

当遇到问题时，不妨问问AI?

AI是很好的学习工具！

### 🔐 登录说明

登录页面：/login/
注册页面：/register/
AI 查询助手：/chat/
## ✨ 功能模块

### 🔐 用户模块
- 用户注册 / 登录 / 登出
- 修改密码
- 登录权限控制（LoginRequired）

### 👨‍🎓 学生管理
- 学生信息增删改查
- 多条件筛选（学号 / 姓名 / 性别 / 班级）
- 排序（学号 / 姓名 / 年龄 / 班级 / 学期）
- 学生详情（选课、成绩、学分统计）
- Excel 批量导入 / 导出

### 🏫 班级与系部管理
- 系部信息管理
- 班级信息管理

### 📚 课程与选课管理
- 课程信息管理
- 学生选课（防重复选课）
- 成绩录入与修改
- 学分、平均成绩统计

### 📊 数据统计仪表盘
- 学生总数 / 班级数 / 课程数 / 系部数
- 系部学生人数统计
- 系部选课人数统计
- 平均成绩分析
- 最近选课记录

### 🤖 AI 查询助手
- 支持自然语言查询
- 自动生成 Django ORM 查询代码
- AST + 正则双重安全校验
- 严格限制危险函数与模块
- 查询结果自动格式化展示

---

⚠️ 安全说明
本项目没有任何安全技术，请在任何环境下都勿进行生产活动。
🎓 说明

本项目为 Django Web 开发课程设计作品，完整实现学生信息管理业务流程，并结合 AI 技术提升数据查询效率。

📌 作者

作者：晓小事 LxXxs Longxixxs
联系方式：lxxxs@foxmail.com
用途：课程设计 / 学习交流

