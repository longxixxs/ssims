from django.urls import path

from xx.views_academics import (
    ClassAddView,
    ClassDeleteView,
    ClassEditView,
    ClassListView,
    CourseAddView,
    CourseDeleteView,
    CourseEditView,
    CourseListView,
    CourseStudentsView,
    DepartAddView,
    DepartDeleteView,
    DepartEditView,
    DepartListView,
    DropCourseView,
    MarkRetakeView,
    PublishGradeView,
    SelectCourseView,
    StudentCourseView,
    UpdateGradeView,
)

urlpatterns = [
    path('classes/', ClassListView.as_view(), name='class_list'),
    path('classes/add/', ClassAddView.as_view(), name='class_add'),
    path('classes/edit/<str:classno>/', ClassEditView.as_view(), name='class_edit'),
    path('classes/delete/<str:classno>/', ClassDeleteView.as_view(), name='class_delete'),

    path('departs/', DepartListView.as_view(), name='depart_list'),
    path('departs/add/', DepartAddView.as_view(), name='depart_add'),
    path('departs/<str:dno>/edit/', DepartEditView.as_view(), name='depart_edit'),
    path('departs/<str:dno>/delete/', DepartDeleteView.as_view(), name='depart_delete'),

    path('courses/', CourseListView.as_view(), name='course_list'),
    path('courses/add/', CourseAddView.as_view(), name='course_add'),
    path('courses/<str:cno>/edit/', CourseEditView.as_view(), name='course_edit'),
    path('courses/<str:cno>/delete/', CourseDeleteView.as_view(), name='course_delete'),
    path('courses/<str:cno>/students/', CourseStudentsView.as_view(), name='course_students'),

    path('select/<str:sno>/', SelectCourseView.as_view(), name='select_course'),
    path('sc/<str:sno>/', StudentCourseView.as_view(), name='student_course'),
    path('sc/<str:sno>/<str:cno>/grade/', UpdateGradeView.as_view(), name='update_grade'),
    path('sc/<str:sno>/<str:cno>/publish/', PublishGradeView.as_view(), name='publish_grade'),
    path('sc/<str:sno>/<str:cno>/retake/', MarkRetakeView.as_view(), name='mark_retake'),
    path('sc/<str:sno>/<str:cno>/drop/', DropCourseView.as_view(), name='drop_course'),
]
