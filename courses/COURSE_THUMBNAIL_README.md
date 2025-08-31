# Course Image Thumbnail System

This document explains the new course image thumbnail system implemented in the Course model.

## Overview

The Course model now includes built-in thumbnail generation for course images, similar to the user avatar system but with course-specific optimizations.

## Features

- **On-demand thumbnail generation**: Thumbnails are created when first requested
- **Multiple sizes**: Support for small (200x150), medium (400x300), and large (600x450) thumbnails
- **Course-optimized aspect ratios**: Uses wider aspect ratios suitable for course thumbnails
- **Automatic cleanup**: Old thumbnails are deleted when images are updated
- **Null fallback**: Returns `None` when no image exists (no default fallback)
- **Storage efficient**: Only stores thumbnails when actually needed

## Usage

### In Python Code

```python
# Get different thumbnail sizes
course = Course.objects.get(title='Example Course')

# Default thumbnail (300x200)
thumbnail_url = course.get_image_thumbnail_url()

# Specific sizes
small_url = course.get_image_small_url()      # 200x150
medium_url = course.get_image_medium_url()    # 400x300
large_url = course.get_image_large_url()      # 600x450

# Custom size
custom_url = course.get_image_thumbnail_url((500, 300))

# Check if image exists
if course.image:
    image_url = course.get_image_url()
else:
    image_url = None  # No fallback for courses
```

### In API Responses

The Course serializers now include these fields:

- `imageUrl`: Full-size image URL
- `imageSmallUrl`: Small thumbnail (200x150)
- `imageMediumUrl`: Medium thumbnail (400x300)
- `imageLargeUrl`: Large thumbnail (600x450)

**Important**: All fields return `null` if no image exists.

### Management Commands

Generate thumbnails for all courses:

```bash
# Generate default thumbnails (300x200)
python manage.py generate_course_thumbnails

# Generate custom size thumbnails
python manage.py generate_course_thumbnails --size 400,300

# Force regeneration of existing thumbnails
python manage.py generate_course_thumbnails --force
```

## Implementation Details

### Storage Structure

```
media/
├── course_images/
│   ├── course_image.jpg
│   └── thumbnails/
│       ├── course_image_200x150.jpg
│       ├── course_image_400x300.jpg
│       └── course_image_600x450.jpg
```

### Key Methods

- `get_image_url()`: Get original image URL (returns None if no image)
- `get_image_thumbnail_url(size)`: Get or generate thumbnail URL
- `_get_thumbnail_path(size)`: Generate thumbnail file path
- `_generate_thumbnail(size)`: Create and save thumbnail
- `_delete_image_thumbnails()`: Clean up old thumbnails
- `update_image(image_file)`: Update course image with cleanup

### Error Handling

- If thumbnail generation fails, returns the original image URL
- If no image exists, returns `None` (no fallback)
- All errors are logged but don't break the application

## Differences from User Avatar System

| Feature | User Avatars | Course Images |
|---------|-------------|---------------|
| Fallback | Default avatar URL | `None` |
| Aspect Ratio | Square (1:1) | Wide (3:2, 4:3) |
| Storage Path | `avatars/thumbnails/` | `course_images/thumbnails/` |
| Default Size | 100x100 | 300x200 |
| Use Case | Profile pictures | Course thumbnails |

## Testing

Run the tests to verify functionality:

```bash
python manage.py test courses.tests.CourseImageThumbnailTest
```

## Performance Considerations

- Thumbnails are generated on first request (lazy loading)
- Generated thumbnails are cached in storage
- Subsequent requests use cached thumbnails
- Consider running `generate_course_thumbnails` command for bulk processing
- Course images typically have wider aspect ratios, so thumbnails are optimized for display in course cards

## API Integration

The following serializers include thumbnail fields:

- `CourseSerializer`
- `CourseReadSerializer`
- `CourseDetailSerializer`

All thumbnail fields return `null` when no image exists, making it easy for frontend applications to handle missing images gracefully.

## Example API Response

```json
{
  "id": 1,
  "title": "Python Programming",
  "description": "Learn Python from scratch",
  "image": "/media/course_images/python_course.jpg",
  "imageUrl": "http://example.com/media/course_images/python_course.jpg",
  "imageSmallUrl": "http://example.com/media/course_images/thumbnails/python_course_200x150.jpg",
  "imageMediumUrl": "http://example.com/media/course_images/thumbnails/python_course_400x300.jpg",
  "imageLargeUrl": "http://example.com/media/course_images/thumbnails/python_course_600x450.jpg"
}
```

If no image exists:

```json
{
  "id": 1,
  "title": "Python Programming",
  "description": "Learn Python from scratch",
  "image": null,
  "imageUrl": null,
  "imageSmallUrl": null,
  "imageMediumUrl": null,
  "imageLargeUrl": null
}
```
