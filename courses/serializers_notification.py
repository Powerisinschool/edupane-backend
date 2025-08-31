from rest_framework import serializers
from .models_notification import Notification

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'message', 'created_at', 'is_read']
        read_only_fields = ['id', 'created_at']
