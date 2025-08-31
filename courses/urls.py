from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CourseViewSet, ModuleViewSet, LessonViewSet, CategoryViewSet,
    EnrollmentViewSet, MaterialViewSet, 
    FeedbackViewSet, StatusUpdateViewSet
)
from .views_notification import NotificationViewSet

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'modules', ModuleViewSet, basename='module')
router.register(r'lessons', LessonViewSet, basename='lesson')
router.register(r'enrollments', EnrollmentViewSet, basename='enrollment')
router.register(r'materials', MaterialViewSet, basename='material')
# router.register(r'deadlines', DeadlineViewSet, basename='deadline')
router.register(r'feedbacks', FeedbackViewSet, basename='feedback')
router.register(r'status-updates', StatusUpdateViewSet, basename='status-update')
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
]
