from django.core.management.base import BaseCommand
from users.models import User
from django.core.files.storage import default_storage
import os

class Command(BaseCommand):
    help = 'Generate thumbnails for all user avatars'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force regeneration of existing thumbnails',
        )
        parser.add_argument(
            '--size',
            type=str,
            default='100,100',
            help='Thumbnail size in format width,height (default: 100,100)',
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

        users_with_avatars = User.objects.filter(avatar__isnull=False).exclude(avatar='')
        
        if not users_with_avatars.exists():
            self.stdout.write(
                self.style.WARNING('No users with avatars found.')
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f'Found {users_with_avatars.count()} users with avatars.')
        )

        success_count = 0
        error_count = 0

        for user in users_with_avatars:
            try:
                # Check if thumbnail already exists
                thumbnail_path = user._get_thumbnail_path(size)
                
                if not force and thumbnail_path and default_storage.exists(thumbnail_path):
                    self.stdout.write(
                        f'Skipping {user.username} - thumbnail already exists'
                    )
                    continue

                # Generate thumbnail
                thumbnail_url = user._generate_thumbnail(size)
                
                if thumbnail_url:
                    self.stdout.write(
                        self.style.SUCCESS(f'Generated thumbnail for {user.username}: {thumbnail_url}')
                    )
                    success_count += 1
                else:
                    self.stdout.write(
                        self.style.ERROR(f'Failed to generate thumbnail for {user.username}')
                    )
                    error_count += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing {user.username}: {str(e)}')
                )
                error_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Thumbnail generation complete. Success: {success_count}, Errors: {error_count}'
            )
        )
