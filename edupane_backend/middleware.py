from urllib.parse import parse_qs
from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from django.conf import settings
from django.db import close_old_connections
from jwt import InvalidSignatureError, ExpiredSignatureError, DecodeError
from jwt import decode as jwt_decode


class JWTAuthMiddleware:
    """Middleware to authenticate user for channels"""

    def __init__(self, app):
        """Initialize the app."""
        self.app = app

    async def __call__(self, scope, receive, send):
        """Authenticate the user based on jwt."""
        # Import lazily here (safe after Django setup)
        from django.contrib.auth.models import AnonymousUser  

        close_old_connections()
        try:
            # Decode query string and get token parameter
            token = parse_qs(scope["query_string"].decode("utf8")).get('token', None)[0]

            # Decode JWT
            data = jwt_decode(token, settings.SECRET_KEY, algorithms=["HS256"])

            # Attach user to scope
            scope['user'] = await self.get_user(data['user_id'])
        except (TypeError, KeyError, InvalidSignatureError, ExpiredSignatureError, DecodeError):
            scope['user'] = AnonymousUser()
        return await self.app(scope, receive, send)

    @database_sync_to_async
    def get_user(self, user_id):
        """Return the user based on user id."""
        # Lazy import to avoid AppRegistryNotReady
        from django.contrib.auth.models import AnonymousUser  
        from users.models import User  

        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return AnonymousUser()
        except Exception as e:
            print(f"Error getting user: {e}")
            return AnonymousUser()


def JWTAuthMiddlewareStack(app):
    """Wrap channels authentication stack with JWTAuthMiddleware."""
    return JWTAuthMiddleware(AuthMiddlewareStack(app))
