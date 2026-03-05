from django.urls import path

from xx.views_auth import UserLoginView, UserLogoutView, UserPasswordView, UserRegisterView

urlpatterns = [
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('register/', UserRegisterView.as_view(), name='register'),
    path('password/', UserPasswordView.as_view(), name='password'),
]
