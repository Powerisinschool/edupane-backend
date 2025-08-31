from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
    path('', include('courses.urls')),
    path('', include('users.urls')),
    path('', include('messaging.urls')),
    path('hello/', views.hello_world),
    path('dashboard/', views.dashboard_data, name='dashboard-data'),
    path('dashboard/post-status/', views.post_status, name='post-status'),
    path('dashboard/accept-invite/', views.accept_invite, name='accept-invite'),
    path('dashboard/decline-invite/', views.decline_invite, name='decline-invite'),
    path('feed/', views.feed, name='feed'),
    path('feed/create/', views.create_status_update, name='create-status-update'),
]
