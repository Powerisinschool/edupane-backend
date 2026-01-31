import os
import django

# 1. Setup Django environment
# Make sure 'edupane_backend' matches your actual folder name for settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "edupane_backend.settings")
django.setup()

from django.contrib.auth import get_user_model

def create_superuser():
    User = get_user_model()
    
    # Get credentials from Render Environment Variables (or use defaults)
    username = os.environ.get("ADMIN_USERNAME", "admin")
    password = os.environ.get("ADMIN_PASSWORD", "admin") # TODO: Change this in production!
    email = "admin@edupane.com"

    if not User.objects.filter(username=username).exists():
        print(f"Creating superuser: {username}...")
        
        # Create the standard superuser (is_staff=True, is_superuser=True)
        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )

        user.role = 'admin' # Set role to admin since we have custom roles
        user.save()
        
        print(f"Superuser '{username}' created successfully with role 'admin'.")
    else:
        print(f"Superuser '{username}' already exists. Skipping.")

if __name__ == "__main__":
    create_superuser()
