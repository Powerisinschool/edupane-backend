from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models_notification import Notification
from .serializers_notification import NotificationSerializer

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark a specific notification as read"""
        notification = self.get_object()

        # Ensure the notification belongs to the current user
        if notification.user != request.user:
            return Response(
                {'error': 'You can only mark your own notifications as read'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        notification.is_read = True
        notification.save()
        
        return Response({
            'success': True,
            'message': 'Notification marked as read',
            'notification': NotificationSerializer(notification).data
        })

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Mark all notifications for the current user as read"""
        notifications = Notification.objects.filter(user=request.user, is_read=False)
        count = notifications.update(is_read=True)
        
        return Response({
            'success': True,
            'message': f'Marked {count} notifications as read',
            'count': count
        })

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get the count of unread notifications for the current user"""
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        
        return Response({
            'unread_count': count
        })
