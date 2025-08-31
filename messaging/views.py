from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Max, Subquery, OuterRef
from django.utils import timezone
from .models import ChatRoom, Membership, Message, ChatInvite
from .serializers import ChatRoomSerializer, MembershipSerializer, MessageSerializer, ChatInviteSerializer
from users.models import User

class ChatRoomViewSet(viewsets.ModelViewSet):
    queryset = ChatRoom.objects.all()
    serializer_class = ChatRoomSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # Return rooms where user is owner or participant
        return ChatRoom.objects.filter(
            Q(owner=user) | Q(participants=user)
        ).annotate(
            latest_message_time=Max('messages__timestamp')
        ).order_by('-latest_message_time').distinct()
    
    def perform_create(self, serializer):
        user = self.request.user
        room = serializer.save(owner=user)
        # Add creator as admin member
        Membership.objects.create(
            user=user,
            room=room,
            role='admin' if user.is_teacher() else 'student'
        )
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Get messages for a room"""
        room = self.get_object()
        
        # Check if user has access
        if not room.is_participant(request.user) and room.owner != request.user:
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Get pagination parameters
        before_id = request.query_params.get('before_id')
        limit = int(request.query_params.get('limit', 50))
        
        messages = Message.objects.filter(room=room).order_by('-timestamp')
        
        if before_id:
            messages = messages.filter(id__lt=before_id)
        
        messages = messages[:limit]
        
        return Response({
            'messages': MessageSerializer(messages, many=True).data,
            'has_more': messages.count() == limit
        })
    
    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Send a message to a room"""
        room = self.get_object()
        
        # Check if user has access
        if not room.is_participant(request.user) and room.owner != request.user:
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
        
        content = request.data.get('content', '').strip()
        if not content:
            return Response({'error': 'Message content is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        message = Message.objects.create(
            room=room,
            sender=request.user,
            content=content
        )
        
        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def invite_user(self, request, pk=None):
        """Invite a user to join the room"""
        room = self.get_object()
        
        # Check permissions - only owner or admins can invite
        if room.owner != request.user:
            membership = Membership.objects.filter(user=request.user, room=room).first()
            if not membership or not membership.is_admin():
                return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'User ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            invited_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if user is already in the room
        if room.is_participant(invited_user):
            return Response({'error': 'User is already in the room'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create or get invite
        invite, created = ChatInvite.objects.get_or_create(
            room=room,
            invited=invited_user,
            defaults={'inviter': request.user}
        )
        
        return Response({
            'success': True,
            'message': 'Invite sent' if created else 'Invite already exists',
            'invite': ChatInviteSerializer(invite).data
        })
    
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Join a public room"""
        room = self.get_object()
        
        if not room.is_public():
            return Response({'error': 'Room is not public'}, status=status.HTTP_403_FORBIDDEN)
        
        if room.is_participant(request.user):
            return Response({'error': 'Already a member'}, status=status.HTTP_400_BAD_REQUEST)
        
        membership = Membership.objects.create(
            user=request.user,
            room=room,
            role='student' if request.user.is_student() else 'teacher'
        )
        
        return Response({
            'success': True,
            'membership': MembershipSerializer(membership).data
        })
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Leave a room"""
        room = self.get_object()
        
        if room.owner == request.user:
            return Response({'error': 'Room owner cannot leave'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            membership = Membership.objects.get(user=request.user, room=room)
            membership.delete()
            return Response({'success': True})
        except Membership.DoesNotExist:
            return Response({'error': 'Not a member'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def create_direct_chat(self, request):
        """Create a direct chat with another user"""
        other_user_id = request.data.get('user_id')
        if not other_user_id:
            return Response({'error': 'User ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            other_user = User.objects.get(id=other_user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if other_user == request.user:
            return Response({'error': 'Cannot create direct chat with yourself'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get or create direct chat
        room = ChatRoom.get_or_create_direct_chat(request.user, other_user)
        
        return Response(ChatRoomSerializer(room).data)

class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # Only show messages from rooms user has access to
        return Message.objects.filter(
            Q(room__owner=user) | Q(room__participants=user)
        ).distinct()

class ChatInviteViewSet(viewsets.ModelViewSet):
    queryset = ChatInvite.objects.all()
    serializer_class = ChatInviteSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        return ChatInvite.objects.filter(
            Q(invited=user) | Q(inviter=user)
        )
    
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Accept a chat invite"""
        invite = self.get_object()
        
        if invite.invited != request.user:
            return Response({'error': 'Not your invite'}, status=status.HTTP_403_FORBIDDEN)
        
        if invite.status != 'pending':
            return Response({'error': 'Invite already responded to'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create membership
        membership, created = Membership.objects.get_or_create(
            user=request.user,
            room=invite.room,
            defaults={'role': 'student' if request.user.is_student() else 'teacher'}
        )
        
        # Update invite
        invite.status = 'accepted'
        invite.responded_at = timezone.now()
        invite.save()
        
        return Response({
            'success': True,
            'membership': MembershipSerializer(membership).data
        })
    
    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        """Decline a chat invite"""
        invite = self.get_object()
        
        if invite.invited != request.user:
            return Response({'error': 'Not your invite'}, status=status.HTTP_403_FORBIDDEN)
        
        if invite.status != 'pending':
            return Response({'error': 'Invite already responded to'}, status=status.HTTP_400_BAD_REQUEST)
        
        invite.status = 'rejected'
        invite.responded_at = timezone.now()
        invite.save()
        
        return Response({'success': True})
