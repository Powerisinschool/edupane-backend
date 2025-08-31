from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChatRoomViewSet, MessageViewSet, ChatInviteViewSet

router = DefaultRouter()
router.register(r'chat-rooms', ChatRoomViewSet, basename='chat-room')
router.register(r'messages', MessageViewSet, basename='message')
router.register(r'chat-invites', ChatInviteViewSet, basename='chat-invite')

urlpatterns = [
    path('', include(router.urls)),
]
