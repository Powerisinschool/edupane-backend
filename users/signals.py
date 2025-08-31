from django.db.models.signals import post_save
from django.dispatch import receiver
from users.models import Image, User

@receiver(post_save, sender=Image)
def generate_image_variants(sender, instance, created, **kwargs):
    if created:
        from tasks.image_task import generate_image_variants
        generate_image_variants.delay(instance.id)

@receiver(post_save, sender=User)
def add_user_to_general_group(sender, instance, created, **kwargs):
    """Add new users to the General chat group automatically"""
    if created:
        from messaging.models import ChatRoom, Membership
        
        # Get or create the General group
        general_group = ChatRoom.get_or_create_general_group()
        
        if general_group:
            # Determine the role based on user's role
            chat_role = 'teacher' if instance.is_teacher() else 'student'
            
            # Add user to General group if not already a member
            membership, created = Membership.objects.get_or_create(
                user=instance,
                room=general_group,
                defaults={'role': chat_role}
            )
