from django.urls import path

from xx.views_students import (
    StudentAddView,
    StudentDeleteView,
    StudentDetailView,
    StudentEditView,
    StudentExportExcelView,
    StudentImportExcelView,
    StudentListView,
)

urlpatterns = [
    path('students/', StudentListView.as_view(), name='student_list'),
    path('students/add/', StudentAddView.as_view(), name='student_add'),
    path('students/import/excel/', StudentImportExcelView.as_view(), name='student_import_excel'),
    path('students/export/excel/', StudentExportExcelView.as_view(), name='student_export_excel'),
    path('students/<str:sno>/', StudentDetailView.as_view(), name='student_detail'),
    path('students/<str:sno>/edit/', StudentEditView.as_view(), name='student_edit'),
    path('students/<str:sno>/delete/', StudentDeleteView.as_view(), name='student_delete'),
]
