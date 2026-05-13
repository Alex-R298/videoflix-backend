from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


class CookieJWTAuthentication(JWTAuthentication):
    """JWT authentication that reads the access token from an HttpOnly cookie.

    Replaces SimpleJWT's default ``Authorization: Bearer ...`` header lookup
    with a cookie lookup so the frontend never has to handle the raw token.
    """

    def authenticate(self, request):
        """Resolve the request's user from the ``access_token`` cookie.

        Args:
            request: Incoming Django/DRF request.

        Returns:
            tuple[User, Token] when a valid cookie is present, otherwise
            ``None`` — letting downstream permissions treat the request as
            anonymous instead of raising 401.
        """
        raw_token = request.COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE'])
        if raw_token is None:
            return None
        try:
            validated_token = self.get_validated_token(raw_token)
        except InvalidToken:
            return None
        return self.get_user(validated_token), validated_token
