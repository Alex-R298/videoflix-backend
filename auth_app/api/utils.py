from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework_simplejwt.tokens import RefreshToken


def generate_tokens_for_user(user):
    """Return (access, refresh) JWT token strings for the given user."""
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token), str(refresh)


def _set_jwt_cookie(response, key, value):
    """Set one JWT cookie using the configured HttpOnly options."""
    cfg = settings.SIMPLE_JWT
    response.set_cookie(
        key=key, value=value,
        httponly=cfg['AUTH_COOKIE_HTTP_ONLY'], secure=cfg['AUTH_COOKIE_SECURE'],
        samesite=cfg['AUTH_COOKIE_SAMESITE'], path=cfg['AUTH_COOKIE_PATH'],
    )


def set_jwt_cookies(response, access_token, refresh_token):
    """Attach both access_token and refresh_token as HttpOnly cookies."""
    cfg = settings.SIMPLE_JWT
    _set_jwt_cookie(response, cfg['AUTH_COOKIE'], access_token)
    _set_jwt_cookie(response, cfg['AUTH_COOKIE_REFRESH'], refresh_token)


def set_access_cookie(response, access_token):
    """Set only the access_token cookie (used by /api/token/refresh/)."""
    _set_jwt_cookie(response, settings.SIMPLE_JWT['AUTH_COOKIE'], access_token)


def delete_jwt_cookies(response):
    """Remove the access_token and refresh_token cookies from the response."""
    cfg = settings.SIMPLE_JWT
    response.delete_cookie(cfg['AUTH_COOKIE'], path=cfg['AUTH_COOKIE_PATH'])
    response.delete_cookie(cfg['AUTH_COOKIE_REFRESH'], path=cfg['AUTH_COOKIE_PATH'])


def build_activation_link(user, request):
    """Build the activation URL containing uidb64 and a one-time token."""
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return f'{request.scheme}://{request.get_host()}/api/activate/{uidb64}/{token}/'


def send_activation_email(user, request):
    """Send the account activation email to the given user."""
    link = build_activation_link(user, request)
    send_mail(
        subject='Confirm your Videoflix registration',
        message=f'Hi,\n\nplease activate your account using this link:\n{link}',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


def build_password_reset_link(user, request):
    """Build the password-reset URL with uidb64 and a one-time token."""
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return f'{request.scheme}://{request.get_host()}/api/password_confirm/{uidb64}/{token}/'


def send_password_reset_email(user, request):
    """Send the password-reset email to the given user."""
    link = build_password_reset_link(user, request)
    send_mail(
        subject='Reset your Videoflix password',
        message=f'Hi,\n\nuse this link to set a new password:\n{link}',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


def get_user_from_uidb64(uidb64):
    """Decode uidb64 and return the matching user, or None if not found."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        return get_user_model().objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
        return None
