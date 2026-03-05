from django.urls import path

from xx.views_users import UserCreateView, UserEditView, UserListView

urlpatterns = [
    path('users/', UserListView.as_view(), name='user_list'),
    path('users/add/', UserCreateView.as_view(), name='user_add'),
    path('users/<int:uid>/edit/', UserEditView.as_view(), name='user_edit'),
]
