from django.db import models
from users.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

ROLE_CHOICES = [
    ("admin", "Admin"),  # full control over the room
    ("moderator", "Moderator"),  # can moderate messages
    ("teacher", "Teacher"), # can manage course-related rooms
    ("rep", "Student Rep"),  # elevated responsibility
    ("arep", "Assistant Student Rep"), # assistant to the student rep
    ("student", "Student"), # regular participant
    ("observer", "Observer"),  # can view but not interact
]

class ChatRoom(models.Model):
    ROOM_TYPE_CHOICES = [
        ('public', 'Public'), # Things like announcements or general discussions
        ('private', 'Private'), # Private rooms for specific courses or groups
        ('group', 'Group'), # Group chats for multiple users
        ('direct', 'Direct'), # Direct messages between two users
    ]
    id = models.AutoField(primary_key=True, editable=False)
    name = models.CharField(max_length=255, blank=True, null=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_chat_rooms')
    room_type = models.CharField(max_length=20, choices=ROOM_TYPE_CHOICES, default='public')
    created_at = models.DateTimeField(auto_now_add=True)
    participants = models.ManyToManyField(User, through='Membership', related_name='chat_rooms')
    default_role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CHOICES[-1])  # default to lowest role

    def has_teacher(self):
        return self.participants.filter(role='teacher').exists()
    
    def is_public(self):
        return self.room_type == 'public'
    
    def is_participant(self, user):
        return self.participants.filter(id=user.id).exists()
    
    def all_participants(self):
        return self.participants.all()

    def get_participant_roles(self):
        return {membership.user: membership.role for membership in self.memberships.all()}

    @classmethod
    def get_or_create_general_group(cls, admin_user=None):
        """Get or create the general group with ID 1"""
        if not admin_user:
            admin_user = User.objects.filter(is_superuser=True).first()
            if not admin_user:
                return None

        general_group, created = cls.objects.get_or_create(
            id=1,
            defaults={
                'name': 'General',
                'room_type': 'public',
                'default_role': 'student',
                'owner': admin_user,
            }
        )

        if created:
            if admin_user:
                general_group.owner = admin_user # Ensure the owner is set
                general_group.save()
                # Add the admin user as a member
                Membership.objects.create(
                    user=admin_user,
                    room=general_group,
                    role='admin',
                )
        return general_group

    @classmethod
    def get_or_create_direct_chat(cls, user1, user2):
        """Get or create a direct chat between two users"""
        # Sort user IDs to ensure consistent room creation
        user_ids = sorted([user1.id, user2.id])
        
        # Create a unique name for the direct chat
        chat_name = f"Direct Chat: {user1.username} & {user2.username}"
        
        # Check if a direct chat already exists between these users
        existing_room = cls.objects.filter(
            room_type='direct',
            participants=user1
        ).filter(
            participants=user2
        ).first()
        
        if existing_room:
            return existing_room
        
        # Create new direct chat room
        room = cls.objects.create(
            name=chat_name,
            room_type='direct',
            owner=user1,
            default_role='student'
        )
        
        # Add both users as participants
        Membership.objects.create(
            user=user1,
            room=room,
            role='student' if user1.is_student() else 'teacher'
        )
        Membership.objects.create(
            user=user2,
            room=room,
            role='student' if user2.is_student() else 'teacher'
        )
        
        return room

    def __str__(self):
        return self.name or f"{self.room_type.capitalize()} chat"

class Membership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CHOICES[-1])  # default to lowest role
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'room')

    def __str__(self):
        return f"{str(self.user)} in {str(self.room)} as {self.role}"
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_moderator(self):
        return self.role == 'moderator'
    
    def is_teacher(self):
        return self.role == 'teacher'
    
    def is_rep(self):
        return self.role == 'rep'
    
    def is_arep(self):
        return self.role == 'arep'
    
    def is_student(self):
        return self.role == 'student'
    
    def is_observer(self):
        return self.role == 'observer'

class Message(models.Model):
    id = models.AutoField(primary_key=True, editable=False)
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages_sent')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['room', '-timestamp']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        # Display first 20 characters of the message; use sender (not user)
        return f"{str(self.sender)}: {self.content[:20]}{'...' if len(self.content) > 20 else ''}"
    
    def toJSON(self):
        return {
            'id': self.id,
            'sender': self.sender.username if self.sender else "Anonymous",
            'content': self.content,
            'timestamp': self.timestamp.isoformat()
        }
    
    @classmethod
    def get_messages(cls, room, before_timestamp=None, limit=50):
        if before_timestamp:
            return cls.get_messages_before(room, before_timestamp, limit)
        return cls.get_latest_messages(room, limit)

    @classmethod
    def get_messages_before(cls, room, before_timestamp, limit=50):
        """
        Fetch messages in the room before a certain timestamp for lazy loading.
        """
        return Message.objects.filter(room=room, timestamp__lt=before_timestamp).order_by('-timestamp')[:limit]

    @classmethod
    def get_latest_messages(cls, room, limit=50):
        """
        Fetch the latest messages in the room.
        """
        return cls.objects.filter(room=room).order_by('-timestamp')[:limit]


class ChatInvite(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='invites')
    inviter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_chat_invites')
    invited = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_invites')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ('room', 'invited')

    def __str__(self):
        return f"Invite to {self.invited} for {self.room} by {self.inviter} ({self.status})"
