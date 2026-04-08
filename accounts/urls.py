from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('password-reset-required/', views.password_reset_required_view, name='password_reset_required'),
    path('bulk-upload/', views.bulk_upload_view, name='bulk_upload'),
]
