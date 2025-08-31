from django.db import models
from django.utils import timezone
from django.core.files.storage import default_storage
from PIL import Image as PILImage
from io import BytesIO
import os
from users.models import User

class Category(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Course(models.Model):
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('unlisted', 'Unlisted'),
        ('private', 'Private'),
    ]
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]

    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    visibility = models.CharField(max_length=16, choices=VISIBILITY_CHOICES, default='public')
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_courses')
    students = models.ManyToManyField(User, related_name='enrolled_courses', blank=True)

    # Add image field for course thumbnails
    image = models.ImageField(upload_to="course_images/", null=True, blank=True)

    # Add public field for backwards compatibility with old frontend
    public = models.BooleanField(default=False)

    # Add teacher field for backwards compatibility (alias to owner)
    @property
    def teacher(self):
        return self.owner

    def __str__(self):
        return self.title

    def get_image_url(self):
        """Get the course image URL, returns None if no image"""
        if self.image:
            return self.image.url
        return None

    def get_image_thumbnail_url(self, size=(300, 200)):
        """Get a thumbnail URL for the course image"""
        if not self.image:
            return None
        
        # Check if thumbnail already exists
        thumbnail_path = self._get_thumbnail_path(size)
        if default_storage.exists(thumbnail_path):
            return default_storage.url(thumbnail_path)
        
        # Generate thumbnail
        return self._generate_thumbnail(size)
    
    def _get_thumbnail_path(self, size):
        """Get the path for a thumbnail of given size"""
        if not self.image:
            return None
        
        filename = os.path.basename(self.image.name)
        name, ext = os.path.splitext(filename)
        return f"course_images/thumbnails/{name}_{size[0]}x{size[1]}.jpg"
    
    def _generate_thumbnail(self, size):
        """Generate and save a thumbnail"""
        try:
            # Open the original image
            img = PILImage.open(self.image.path)
            
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
            print(f"Error generating thumbnail for course {self.id}: {e}")
            return self.get_image_url()
    
    def get_image_small_url(self):
        """Get small course image thumbnail (200x150)"""
        return self.get_image_thumbnail_url((200, 150))
    
    def get_image_medium_url(self):
        """Get medium course image thumbnail (400x300)"""
        return self.get_image_thumbnail_url((400, 300))
    
    def get_image_large_url(self):
        """Get large course image thumbnail (600x450)"""
        return self.get_image_thumbnail_url((600, 450))
    
    def update_image(self, image_file):
        """Update course image with new image file"""
        # Delete old image file and thumbnails if they exist
        if self.image:
            self._delete_image_thumbnails()
            self.image.delete(save=False)

        # Set new image
        if image_file:
            self.image = image_file
            self.save()

        return self.image
    
    def _delete_image_thumbnails(self):
        """Delete all thumbnails for the current image"""
        if not self.image:
            return
        
        try:
            # Common thumbnail sizes to check
            sizes = [(200, 150), (400, 300), (600, 450)]
            
            for size in sizes:
                thumbnail_path = self._get_thumbnail_path(size)
                if thumbnail_path and default_storage.exists(thumbnail_path):
                    default_storage.delete(thumbnail_path)
        except Exception as e:
            print(f"Error deleting thumbnails for course {self.id}: {e}")

class Module(models.Model):
    id = models.AutoField(primary_key=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title

class Lesson(models.Model):
    id = models.AutoField(primary_key=True)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    video_url = models.URLField(blank=True)
    external_url = models.URLField(blank=True)
    attachment = models.FileField(upload_to='lesson_attachments/', blank=True)
    duration = models.DurationField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title

# Add missing models from old elearning project
class Enrollment(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    date_enrolled = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "course")

    def __str__(self):
        return f"{self.student.username} enrolled in {self.course.title}"

        def save(self, *args, **kwargs):
            is_new = self.pk is None
            super().save(*args, **kwargs)
            if is_new:
                # Notify the teacher (owner) of the course
                Notification = None
                try:
                    from .models_notification import Notification
                except ImportError:
                    pass
                if Notification:
                    Notification.objects.create(
                        user=self.course.teacher,
                        message=f"{self.student.username} has enrolled in your course '{self.course.title}'."
                    )

class Material(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='materials')
    file = models.FileField(upload_to="materials/")
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or f"Material for {self.course.title}"

        def save(self, *args, **kwargs):
            is_new = self.pk is None
            super().save(*args, **kwargs)
            if is_new:
                Notification = None
                try:
                    from .models_notification import Notification
                except ImportError:
                    pass
                if Notification:
                    students = self.course.students.all()
                    for student in students:
                        Notification.objects.create(
                            user=student,
                            message=f"New material '{self.title or self.file.name}' has been added to your course '{self.course.title}'."
                        )

class Deadline(models.Model):
    DEADLINE_TYPES = [
        ('assignment', 'Assignment'),
        ('quiz', 'Quiz'),
        ('exam', 'Exam'),
        ('project', 'Project'),
        ('discussion', 'Discussion'),
        ('other', 'Other'),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='deadlines')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    deadline_type = models.CharField(max_length=20, choices=DEADLINE_TYPES, default='assignment')
    due_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date']

    def __str__(self):
        return f"{self.title} - {self.course.title}"

    @property
    def is_overdue(self):
        return timezone.now() > self.due_date

    @property
    def is_due_soon(self):
        """Returns True if deadline is within 24 hours"""
        now = timezone.now()
        return now <= self.due_date and (self.due_date - now).days <= 1

    @property
    def days_until_due(self):
        """Returns number of days until due date"""
        now = timezone.now()
        if now > self.due_date:
            return 0
        return (self.due_date - now).days

class Feedback(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedbacks')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='feedbacks')
    rating = models.IntegerField(default=0, choices=[(i, str(i)) for i in range(1, 6)])  # 1 to 5 rating
    aspects = models.CharField(max_length=100, blank=True) # e.g. "content", "delivery", "interaction"
    comment = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback by {self.student.username} for {self.course.title}"

class StatusUpdate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='status_updates')
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Status by {self.user.username}: {self.text[:50]}..."
