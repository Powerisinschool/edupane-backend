from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Count, Q
from datetime import datetime, timedelta
from courses.models import Course, Module, Lesson, StatusUpdate
from messaging.models import ChatRoom, Message, ChatInvite, Membership
from users.models import User

@api_view(['GET'])
@permission_classes([])  # Allow access without authentication
def hello_world(request):
    return Response({'message': 'Hello, World!'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_data(request):
    """Get comprehensive dashboard data for the authenticated user"""
    user = request.user
    
    # Check if user is a teacher
    if user.is_teacher():
        # Teacher Dashboard Data
        # Get courses owned by this teacher
        owned_courses = Course.objects.filter(owner=user).prefetch_related('students')
        
        # Get group chats owned by this teacher
        group_chats = ChatRoom.objects.filter(
            owner=user, 
            room_type='group'
        ).prefetch_related('participants')
        
        # Calculate total enrolled students across all courses
        total_students = 0
        for course in owned_courses:
            total_students += course.students.count()
        
        # Prepare courses data
        courses = []
        for course in owned_courses:
            courses.append({
                'id': course.id,
                'title': course.title,
                'description': course.description,
                'status': course.status,
                'student_count': course.students.count(),
                'created_at': course.created_at.isoformat(),
                'updated_at': course.updated_at.isoformat()
            })
        
        # Prepare group chats data
        group_chats_data = []
        for chat in group_chats:
            group_chats_data.append({
                'id': chat.id,
                'name': chat.name,
                'participant_count': chat.participants.count(),
                'room_type': chat.room_type,
                'created_at': chat.created_at.isoformat()
            })
        
        # Calculate stats
        stats = {
            'totalCourses': owned_courses.count(),
            'groupChats': group_chats.count(),
            'totalStudents': total_students
        }
        
        dashboard_data = {
            'user': {
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'role': user.role
            },
            'stats': stats,
            'courses': courses,
            'groupChats': group_chats_data
        }
        
        return Response(dashboard_data)
    
    else:
        # Student Dashboard Data (existing logic)
        # Get user's enrolled courses
        enrolled_courses = user.enrolled_courses.filter(status='published').prefetch_related('owner')
        
        # Get course enrollments with teacher info
        enrollments = []
        for course in enrolled_courses:
            enrollments.append({
                'course': {
                    'id': course.id,
                    'title': course.title,
                    'teacher': {
                        'first_name': course.owner.first_name,
                        'last_name': course.owner.last_name,
                        'username': course.owner.username
                    }
                }
            })
        
        # Get upcoming deadlines (simplified - you might want to add actual deadline model)
        upcoming_deadlines = []
        for course in enrolled_courses:
            # Mock deadlines for now - you can extend this with actual deadline models
            upcoming_deadlines.append({
                'id': f'd{course.id}_1',
                'title': f'{course.title} - Module 1 Quiz',
                'deadlineType': 'quiz',
                'isDueSoon': True,
                'daysUntilDue': 3,
                'course': {'title': course.title}
            })
        
        # Get pending chat invites
        pending_invites = []
        chat_invites = ChatInvite.objects.filter(
            invited=user, 
            status='pending'
        ).select_related('room', 'inviter')
        
        for invite in chat_invites:
            pending_invites.append({
                'id': invite.id,
                'room': {'name': invite.room.name},
                'inviter': {
                    'fullName': f"{invite.inviter.first_name} {invite.inviter.last_name}",
                    'username': invite.inviter.username
                }
            })
        
        # Calculate stats (removed statuses as they'll be loaded separately via feed)
        stats = {
            'enrolledCourses': enrolled_courses.count(),
            'feedbacks': 0,  # You can add feedback model later
            'chatInvites': len(pending_invites),
            'upcomingDeadlines': len(upcoming_deadlines)
        }
        
        dashboard_data = {
            'user': {
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'role': user.role
            },
            'stats': stats,
            'enrollments': enrollments,
            'upcomingDeadlines': upcoming_deadlines,
            'pendingInvites': pending_invites
        }
        
        return Response(dashboard_data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_status(request):
    """Post a status update to a chat room"""
    user = request.user
    text = request.data.get('text')
    room_id = request.data.get('room_id', 1)  # Default to general room
    
    if not text:
        return Response({'error': 'Text is required'}, status=400)
    
    try:
        room = ChatRoom.objects.get(id=room_id, participants=user)
        message = Message.objects.create(
            room=room,
            sender=user,
            content=text
        )
        return Response({'success': True, 'message_id': message.id})
    except ChatRoom.DoesNotExist:
        return Response({'error': 'Room not found or access denied'}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_invite(request):
    """Accept a chat invite"""
    user = request.user
    invite_id = request.data.get('invite_id')
    
    try:
        invite = ChatInvite.objects.get(id=invite_id, invited=user, status='pending')
        invite.status = 'accepted'
        invite.responded_at = datetime.now()
        invite.save()
        
        # Add user to the room
        Membership.objects.get_or_create(
            user=user,
            room=invite.room,
            defaults={'role': 'student'}
        )
        
        return Response({'success': True})
    except ChatInvite.DoesNotExist:
        return Response({'error': 'Invite not found'}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def decline_invite(request):
    """Decline a chat invite"""
    user = request.user
    invite_id = request.data.get('invite_id')
    
    try:
        invite = ChatInvite.objects.get(id=invite_id, invited=user, status='pending')
        invite.status = 'rejected'
        invite.responded_at = datetime.now()
        invite.save()
        
        return Response({'success': True})
    except ChatInvite.DoesNotExist:
        return Response({'error': 'Invite not found'}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def feed(request):
    """Get paginated feed of status updates for the authenticated user"""
    # Get pagination parameters
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 20))
    offset = (page - 1) * limit
    
    # Get all status updates (they are public to everyone)
    status_updates = StatusUpdate.objects.select_related('user').order_by('-timestamp')[offset:offset + limit]
    
    # Check if there are more updates (for hasMore flag)
    total_count = StatusUpdate.objects.count()
    has_more = (offset + limit) < total_count
    
    # Serialize the status updates
    feed_items = []
    for status in status_updates:
        feed_items.append({
            'id': status.id,
            'user': {
                'id': status.user.id,
                'username': status.user.username,
                'first_name': status.user.first_name,
                'last_name': status.user.last_name,
                'full_name': status.user.get_full_name(),
                'role': status.user.role,
                'avatar_url': status.user.get_avatar_url()
            },
            'text': status.text,
            'timestamp': status.timestamp.isoformat(),
            'created_at': status.timestamp.isoformat()  # For compatibility
        })
    
    return Response({
        'feed': feed_items,
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total_count,
            'has_more': has_more,
            'next_page': page + 1 if has_more else None
        }
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_status_update(request):
    """Create a new status update"""
    user = request.user
    text = request.data.get('text', '').strip()
    
    if not text:
        return Response({'error': 'Status text is required'}, status=400)
    
    if len(text) > 500:  # Limit status update length
        return Response({'error': 'Status text is too long (max 500 characters)'}, status=400)
    
    # Create the status update
    status_update = StatusUpdate.objects.create(
        user=user,
        text=text
    )
    
    # Return the created status update
    return Response({
        'success': True,
        'status_update': {
            'id': status_update.id,
            'user': {
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.get_full_name(),
                'role': user.role,
                'avatar_url': user.get_avatar_url()
            },
            'text': status_update.text,
            'timestamp': status_update.timestamp.isoformat(),
            'created_at': status_update.timestamp.isoformat()
        }
    }, status=201)
