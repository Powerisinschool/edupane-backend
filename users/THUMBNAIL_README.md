# User Avatar Thumbnail System

This document explains the new avatar thumbnail system implemented in the User model.

## Overview

The User model now includes built-in thumbnail generation for avatars. This replaces the previous complex Image model approach with a simpler, more efficient solution.

## Features

- **On-demand thumbnail generation**: Thumbnails are created when first requested
- **Multiple sizes**: Support for small (100x100), medium (200x200), and large (300x300) thumbnails
- **Automatic cleanup**: Old thumbnails are deleted when avatars are updated
- **Fallback support**: Returns default avatar URL when no avatar exists
- **Storage efficient**: Only stores thumbnails when actually needed

## Usage

### In Python Code

```python
# Get different thumbnail sizes
user = User.objects.get(username='example')

# Default thumbnail (100x100)
thumbnail_url = user.get_avatar_thumbnail_url()

# Specific sizes
small_url = user.get_avatar_small_url()      # 100x100
medium_url = user.get_avatar_medium_url()    # 200x200
large_url = user.get_avatar_large_url()      # 300x300

# Custom size
custom_url = user.get_avatar_thumbnail_url((150, 150))
```

### In API Responses

The User serializer now includes these fields:

- `avatarThumbnailUrl`: Default thumbnail (100x100)
- `avatarSmallUrl`: Small thumbnail (100x100)
- `avatarMediumUrl`: Medium thumbnail (200x200)
- `avatarLargeUrl`: Large thumbnail (300x300)

### Management Commands

Generate thumbnails for all users:

```bash
# Generate default thumbnails (100x100)
python manage.py generate_thumbnails

# Generate custom size thumbnails
python manage.py generate_thumbnails --size 200,200

# Force regeneration of existing thumbnails
python manage.py generate_thumbnails --force
```

## Implementation Details

### Storage Structure

```
media/
├── avatars/
│   ├── user_avatar.jpg
│   └── thumbnails/
│       ├── user_avatar_100x100.jpg
│       ├── user_avatar_200x200.jpg
│       └── user_avatar_300x300.jpg
```

### Key Methods

- `get_avatar_thumbnail_url(size)`: Get or generate thumbnail URL
- `_get_thumbnail_path(size)`: Generate thumbnail file path
- `_generate_thumbnail(size)`: Create and save thumbnail
- `_delete_avatar_thumbnails()`: Clean up old thumbnails

### Error Handling

- If thumbnail generation fails, returns the original avatar URL
- If no avatar exists, returns the default avatar URL
- All errors are logged but don't break the application

## Migration from Old System

If you were using the previous Image model for avatars:

1. The User model now handles thumbnails directly
2. No need for separate Image model instances
3. Thumbnails are generated automatically when needed
4. Old thumbnails are cleaned up automatically

## Testing

Run the tests to verify functionality:

```bash
python manage.py test users.tests.UserAvatarThumbnailTest
```

## Performance Considerations

- Thumbnails are generated on first request (lazy loading)
- Generated thumbnails are cached in storage
- Subsequent requests use cached thumbnails
- Consider running `generate_thumbnails` command for bulk processing
