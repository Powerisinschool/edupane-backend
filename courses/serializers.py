from rest_framework import serializers
from .models import Course, Module, Lesson, Category, Enrollment, Material, Deadline, Feedback, StatusUpdate
from users.serializers import UserSerializer

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class CourseSerializer(serializers.ModelSerializer):
    teacher = UserSerializer(read_only=True, source='owner')
    imageUrl = serializers.SerializerMethodField()
    imageSmallUrl = serializers.SerializerMethodField()
    imageMediumUrl = serializers.SerializerMethodField()
    imageLargeUrl = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = '__all__'
        
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Add backwards compatibility field
        data['public'] = instance.visibility == 'public'
        return data
    
    def get_imageUrl(self, obj):
        """Get full-size image URL"""
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.get_image_url())
        return None

    def get_imageSmallUrl(self, obj):
        """Get small image thumbnail URL"""
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.get_image_small_url())
        return None

    def get_imageMediumUrl(self, obj):
        """Get medium image thumbnail URL"""
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.get_image_medium_url())
        return None

    def get_imageLargeUrl(self, obj):
        """Get large image thumbnail URL"""
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.get_image_large_url())
        return None

class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = '__all__'

class LessonWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ['title', 'content', 'video_url', 'external_url', 'attachment', 'duration', 'order']

class ModuleSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)
    class Meta:
        model = Module
        fields = '__all__'

class ModuleWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ['title', 'description', 'order']

class CourseReadSerializer(serializers.ModelSerializer):
    modules = ModuleSerializer(many=True, read_only=True)
    creator = UserSerializer(read_only=True, source='owner')
    teacher = UserSerializer(read_only=True, source='owner')
    imageUrl = serializers.SerializerMethodField()
    imageSmallUrl = serializers.SerializerMethodField()
    imageMediumUrl = serializers.SerializerMethodField()
    imageLargeUrl = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'owner', 'category', 'visibility', 'status', 'created_at', 'updated_at', 'modules', 'creator', 'teacher', 'public', 'image', 'imageUrl', 'imageSmallUrl', 'imageMediumUrl', 'imageLargeUrl']
    
    def get_imageUrl(self, obj):
        """Get full-size image URL"""
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.get_image_url())
        return None

    def get_imageSmallUrl(self, obj):
        """Get small image thumbnail URL"""
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.get_image_small_url())
        return None

    def get_imageMediumUrl(self, obj):
        """Get medium image thumbnail URL"""
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.get_image_medium_url())
        return None

    def get_imageLargeUrl(self, obj):
        """Get large image thumbnail URL"""
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.get_image_large_url())
        return None

class CourseWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['title', 'slug', 'description', 'category', 'visibility', 'image', 'public']

class CourseDetailSerializer(serializers.ModelSerializer):
    teacher = UserSerializer(read_only=True, source='owner')
    modules = ModuleSerializer(many=True, read_only=True)
    materials = serializers.SerializerMethodField()
    deadlines = serializers.SerializerMethodField()
    is_enrolled = serializers.SerializerMethodField()
    imageUrl = serializers.SerializerMethodField()
    imageSmallUrl = serializers.SerializerMethodField()
    imageMediumUrl = serializers.SerializerMethodField()
    imageLargeUrl = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'teacher', 'public', 'image', 'imageUrl', 'imageSmallUrl', 'imageMediumUrl', 'imageLargeUrl', 'created_at', 'updated_at', 'modules', 'materials', 'deadlines', 'is_enrolled']
    
    def get_imageUrl(self, obj):
        """Get full-size image URL"""
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.get_image_url())
        return None

    def get_imageSmallUrl(self, obj):
        """Get small image thumbnail URL"""
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.get_image_small_url())
        return None

    def get_imageMediumUrl(self, obj):
        """Get medium image thumbnail URL"""
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.get_image_medium_url())
        return None

    def get_imageLargeUrl(self, obj):
        """Get large image thumbnail URL"""
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.get_image_large_url())
        return None
    
    def get_materials(self, obj):
        return MaterialSerializer(obj.materials.all(), many=True).data
    
    def get_deadlines(self, obj):
        return DeadlineSerializer(obj.deadlines.all(), many=True).data
    
    def get_is_enrolled(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            return obj.enrollments.filter(student=request.user).exists()
        return False

class EnrollmentSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)
    course = CourseSerializer(read_only=True)
    
    class Meta:
        model = Enrollment
        fields = '__all__'

class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Material
        fields = '__all__'

class DeadlineSerializer(serializers.ModelSerializer):
    is_overdue = serializers.ReadOnlyField()
    is_due_soon = serializers.ReadOnlyField()
    days_until_due = serializers.ReadOnlyField()
    course = CourseSerializer(read_only=True)
    
    class Meta:
        model = Deadline
        fields = '__all__'

class FeedbackSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)
    course = CourseSerializer(read_only=True)
    
    class Meta:
        model = Feedback
        fields = '__all__'

class StatusUpdateSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = StatusUpdate
        fields = '__all__'
