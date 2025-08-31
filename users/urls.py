from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import UserViewSet, ImageViewSet, UserProfileViewSet, RegisterView, MeView, username_available, validate_teacher_code

router = DefaultRouter()
router.register(r'images', ImageViewSet, basename='image')
router.register(r'users', UserViewSet, basename='user')
router.register(r'profile', UserProfileViewSet, basename='user-profile')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', MeView.as_view(), name='me'),
    path('auth/username-available/', username_available, name='username-available'),
    path('auth/validate-teacher-code/', validate_teacher_code, name='validate-teacher-code'),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path('upload-image/', views.upload_image, name='upload-image'),
    # Legacy endpoints (kept for backward compatibility)
    # path('register/', views.register),
    # path('logout/', views.logout),
    # path('profile/', views.profile),
    # path('profile/update/', views.update_profile),
    # path('profile/delete/', views.delete_profile),
    # path('profile/change-password/', views.change_password),
]
