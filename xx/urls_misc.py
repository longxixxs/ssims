from django.urls import path

from xx.views_misc import AuditLogListView, DashboardView, chat_view

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('chat/', chat_view, name='chat'),
    path('audit/', AuditLogListView.as_view(), name='audit_list'),
]
