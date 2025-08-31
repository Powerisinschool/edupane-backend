from django.core.management.base import BaseCommand
from courses.models import Course
from django.core.files.storage import default_storage
import os

class Command(BaseCommand):
    help = 'Generate thumbnails for all course images'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force regeneration of existing thumbnails',
        )
        parser.add_argument(
            '--size',
            type=str,
            default='300,200',
            help='Thumbnail size in format width,height (default: 300,200)',
        )

    def handle(self, *args, **options):
        force = options['force']
        size_str = options['size']
        
        try:
            width, height = map(int, size_str.split(','))
            size = (width, height)
        except ValueError:
            self.stdout.write(
                self.style.ERROR(f'Invalid size format: {size_str}. Use width,height format.')
            )
            return

        courses_with_images = Course.objects.filter(image__isnull=False).exclude(image='')
        
        if not courses_with_images.exists():
            self.stdout.write(
                self.style.WARNING('No courses with images found.')
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f'Found {courses_with_images.count()} courses with images.')
        )

        success_count = 0
        error_count = 0

        for course in courses_with_images:
            try:
                # Check if thumbnail already exists
                thumbnail_path = course._get_thumbnail_path(size)
                
                if not force and thumbnail_path and default_storage.exists(thumbnail_path):
                    self.stdout.write(
                        f'Skipping {course.title} - thumbnail already exists'
                    )
                    continue

                # Generate thumbnail
                thumbnail_url = course._generate_thumbnail(size)
                
                if thumbnail_url:
                    self.stdout.write(
                        self.style.SUCCESS(f'Generated thumbnail for {course.title}: {thumbnail_url}')
                    )
                    success_count += 1
                else:
                    self.stdout.write(
                        self.style.ERROR(f'Failed to generate thumbnail for {course.title}')
                    )
                    error_count += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing {course.title}: {str(e)}')
                )
                error_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Course thumbnail generation complete. Success: {success_count}, Errors: {error_count}'
            )
        )
