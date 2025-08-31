from django.db import models
from django.contrib.auth.models import AbstractUser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image as PILImage
from io import BytesIO
import os

class Image(models.Model):
    id = models.AutoField(primary_key=True)
    image = models.ImageField(upload_to='uploads/')
    thumbnail = models.ImageField(upload_to='uploads/thumbnails/', null=True, blank=True)
    medium = models.ImageField(upload_to='uploads/medium/', null=True, blank=True)
    large = models.ImageField(upload_to='uploads/large/', null=True, blank=True)
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.image.name

    def get_thumbnail_url(self):
        return self.thumbnail.url if self.thumbnail else self.get_original_url()

    def get_medium_url(self):
        return self.medium.url if self.medium else self.get_original_url()

    def get_large_url(self):
        return self.large.url if self.large else self.get_original_url()

    def get_original_url(self):
        return self.image.url if self.image else ''

    def generate_thumbnails(self):
        """Generate thumbnail variants of the image"""
        if not self.image:
            return False

        try:
            # Open the original image
            img = PILImage.open(self.image.path)

            # Define sizes
            sizes = {
                'thumbnail': (100, 100),
                'medium': (500, 500),
                'large': (1000, 1000),
            }

            for size_name, (width, height) in sizes.items():
                # Create a copy of the image
                img_copy = img.copy()

                # Resize while maintaining aspect ratio
                img_copy.thumbnail((width, height), PILImage.Resampling.LANCZOS)

                # Convert to RGB if necessary (for JPEG compatibility)
                if img_copy.mode in ('RGBA', 'LA', 'P'):
                    # Create a white background
                    background = PILImage.new('RGB', img_copy.size, (255, 255, 255))
                    if img_copy.mode == 'P':
                        img_copy = img_copy.convert('RGBA')
                    background.paste(img_copy, mask=img_copy.split()[-1] if img_copy.mode == 'RGBA' else None)
                    img_copy = background

                # Save to BytesIO
                buffer = BytesIO()
                img_copy.save(buffer, format='JPEG', quality=85, optimize=True)
                buffer.seek(0)

                # Create filename
                filename = os.path.basename(self.image.name)
                name, ext = os.path.splitext(filename)
                thumbnail_filename = f"{name}_{size_name}.jpg"

                # Save to the appropriate field
                field = getattr(self, size_name)
                field.save(thumbnail_filename, ContentFile(buffer.getvalue()), save=False)

            self.processed = True
            self.save()
            return True

        except Exception as e:
            print(f"Error generating thumbnails for image {self.id}: {e}")
            return False

class User(AbstractUser):
    permission_classes = [IsAuthenticated]
    ROLES = [
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('admin', 'Admin'),
    ]

    # For backwards compatibility with old project
    STUDENT = "student"
    TEACHER = "teacher"
    ROLE_CHOICES = ROLES

    role = models.CharField(max_length=16, choices=ROLES, default='student')

    # Profile fields
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=100, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    last_login_tracked = models.DateTimeField(null=True, blank=True)

    # Notification preferences
    notify_new_courses = models.BooleanField(default=True)
    notify_reminders = models.BooleanField(default=True)
    notify_messages = models.BooleanField(default=False)

    def __str__(self):
        return f"User: {self.username} ({self.get_full_name()})"

    def is_teacher(self):
        return self.role == 'teacher' or self.role == 'admin'

    def is_student(self):
        return self.role == 'student'

    def is_admin(self):
        return self.role == 'admin'

    def update_last_login_tracked(self):
        """Update the tracked last login time"""
        from django.utils import timezone
        self.last_login_tracked = timezone.now()
        self.save(update_fields=['last_login_tracked'])

    def get_status_updates_since_last_login(self):
        """Get status updates since last tracked login"""
        from courses.models import StatusUpdate
        if not self.last_login_tracked:
            # If no tracked login, return all status updates
            return StatusUpdate.objects.all()
        return StatusUpdate.objects.filter(timestamp__gt=self.last_login_tracked)

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username

    def get_avatar_url(self):
        """Get the avatar URL, with fallback to default"""
        if self.avatar:
            return self.avatar.url
        return "https://images.rawpixel.com/image_png_800/czNmcy1wcml2YXRlL3Jhd3BpeGVsX2ltYWdlcy93ZWJzaXRlX2NvbnRlbnQvbHIvdjkzNy1hZXctMTY1LnBuZw.png"

    def get_avatar_thumbnail_url(self, size=(100, 100)):
        """Get a thumbnail URL for the avatar"""
        if not self.avatar:
            return self.get_avatar_url()
        
        # Check if thumbnail already exists
        thumbnail_path = self._get_thumbnail_path(size)
        if default_storage.exists(thumbnail_path):
            return default_storage.url(thumbnail_path)
        
        # Generate thumbnail
        return self._generate_thumbnail(size)
    
    def _get_thumbnail_path(self, size):
        """Get the path for a thumbnail of given size"""
        if not self.avatar:
            return None
        
        filename = os.path.basename(self.avatar.name)
        name, ext = os.path.splitext(filename)
        return f"avatars/thumbnails/{name}_{size[0]}x{size[1]}.jpg"
    
    def _generate_thumbnail(self, size):
        """Generate and save a thumbnail"""
        try:
            # Open the original image
            img = PILImage.open(self.avatar.path)
            
            # Create thumbnail
            img.thumbnail(size, PILImage.Resampling.LANCZOS)
            
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                background = PILImage.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            # Save thumbnail
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            buffer.seek(0)
            
            thumbnail_path = self._get_thumbnail_path(size)
            default_storage.save(thumbnail_path, buffer)
            
            return default_storage.url(thumbnail_path)
            
        except Exception as e:
            print(f"Error generating thumbnail: {e}")
            return self.get_avatar_url()

    def update_avatar(self, image_file):
        """Update user avatar with new image file"""
        # Delete old avatar file and thumbnails if they exist
        if self.avatar:
            self._delete_avatar_thumbnails()
            self.avatar.delete(save=False)

        # Set new avatar
        if image_file:
            self.avatar = image_file
            self.save()

        return self.avatar
    
    def _delete_avatar_thumbnails(self):
        """Delete all thumbnails for the current avatar"""
        if not self.avatar:
            return
        
        try:
            # Common thumbnail sizes to check
            sizes = [(100, 100), (200, 200), (300, 300), (500, 500)]
            
            for size in sizes:
                thumbnail_path = self._get_thumbnail_path(size)
                if thumbnail_path and default_storage.exists(thumbnail_path):
                    default_storage.delete(thumbnail_path)
        except Exception as e:
            print(f"Error deleting thumbnails: {e}")
    
    def get_avatar_small_url(self):
        """Get small avatar thumbnail (100x100)"""
        return self.get_avatar_thumbnail_url((100, 100))
    
    def get_avatar_medium_url(self):
        """Get medium avatar thumbnail (200x200)"""
        return self.get_avatar_thumbnail_url((200, 200))
    
    def get_avatar_large_url(self):
        """Get large avatar thumbnail (300x300)"""
        return self.get_avatar_thumbnail_url((300, 300))

class UserProfile(models.Model):
    """Legacy profile model - kept for backward compatibility"""
    permission_classes = [IsAuthenticated]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='legacy_profile')

    def __str__(self):
        return f"Legacy Profile of {self.user.username}"

    class Meta:
        verbose_name = "Legacy User Profile"
        verbose_name_plural = "Legacy User Profiles"
