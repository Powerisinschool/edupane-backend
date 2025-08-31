from rest_framework import viewsets, status, serializers, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from .models import Course, Module, Lesson, Category, Enrollment, Material, Deadline, Feedback, StatusUpdate
from .models_notification import Notification
from .serializers import (
    CourseReadSerializer, CourseWriteSerializer, CourseDetailSerializer, CourseSerializer,
    ModuleSerializer, ModuleWriteSerializer, LessonSerializer, LessonWriteSerializer,
    CategorySerializer, EnrollmentSerializer, MaterialSerializer, 
    DeadlineSerializer, FeedbackSerializer, StatusUpdateSerializer
)

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Show all courses for teachers, or enrolled courses for students
        if user.is_teacher():
            return Course.objects.all()
        else:
            return Course.objects.filter(
                Q(visibility='public') | Q(enrollments__student=user) | Q(owner=user)
            ).distinct()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CourseDetailSerializer
        elif self.request.method in ['GET']:
            return CourseReadSerializer
        return CourseWriteSerializer
    
    def perform_create(self, serializer):
        user = self.request.user
        # Set public based on visibility for backwards compatibility
        validated_data = serializer.validated_data
        if 'public' in validated_data:
            validated_data['visibility'] = 'public' if validated_data.get('public') else 'private'
        course = serializer.save(owner=user, status='draft')
    
    @action(detail=False, methods=['post'])
    def update_image(self, request):
        """Update a course's image"""
        if 'image' not in request.FILES:
            return Response(
                {'error': 'No image file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if 'course' not in request.data:
            return Response(
                {'error': 'Course ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            course_id = request.data['course']
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response(
                {'error': 'Course not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError:
            return Response(
                {'error': 'Invalid course ID'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user has permission to update this course
        if course.owner != request.user:
            return Response(
                {'error': 'You do not have permission to update this course'},
                status=status.HTTP_403_FORBIDDEN
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
            # Update image using the model method
            course.update_image(image_file)

            # Return updated course data
            serializer = CourseSerializer(course, context={'request': request})
            return Response({
                'status': 'success',
                'message': 'Image updated successfully. Thumbnails are being generated.',
                'course': serializer.data
            })

        except Exception as e:
            return Response(
                {'error': f'Error updating course image: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def enroll(self, request, pk=None):
        """Enroll in a course"""
        course = self.get_object()
        user = request.user
        
        if user.is_teacher():
            return Response({
                'error': 'Teachers cannot enroll in courses'
            }, status=status.HTTP_403_FORBIDDEN)
        
        enrollment, created = Enrollment.objects.get_or_create(
            student=user, course=course
        )
        
        # Notify the teacher
        teacher = course.owner
        Notification.objects.create(
            user=teacher,
            message=f"{user.username} enrolled in your course '{course.title}'"
        )
        
        return Response({
            'success': True,
            'message': 'Enrolled successfully' if created else 'Already enrolled',
            'enrollment': EnrollmentSerializer(enrollment).data
        })
    
    @action(detail=True, methods=['post'])
    def unenroll(self, request, pk=None):
        """Unenroll from a course"""
        course = self.get_object()
        user = request.user
        
        try:
            enrollment = Enrollment.objects.get(student=user, course=course)
            enrollment.delete()
            return Response({
                'success': True,
                'message': 'Unenrolled successfully'
            })
        except Enrollment.DoesNotExist:
            return Response({
                'error': 'You are not enrolled in this course'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def leave_feedback(self, request, pk=None):
        """Leave feedback for a course"""
        course = self.get_object()
        user = request.user
        
        # Check if user is enrolled
        if not course.enrollments.filter(student=user).exists():
            return Response({
                'error': 'You must be enrolled to leave feedback'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = FeedbackSerializer(data=request.data)
        if serializer.is_valid():
            feedback = serializer.save(student=user, course=course)
            return Response(FeedbackSerializer(feedback).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def upload_material(self, request, pk=None):
        """Upload course material"""
        course = self.get_object()
        
        if course.owner != request.user:
            return Response({
                'error': 'Only course owner can upload materials'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = MaterialSerializer(data=request.data)
        if serializer.is_valid():
            material = serializer.save(course=course)
            return Response(MaterialSerializer(material).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def materials(self, request, pk=None):
        """Get course materials"""
        course = self.get_object()
        materials = Material.objects.filter(course=course)
        return Response(MaterialSerializer(materials, many=True).data)
    
    @action(detail=True, methods=['delete'], url_path='materials/(?P<material_id>[^/.]+)')
    def delete_material(self, request, pk=None, material_id=None):
        """Delete course material (teachers only)"""
        course = self.get_object()
        
        if course.owner != request.user:
            return Response({
                'error': 'Only course owner can delete materials'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            material = Material.objects.get(id=material_id, course=course)
            # Delete the actual file from storage
            if material.file:
                material.file.delete(save=False)
            material.delete()
            return Response({'success': True, 'message': 'Material deleted successfully'})
        except Material.DoesNotExist:
            return Response({
                'error': 'Material not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'])
    def enrollments(self, request, pk=None):
        """Get course enrollments (teachers only)"""
        course = self.get_object()
        
        if course.owner != request.user:
            return Response({
                'error': 'Only course owner can view enrollments'
            }, status=status.HTTP_403_FORBIDDEN)
        
        enrollments = Enrollment.objects.filter(course=course)
        return Response(EnrollmentSerializer(enrollments, many=True).data)
    
    @action(detail=True, methods=['post'])
    def add_students(self, request, pk=None):
        """Add students to course (teachers only)"""
        course = self.get_object()
        
        if course.owner != request.user:
            return Response({
                'error': 'Only course owner can add students'
            }, status=status.HTTP_403_FORBIDDEN)
        
        student_ids = request.data.get('student_ids', [])
        from users.models import User
        students = User.objects.filter(id__in=student_ids, role='student')
        
        enrollments_created = 0
        for student in students:
            enrollment, created = Enrollment.objects.get_or_create(
                student=student, course=course
            )
            if created:
                enrollments_created += 1
        
        return Response({
            'success': True,
            'message': f'Added {enrollments_created} students to course'
        })
    
    @action(detail=True, methods=['delete'], url_path='remove_student/(?P<student_id>[^/.]+)')
    def remove_student(self, request, pk=None, student_id=None):
        """Remove student from course (teachers only)"""
        course = self.get_object()
        
        if course.owner != request.user:
            return Response({
                'error': 'Only course owner can remove students'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            from users.models import User
            student = User.objects.get(id=student_id, role='student')
            enrollment = Enrollment.objects.get(course=course, student=student)
            enrollment.delete()
            
            return Response({
                'success': True,
                'message': f'Removed {student.get_full_name() or student.username}'
            })
        except (User.DoesNotExist, Enrollment.DoesNotExist):
            return Response({'error': 'Student or enrollment not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get', 'post'])
    def modules(self, request, pk=None):
        """Get or create modules for a course"""
        course = self.get_object()
        
        if request.method == 'GET':
            modules = Module.objects.filter(course=course).order_by('order')
            serializer = ModuleSerializer(modules, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            if course.owner != request.user:
                return Response({
                    'error': 'Only course owner can add modules'
                }, status=status.HTTP_403_FORBIDDEN)
            
            serializer = ModuleWriteSerializer(data=request.data)
            if serializer.is_valid():
                module = serializer.save(course=course)
                return Response(ModuleSerializer(module).data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['put', 'delete'], url_path='modules/(?P<module_id>[^/.]+)')
    def module_detail(self, request, pk=None, module_id=None):
        """Update or delete a specific module"""
        course = self.get_object()
        
        if course.owner != request.user:
            return Response({
                'error': 'Only course owner can modify modules'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            module = Module.objects.get(id=module_id, course=course)
        except Module.DoesNotExist:
            return Response({'error': 'Module not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if request.method == 'PUT':
            serializer = ModuleWriteSerializer(module, data=request.data)
            if serializer.is_valid():
                updated_module = serializer.save()
                return Response(ModuleSerializer(updated_module).data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        elif request.method == 'DELETE':
            module.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['get', 'post'], url_path='modules/(?P<module_id>[^/.]+)/lessons')
    def module_lessons(self, request, pk=None, module_id=None):
        """Get or create lessons for a module"""
        course = self.get_object()
        
        try:
            module = Module.objects.get(id=module_id, course=course)
        except Module.DoesNotExist:
            return Response({'error': 'Module not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if request.method == 'GET':
            lessons = Lesson.objects.filter(module=module).order_by('order')
            serializer = LessonSerializer(lessons, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            if course.owner != request.user:
                return Response({
                    'error': 'Only course owner can add lessons'
                }, status=status.HTTP_403_FORBIDDEN)
            
            serializer = LessonWriteSerializer(data=request.data)
            if serializer.is_valid():
                lesson = serializer.save(module=module)
                return Response(LessonSerializer(lesson).data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['put', 'delete'], url_path='modules/(?P<module_id>[^/.]+)/lessons/(?P<lesson_id>[^/.]+)')
    def lesson_detail(self, request, pk=None, module_id=None, lesson_id=None):
        """Update or delete a specific lesson"""
        course = self.get_object()
        
        if course.owner != request.user:
            return Response({
                'error': 'Only course owner can modify lessons'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            module = Module.objects.get(id=module_id, course=course)
            lesson = Lesson.objects.get(id=lesson_id, module=module)
        except (Module.DoesNotExist, Lesson.DoesNotExist):
            return Response({'error': 'Module or lesson not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if request.method == 'PUT':
            serializer = LessonWriteSerializer(lesson, data=request.data)
            if serializer.is_valid():
                updated_lesson = serializer.save()
                return Response(LessonSerializer(updated_lesson).data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        elif request.method == 'DELETE':
            lesson.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['put'])
    @transaction.atomic
    def structure(self, request, pk=None, *args, **kwargs):
        course = self.get_object()
        if course.owner != request.user:
            return Response({'detail': 'You are not the owner of this course'}, status=status.HTTP_403_FORBIDDEN)

        Module.objects.filter(course=course).delete()

        for module_data in request.data.get('modules', []):
            lessons_data = module_data.pop('lessons', [])
            module = Module.objects.create(course=course, **module_data)
            for lesson_data in lessons_data:
                Lesson.objects.create(module=module, **lesson_data)
        
        return Response({'detail': 'Course structure updated successfully', 'course': CourseReadSerializer(course).data}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None, *args, **kwargs):
        course = self.get_object()
        if course.owner != request.user:
            return Response({'detail': 'You are not the owner of this course'}, status=status.HTTP_403_FORBIDDEN)
        if not course.modules.exists():
            return Response({'detail': 'Course must have at least one module'}, status=status.HTTP_400_BAD_REQUEST)
        if not course.modules.first().lessons.exists():
            return Response({'detail': 'Course must have at least one lesson'}, status=status.HTTP_400_BAD_REQUEST)
        course.status = 'published'
        course.save(update_fields=['status'])
        return Response({'detail': 'Course published successfully', 'course': CourseReadSerializer(course).data}, status=status.HTTP_200_OK)

class ModuleViewSet(viewsets.ModelViewSet):
    queryset = Module.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ['GET']:
            return ModuleSerializer
        return ModuleWriteSerializer
    
    def perform_create(self, serializer):
        course_id = self.request.data.get('course')
        if course_id:
            course = Course.objects.get(id=course_id)
            if course.owner != self.request.user:
                raise serializers.ValidationError("You can only add modules to your own courses")
            serializer.save(course=course)
        else:
            raise serializers.ValidationError("Course ID is required")
    
    def perform_update(self, serializer):
        module = self.get_object()
        if module.course.owner != self.request.user:
            raise serializers.ValidationError("You can only update modules in your own courses")
        serializer.save()
    
    def perform_destroy(self, instance):
        if instance.course.owner != self.request.user:
            raise serializers.ValidationError("You can only delete modules from your own courses")
        instance.delete()

class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ['GET']:
            return LessonSerializer
        return LessonWriteSerializer
    
    def perform_create(self, serializer):
        module_id = self.request.data.get('module')
        if module_id:
            module = Module.objects.get(id=module_id)
            if module.course.owner != self.request.user:
                raise serializers.ValidationError("You can only add lessons to modules in your own courses")
            serializer.save(module=module)
        else:
            raise serializers.ValidationError("Module ID is required")
    
    def perform_update(self, serializer):
        lesson = self.get_object()
        if lesson.module.course.owner != self.request.user:
            raise serializers.ValidationError("You can only update lessons in your own courses")
        serializer.save()
    
    def perform_destroy(self, instance):
        if instance.module.course.owner != self.request.user:
            raise serializers.ValidationError("You can only delete lessons from your own courses")
        instance.delete()

class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_teacher():
            return Enrollment.objects.filter(course__owner=user)
        else:
            return Enrollment.objects.filter(student=user)

    def perform_create(self, serializer):
        enrollment = serializer.save()
        # Notify the teacher
        teacher = enrollment.course.owner
        Notification.objects.create(
            user=teacher,
            message=f"{enrollment.student.username} enrolled in your course '{enrollment.course.title}'"
        )

class MaterialViewSet(viewsets.ModelViewSet):
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        course_id = self.request.data.get('course')
        if course_id:
            course = Course.objects.get(id=course_id)
            if course.owner != self.request.user:
                raise serializers.ValidationError("You can only add materials to your own courses")
            material = serializer.save(course=course)
            # Notify all enrolled students
            students = course.students.all()
            for student in students:
                Notification.objects.create(
                    user=student,
                    message=f"New material '{material.title or 'Untitled'}' added to course '{course.title}'"
                )
        else:
            raise serializers.ValidationError("Course ID is required")
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming deadlines for the user"""
        user = request.user
        if user.is_student():
            enrolled_course_ids = user.enrollments.values_list('course_id', flat=True)
            deadlines = Deadline.objects.filter(
                course_id__in=enrolled_course_ids,
                due_date__gte=timezone.now()
            ).order_by('due_date')[:10]
        else:
            deadlines = Deadline.objects.filter(
                course__owner=user,
                due_date__gte=timezone.now()
            ).order_by('due_date')[:10]
        
        return Response(DeadlineSerializer(deadlines, many=True).data)

class FeedbackViewSet(viewsets.ModelViewSet):
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_teacher():
            return Feedback.objects.filter(course__owner=user)
        else:
            return Feedback.objects.filter(student=user)
    
    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

class StatusUpdateViewSet(viewsets.ModelViewSet):
    queryset = StatusUpdate.objects.all()
    serializer_class = StatusUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    def get_queryset(self):
        return StatusUpdate.objects.all().order_by('-timestamp')[:50]
