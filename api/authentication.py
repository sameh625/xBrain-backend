"""Custom JWT authentication that respects an access-token blacklist.

By default, rest_framework_simplejwt only blacklists *refresh* tokens.
Access tokens are short-lived and remain valid until they expire naturally,
which means a user who calls /api/auth/logout/ can still use their access
token for up to its remaining TTL.

This module fixes that. On logout, the LogoutView writes the access token's
`jti` (JWT ID) to a Redis key with TTL equal to the token's remaining lifetime.
This authentication class checks that key on every request; if present, the
token is rejected.

Cost per authenticated request: one Redis GET. Sub-millisecond.
"""

from django.core.cache import cache
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


ACCESS_BLACKLIST_KEY_PREFIX = 'jwt_access_blacklist_'


def access_blacklist_key(jti: str) -> str:
    return f'{ACCESS_BLACKLIST_KEY_PREFIX}{jti}'


class BlacklistAwareJWTAuthentication(JWTAuthentication):
    """JWTAuthentication that also rejects access tokens whose `jti` is in
    the cache-backed access-token blacklist."""

    def get_validated_token(self, raw_token):
        validated_token = super().get_validated_token(raw_token)
        jti = validated_token.get('jti')
        if jti and cache.get(access_blacklist_key(jti)):
            raise InvalidToken('Access token has been logged out.')
        return validated_token
