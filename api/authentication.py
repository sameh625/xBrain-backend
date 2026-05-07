from drf_spectacular.extensions import OpenApiAuthenticationExtension
from django.core.cache import cache
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


ACCESS_BLACKLIST_KEY_PREFIX = 'jwt_access_blacklist_'


def access_blacklist_key(jti: str) -> str:
    return f'{ACCESS_BLACKLIST_KEY_PREFIX}{jti}'


class BlacklistAwareJWTAuthentication(JWTAuthentication):
    def get_validated_token(self, raw_token):
        validated_token = super().get_validated_token(raw_token)
        jti = validated_token.get('jti')
        if jti and cache.get(access_blacklist_key(jti)):
            raise InvalidToken('Access token has been logged out.')
        return validated_token



class BlacklistAwareJWTScheme(OpenApiAuthenticationExtension):
    target_class = 'api.authentication.BlacklistAwareJWTAuthentication'
    name = 'jwtAuth'
    match_subclasses = False
    priority = 1

    def get_security_definition(self, auto_schema):
        return {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
        }