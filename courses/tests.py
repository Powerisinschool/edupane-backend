from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
import os
from .models import Course, Category
from users.models import User

# Create your tests here.

class CourseImageThumbnailTest(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username='testteacher',
            email='teacher@example.com',
            password='testpass123',
            role='teacher'
        )
        
        # Create a test category
        self.category = Category.objects.create(
            name='Test Category',
            description='Test category description'
        )
        
        # Create a test course
        self.course = Course.objects.create(
            title='Test Course',
            description='Test course description',
            owner=self.user,
            category=self.category,
            visibility='public',
            status='published'
        )
        
        # Create a simple test image
        self.test_image_content = b'fake-image-content'
        self.test_image = SimpleUploadedFile(
            name='test_course_image.jpg',
            content=self.test_image_content,
            content_type='image/jpeg'
        )
    
    def test_course_image_thumbnail_generation(self):
        """Test that course image thumbnails are generated correctly"""
        # Set image
        self.course.image = self.test_image
        self.course.save()
        
        # Test thumbnail generation
        thumbnail_url = self.course.get_image_thumbnail_url()
        self.assertIsNotNone(thumbnail_url)
        
        # Test different sizes
        small_url = self.course.get_image_small_url()
        medium_url = self.course.get_image_medium_url()
        large_url = self.course.get_image_large_url()
        
        self.assertIsNotNone(small_url)
        self.assertIsNotNone(medium_url)
        self.assertIsNotNone(large_url)
    
    def test_course_image_fallback(self):
        """Test that None is returned when no image exists"""
        # Course without image
        course_no_image = Course.objects.create(
            title='No Image Course',
            description='Course without image',
            owner=self.user,
            category=self.category,
            visibility='public',
            status='published'
        )
        
        image_url = course_no_image.get_image_url()
        thumbnail_url = course_no_image.get_image_thumbnail_url()
        
        self.assertIsNone(image_url)
        self.assertIsNone(thumbnail_url)
    
    def test_thumbnail_path_generation(self):
        """Test that thumbnail paths are generated correctly"""
        self.course.image = self.test_image
        self.course.save()
        
        thumbnail_path = self.course._get_thumbnail_path((300, 200))
        self.assertIsNotNone(thumbnail_path)
        self.assertIn('thumbnails', thumbnail_path)
        self.assertIn('300x200', thumbnail_path)
    
    def test_custom_thumbnail_size(self):
        """Test custom thumbnail size generation"""
        self.course.image = self.test_image
        self.course.save()
        
        custom_size = (500, 300)
        custom_url = self.course.get_image_thumbnail_url(custom_size)
        self.assertIsNotNone(custom_url)
        
        custom_path = self.course._get_thumbnail_path(custom_size)
        self.assertIn('500x300', custom_path)
