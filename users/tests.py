from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
import os
from .models import User

# Create your tests here.

class UserAvatarThumbnailTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create a simple test image
        self.test_image_content = b'fake-image-content'
        self.test_image = SimpleUploadedFile(
            name='test_image.jpg',
            content=self.test_image_content,
            content_type='image/jpeg'
        )
    
    def test_avatar_thumbnail_generation(self):
        """Test that avatar thumbnails are generated correctly"""
        # Set avatar
        self.user.avatar = self.test_image
        self.user.save()
        
        # Test thumbnail generation
        thumbnail_url = self.user.get_avatar_thumbnail_url()
        self.assertIsNotNone(thumbnail_url)
        
        # Test different sizes
        small_url = self.user.get_avatar_small_url()
        medium_url = self.user.get_avatar_medium_url()
        large_url = self.user.get_avatar_large_url()
        
        self.assertIsNotNone(small_url)
        self.assertIsNotNone(medium_url)
        self.assertIsNotNone(large_url)
    
    def test_avatar_fallback(self):
        """Test that fallback URL is returned when no avatar exists"""
        # User without avatar
        user_no_avatar = User.objects.create_user(
            username='noavatar',
            email='noavatar@example.com',
            password='testpass123'
        )
        
        avatar_url = user_no_avatar.get_avatar_url()
        thumbnail_url = user_no_avatar.get_avatar_thumbnail_url()
        
        self.assertIsNotNone(avatar_url)
        self.assertIsNotNone(thumbnail_url)
        self.assertEqual(avatar_url, thumbnail_url)
    
    def test_thumbnail_path_generation(self):
        """Test that thumbnail paths are generated correctly"""
        self.user.avatar = self.test_image
        self.user.save()
        
        thumbnail_path = self.user._get_thumbnail_path((100, 100))
        self.assertIsNotNone(thumbnail_path)
        self.assertIn('thumbnails', thumbnail_path)
        self.assertIn('100x100', thumbnail_path)
