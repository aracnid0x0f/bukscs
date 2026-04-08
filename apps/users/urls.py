from django.urls import path
from . import views

urlpatterns = [
    path('dispatch/', views.role_dispatch, name='role_dispatch'),
]