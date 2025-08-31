from rest_framework import serializers
from .models import User, UserProfile, Image
from django.contrib.auth.password_validation import validate_password

class ImageSerializer(serializers.ModelSerializer):
    thumbnail_url = serializers.SerializerMethodField()
    medium_url = serializers.SerializerMethodField()
    large_url = serializers.SerializerMethodField()
    original_url = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = [
            'id', 'image', 'thumbnail', 'medium', 'large',
            'processed', 'created_at', 'updated_at',
            'thumbnail_url', 'medium_url', 'large_url', 'original_url'
        ]
        read_only_fields = ['thumbnail', 'medium', 'large', 'processed', 'created_at', 'updated_at']

    def get_thumbnail_url(self, obj):
        return obj.get_thumbnail_url()

    def get_medium_url(self, obj):
        return obj.get_medium_url()

    def get_large_url(self, obj):
        return obj.get_large_url()

    def get_original_url(self, obj):
        return obj.get_original_url()

class UserProfileSerializer(serializers.ModelSerializer):
    """Legacy serializer - kept for backward compatibility"""
    class Meta:
        model = UserProfile
        fields = ['id', 'user']

class UserSerializer(serializers.ModelSerializer):
    photoUrl = serializers.SerializerMethodField()
    avatarUrl = serializers.SerializerMethodField()
    avatarThumbnailUrl = serializers.SerializerMethodField()
    avatarSmallUrl = serializers.SerializerMethodField()
    avatarMediumUrl = serializers.SerializerMethodField()
    avatarLargeUrl = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'role',
            'bio', 'location', 'avatar', 'photoUrl', 'avatarUrl', 'avatarThumbnailUrl',
            'avatarSmallUrl', 'avatarMediumUrl', 'avatarLargeUrl',
            'notify_new_courses', 'notify_reminders', 'notify_messages'
        ]

    def get_photoUrl(self, obj):
        """Legacy field - returns avatar URL for backward compatibility"""
        return obj.get_avatar_url()

    def get_avatarUrl(self, obj):
        """Get full-size avatar URL"""
        request = self.context.get('request')
        if obj.avatar and request:
            return request.build_absolute_uri(obj.avatar.url)
        return None

    def get_avatarThumbnailUrl(self, obj):
        """Get thumbnail avatar URL"""
        request = self.context.get('request')
        if obj.avatar and request:
            return request.build_absolute_uri(obj.get_avatar_thumbnail_url())
        return None

    def get_avatarSmallUrl(self, obj):
        """Get small avatar thumbnail URL"""
        request = self.context.get('request')
        if obj.avatar and request:
            return request.build_absolute_uri(obj.get_avatar_small_url())
        return None

    def get_avatarMediumUrl(self, obj):
        """Get medium avatar thumbnail URL"""
        request = self.context.get('request')
        if obj.avatar and request:
            return request.build_absolute_uri(obj.get_avatar_medium_url())
        return None

    def get_avatarLargeUrl(self, obj):
        """Get large avatar thumbnail URL"""
        request = self.context.get('request')
        if obj.avatar and request:
            return request.build_absolute_uri(obj.get_avatar_large_url())
        return None

    def update(self, instance, validated_data):
        """Update user instance"""
        # Handle avatar separately if needed
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    teacher_code = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ("username", "email", "role", "first_name", "last_name", "password", "password2", "teacher_code")

    def to_internal_value(self, data):
        # Map role values from frontend to backend before validation
        if 'role' in data:
            role_mapping = {
                'ST': 'student',
                'TR': 'teacher',
                'student': 'student',
                'teacher': 'teacher',
                'admin': 'admin'
            }
            
            role = data.get("role")
            if role in role_mapping:
                data = data.copy()  # Don't modify the original data
                data["role"] = role_mapping[role]
        
        return super().to_internal_value(data)

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Passwords must match."})
        
        # Validate teacher code if role is teacher
        if attrs["role"] == "teacher":
            teacher_code = attrs.get("teacher_code", "").strip()
            if not teacher_code or teacher_code != "TEACH1234":
                raise serializers.ValidationError({"teacher_code": "Invalid teacher code."})
        
        return attrs

    def create(self, validated_data):
        # Remove teacher_code from validated_data as it's not a User model field
        validated_data.pop("teacher_code", None)
        
        user = User.objects.create(
            username=validated_data["username"],
            email=validated_data["email"],
            role=validated_data["role"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
        )
        user.set_password(validated_data["password"])
        user.save()
        return user
