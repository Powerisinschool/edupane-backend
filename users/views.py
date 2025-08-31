from django.shortcuts import render
from django.db import models
from rest_framework import generics, viewsets, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, action
from django.contrib.auth import get_user_model
from .models import User, Image, UserProfile
from .serializers import UserSerializer, ImageSerializer, UserProfileSerializer, RegisterSerializer
from tasks.image_task import process_image_upload

class ImageViewSet(viewsets.ModelViewSet):
    queryset = Image.objects.all()
    serializer_class = ImageSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        """Create image and trigger background processing"""
        image = serializer.save()

        # Trigger background task to generate thumbnails
        process_image_upload.delay(image.id)

        return image

    @action(detail=True, methods=['post'])
    def regenerate_thumbnails(self, request, pk=None):
        """Manually regenerate thumbnails for an image"""
        try:
            image = self.get_object()

            # Trigger background task
            task = process_image_upload.delay(image.id)

            return Response({
                'status': 'processing',
                'task_id': task.id,
                'message': 'Thumbnail generation started'
            })

        except Image.DoesNotExist:
            return Response(
                {'error': 'Image not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get processing status of an image"""
        try:
            image = self.get_object()
            return Response({
                'id': image.id,
                'processed': image.processed,
                'has_thumbnail': bool(image.thumbnail),
                'has_medium': bool(image.medium),
                'has_large': bool(image.large),
                'created_at': image.created_at,
                'updated_at': image.updated_at
            })

        except Image.DoesNotExist:
            return Response(
                {'error': 'Image not found'},
                status=status.HTTP_404_NOT_FOUND
            )

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter users based on query parameters"""
        queryset = User.objects.all()
        
        # Filter by role
        role = self.request.query_params.get('role', None)
        if role:
            queryset = queryset.filter(role=role)
        
        # Filter by search term (optional for future use)
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                models.Q(username__icontains=search) |
                models.Q(first_name__icontains=search) |
                models.Q(last_name__icontains=search) |
                models.Q(email__icontains=search)
            )
        
        return queryset.order_by('username')

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search users with live search functionality for teachers"""
        # Check if user is a teacher
        if not request.user.is_teacher():
            return Response(
                {'error': 'Access denied. Teachers only.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get query parameters
        query = request.query_params.get('q', '').strip()
        role_filter = request.query_params.get('role', '').strip()
        limit = int(request.query_params.get('limit', 20))
        
        # Start with all users
        users = User.objects.all()
        
        # Apply search filter
        if query:
            users = users.filter(
                models.Q(username__icontains=query) |
                models.Q(first_name__icontains=query) |
                models.Q(last_name__icontains=query) |
                models.Q(email__icontains=query)
            )
        
        # Apply role filter
        if role_filter and role_filter in ['student', 'teacher', 'admin']:
            users = users.filter(role=role_filter)
        
        # Order and limit results
        users = users.order_by('last_name', 'first_name', 'username')[:limit]
        
        # Serialize the results
        serializer = UserSerializer(users, many=True)
        
        return Response({
            'success': True,
            'users': serializer.data,
            'total': users.count()
        })

class UserProfileViewSet(viewsets.ModelViewSet):
    """Simplified profile management - works directly with User model"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return only the current user"""
        if self.request.user.is_authenticated:
            return User.objects.filter(id=self.request.user.id)
        return User.objects.none()

    @action(detail=False, methods=['post'])
    def update_avatar(self, request):
        """Update the current user's avatar"""
        if 'image' not in request.FILES:
            return Response(
                {'error': 'No image file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        image_file = request.FILES['image']

        # Validate file type
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
        if image_file.content_type not in allowed_types:
            return Response(
                {'error': 'Invalid file type. Only JPEG, PNG, GIF, and WebP are allowed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate file size (max 10MB)
        if image_file.size > 10 * 1024 * 1024:
            return Response(
                {'error': 'File too large. Maximum size is 10MB.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Update avatar using the model method
            request.user.update_avatar(image_file)

            # Return updated user data
            serializer = UserSerializer(request.user)
            return Response({
                'status': 'success',
                'message': 'Avatar updated successfully. Thumbnails are being generated.',
                'user': serializer.data
            })

        except Exception as e:
            return Response(
                {'error': f'Error updating avatar: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def update_profile_picture(self, request):
        """Legacy endpoint - redirects to update_avatar for backward compatibility"""
        return self.update_avatar(request)

    @action(detail=False, methods=['patch'])
    def update_profile(self, request):
        """Update user profile information"""
        user = request.user
        serializer = UserSerializer(user, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({
                'status': 'success',
                'message': 'Profile updated successfully.',
                'user': serializer.data
            })

        return Response({
            'error': 'Invalid data provided',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_image(request):
    """Simple image upload endpoint"""
    if 'image' not in request.FILES:
        return Response(
            {'error': 'No image file provided'},
            status=status.HTTP_400_BAD_REQUEST
        )

    image_file = request.FILES['image']

    # Validate file type
    allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
    if image_file.content_type not in allowed_types:
        return Response(
            {'error': 'Invalid file type. Only JPEG, PNG, GIF, and WebP are allowed.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate file size (max 10MB)
    if image_file.size > 10 * 1024 * 1024:
        return Response(
            {'error': 'File too large. Maximum size is 10MB.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Create image object
        image = Image.objects.create(image=image_file)

        # Trigger background processing
        process_image_upload.delay(image.id)

        # Return image data
        serializer = ImageSerializer(image)
        return Response({
            'status': 'success',
            'message': 'Image uploaded successfully. Thumbnails are being generated.',
            'image': serializer.data
        })

    except Exception as e:
        return Response(
            {'error': f'Error uploading image: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def username_available(request):
    """Check if a username is available"""
    username = request.query_params.get('username', '').strip()
    if not username:
        return Response({"available": False, "reason": "missing"}, status=400)
    User = get_user_model()
    exists = User.objects.filter(username__iexact=username).exists()
    return Response({"available": not exists})


@api_view(['POST'])
@permission_classes([AllowAny])
def validate_teacher_code(request):
    """Validate teacher invitation/verification code"""
    code = (request.data.get('teacher_code') or '').strip()
    # Simple validation; replace with settings-based or DB-backed verification as needed
    return Response({"valid": code == 'TEACH1234'})
