# xx/urls.py
from django.urls import path
from xx import views

app_name = 'xx'  # ✅ 必须添加这一行！

urlpatterns = [
    # ==================== 用户认证 ====================
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    path('register/', views.UserRegisterView.as_view(), name='register'),
    path('password/', views.UserPasswordView.as_view(), name='password'),

    # ==================== 仪表盘 ====================
    path('', views.DashboardView.as_view(), name='dashboard'),

    # ==================== 学生管理 ====================
    path('students/', views.StudentListView.as_view(), name='student_list'),
    path('students/add/', views.StudentAddView.as_view(), name='student_add'),
    path('students/import/excel/', views.StudentImportExcelView.as_view(), name='student_import_excel'),
    path('students/export/excel/', views.StudentExportExcelView.as_view(), name='student_export_excel'),
    path('students/<str:sno>/', views.StudentDetailView.as_view(), name='student_detail'),
    path('students/<str:sno>/edit/', views.StudentEditView.as_view(), name='student_edit'),
    path('students/<str:sno>/delete/', views.StudentDeleteView.as_view(), name='student_delete'),

    # ==================== 班级管理 ====================
    path('classes/', views.ClassListView.as_view(), name='class_list'),
    path('classes/add/', views.ClassAddView.as_view(), name='class_add'),
    path('classes/edit/<str:classno>/', views.ClassEditView.as_view(), name='class_edit'),
    path('classes/delete/<str:classno>/', views.ClassDeleteView.as_view(), name='class_delete'),

    # ==================== 系部管理 ====================
    path('departs/', views.DepartListView.as_view(), name='depart_list'),
    path('departs/add/', views.DepartAddView.as_view(), name='depart_add'),
    path('departs/<str:dno>/edit/', views.DepartEditView.as_view(), name='depart_edit'),
    path('departs/<str:dno>/delete/', views.DepartDeleteView.as_view(), name='depart_delete'),

    # ==================== 课程管理 ====================
    path('courses/', views.CourseListView.as_view(), name='course_list'),
    path('courses/add/', views.CourseAddView.as_view(), name='course_add'),
    path('courses/<str:cno>/edit/', views.CourseEditView.as_view(), name='course_edit'),
    path('courses/<str:cno>/delete/', views.CourseDeleteView.as_view(), name='course_delete'),
    path('courses/<str:cno>/students/', views.CourseStudentsView.as_view(), name='course_students'),

    # ==================== 选课与成绩管理 ====================
    path('select/<str:sno>/', views.SelectCourseView.as_view(), name='select_course'),
    path('sc/<str:sno>/', views.StudentCourseView.as_view(), name='student_course'),
    path('sc/<str:sno>/<str:cno>/grade/', views.UpdateGradeView.as_view(), name='update_grade'),

    # ==================== AI助手 ====================
    path('chat/', views.chat_view, name='chat')
]
