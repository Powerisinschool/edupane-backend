import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Message, ChatRoom
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

import asyncio
from datetime import datetime, timedelta
from collections import defaultdict

# Global set to track all online users
ONLINE_USERS = defaultdict(set)  # room_id -> set of user_ids
# Change to store time online too? this would help with cleaning up stale connections
# ONLINE_USERS = defaultdict(dict)  # room_id -> {user_id: last_active_time}

class ChatConsumer(AsyncWebsocketConsumer):
    @classmethod
    async def cleanup_stale_connections(cls):
        """Periodically clean up stale connections from ONLINE_USERS."""
        while True:
            for room_id in list(ONLINE_USERS.keys()):
                if not ONLINE_USERS[room_id]:
                    del ONLINE_USERS[room_id]
            await asyncio.sleep(300)  # Run cleanup every 5 minutes

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_id = None
        self.room_group_name = None
        self.user = None
        self.last_message_time = None
        self.message_count = 0
        self.rate_limit_window = timedelta(seconds=10)  # seconds
        self.max_messages_per_window = 5  # max messages allowed in the window
        self.last_typing_update = None
        self.typing_cooldown = timedelta(milliseconds=500)  # milliseconds

    @database_sync_to_async
    def get_room_participants(self):
        room = ChatRoom.objects.get(id=self.room_id)
        return [user.id for user in room.participants.all()]

    async def connect(self):
        asyncio.create_task(self.cleanup_stale_connections())
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope["user"]
        print(f"Connecting to room: {self.room_group_name}")

        # Join room group (all users can join to receive messages)
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        # Add user to online users set (only authenticated users)
        if self.user.is_authenticated:
            ONLINE_USERS[self.room_id].add(self.user.id)

            for room_id in list(ONLINE_USERS.keys()):
                if not ONLINE_USERS[room_id]:
                    del ONLINE_USERS[room_id]
            
            # Get room participants and broadcast online status
            room_participants = await self.get_room_participants()
            online_participants = list(ONLINE_USERS[self.room_id].intersection(set(room_participants)))

            # Broadcast updated online status to room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'online_status_update',
                    'online_users': online_participants
                }
            )

        await self.accept()

    async def disconnect(self, close_code):
        # Remove user from online users set
        if self.user.is_authenticated:
            ONLINE_USERS[self.room_id].discard(self.user.id)
            # Clean up empty room entries
            if not ONLINE_USERS[self.room_id]:
                del ONLINE_USERS[self.room_id]
            
            # Get room participants and broadcast online status
            room_participants = await self.get_room_participants()
            online_participants = list(ONLINE_USERS[self.room_id].intersection(set(room_participants)))

            # Broadcast updated online status to room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'online_status_update',
                    'online_users': online_participants
                }
            )

        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    @database_sync_to_async
    def save_message(self, user, content):
        if not user or not user.is_authenticated:
            return None, "User must be authenticated to send messages"
        try:
            room = ChatRoom.objects.get(id=self.room_id)
        except ObjectDoesNotExist:
            return None, f"Chat room {self.room_id} does not exist"
        try:
            message = Message.objects.create(room=room, sender=user, content=content)
            return message, None
        except Exception as e:
            return None, f"Failed to save message: {str(e)}"
    
    @database_sync_to_async
    def get_messages(self, before_timestamp=None, limit=50):
        room = ChatRoom.objects.get(id=self.room_id)
        messages = Message.get_messages(room, before_timestamp, limit)
        return [{
            'id': msg.id,
            'sender': msg.sender.username if msg.sender else "Anonymous",
            'content': msg.content,
            'timestamp': msg.timestamp.isoformat()
        } for msg in messages]

    async def receive(self, text_data):
        now = datetime.now()

        if self.last_message_time and now - self.last_message_time > self.rate_limit_window:
            self.message_count = 0

        self.last_message_time = now
        self.message_count += 1

        # Rate limiting: if exceeded, ignore the message
        if self.message_count > self.max_messages_per_window:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Rate limit exceeded. Please wait a moment.'
            }))
            return

        data = json.loads(text_data)

        if data.get('type') == 'load_more':
            before_timestamp = data.get('before_timestamp')
            if before_timestamp:
                before_timestamp = timezone.datetime.fromisoformat(before_timestamp)
            messages = await self.get_messages(before_timestamp, limit=data.get('limit', 50))
            await self.send(text_data=json.dumps({
                'type': 'history',
                'messages': messages
            }))
        elif data.get('type') == 'typing':
            if not self.scope["user"].is_authenticated:
                return  # Ignore typing status from unauthenticated users
                
            if self.last_typing_update and now - self.last_typing_update < self.typing_cooldown:
                return # This makes sure we don't broadcast typing status too frequently
            self.last_typing_update = now
            # Broadcast typing status to the group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_status',
                    'user': self.scope["user"].username,
                    'is_typing': data.get('is_typing', False)
                }
            )
        else:
            message = data.get('message', '')

            # Check if user is authenticated before saving message
            user = self.scope.get("user")
            print(f"User: {user}")
            print(f"To send message: {message} from user: {user}")
            if not user or not user.is_authenticated:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'You must be authenticated to send messages'
                }))
                return

            try:
                # Save message to database
                print(f"Saving message: {message} from user: {user}")
                message_obj, error = await self.save_message(user, message)
                
                if error:
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': error
                    }))
                    return

                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': message,
                        'message_id': message_obj.id,
                        'timestamp': message_obj.timestamp.isoformat(),
                        'user': self.scope["user"].username
                    }
                )

                await self.send(text_data=json.dumps({
                    'type': 'receipt',
                    'message_id': message_obj.id,
                    'status': 'sent',
                    'timestamp': message_obj.timestamp.isoformat()
                }))
            except Exception as e:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Failed to save message'
                }))

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'message_id': event.get('message_id', None),
            'user': event.get('user', 'Anonymous'),
            'timestamp': event.get('timestamp', None)
        }))
        
    async def typing_status(self, event):
        # Send typing status to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'typing_status',
            'user': event['user'],
            'is_typing': event['is_typing']
        }))

    async def online_status_update(self, event):
        # Send online status update to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'online_status',
            'online_users': event['online_users']
        }))
    
    async def redis_disconnect(self, event):
        # Send redis disconnect to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'redis_disconnect',
            'message': event['message']
        }))
