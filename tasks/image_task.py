from celery import shared_task
from users.models import Image
from PIL import Image as PILImage
from io import BytesIO
from django.core.files.base import ContentFile
from django.conf import settings
import os
import requests

SIZE_MAP = {
    'thumbnail': (100, 100),
    'medium': (500, 500),
    'large': (1000, 1000),
}

@shared_task
def generate_image_variants(image_id) -> dict:
    """Generate thumbnail variants for an image"""
    try:
        obj = Image.objects.get(id=image_id)
        
        # Use the new method from the model
        success = obj.generate_thumbnails()
        
        if success:
            return { 'status': 'success', 'image_id': image_id }
        else:
            return { 'status': 'error', 'message': f'Failed to generate thumbnails for image {image_id}' }
            
    except Image.DoesNotExist:
        return { 'status': 'error', 'message': f'Image with id {image_id} does not exist' }
    except Exception as e:
        return { 'status': 'error', 'message': f'Error generating image variants: {str(e)}' }

@shared_task
def process_image_upload(image_id) -> dict:
    """Process an uploaded image - generate thumbnails and mark as processed"""
    try:
        obj = Image.objects.get(id=image_id)
        
        # Generate thumbnails
        success = obj.generate_thumbnails()
        
        if success:
            return { 'status': 'success', 'image_id': image_id }
        else:
            return { 'status': 'error', 'message': f'Failed to process image {image_id}' }
            
    except Image.DoesNotExist:
        return { 'status': 'error', 'message': f'Image with id {image_id} does not exist' }
    except Exception as e:
        return { 'status': 'error', 'message': f'Error processing image: {str(e)}' }
