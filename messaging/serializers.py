from rest_framework import serializers
from .models import ChatRoom, Membership, Message, ChatInvite
from users.serializers import UserSerializer

class MembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Membership
        fields = '__all__'

class ChatRoomSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    participants = UserSerializer(many=True, read_only=True)
    memberships = MembershipSerializer(many=True, read_only=True)
    latest_message = serializers.SerializerMethodField()
    participant_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = '__all__'
        
    def get_latest_message(self, obj):
        latest = obj.messages.first()
        if latest:
            return MessageSerializer(latest).data
        return None
    
    def get_participant_count(self, obj):
        return obj.participants.count()

class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    
    class Meta:
        model = Message
        fields = '__all__'

class ChatInviteSerializer(serializers.ModelSerializer):
    room = ChatRoomSerializer(read_only=True)
    inviter = UserSerializer(read_only=True)
    invited = UserSerializer(read_only=True)
    
    class Meta:
        model = ChatInvite
        fields = '__all__'
