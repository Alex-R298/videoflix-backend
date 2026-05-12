from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework_simplejwt.tokens import RefreshToken


def generate_tokens_for_user(user):
    """Return (access, refresh) JWT token strings for the given user."""
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token), str(refresh)


def set_jwt_cookies(response, access_token, refresh_token):
    """Attach access_token and refresh_token as HttpOnly cookies to the response."""
    cfg = settings.SIMPLE_JWT
    response.set_cookie(
        key=cfg['AUTH_COOKIE'], value=access_token,
        httponly=cfg['AUTH_COOKIE_HTTP_ONLY'], secure=cfg['AUTH_COOKIE_SECURE'],
        samesite=cfg['AUTH_COOKIE_SAMESITE'], path=cfg['AUTH_COOKIE_PATH'],
    )
    response.set_cookie(
        key=cfg['AUTH_COOKIE_REFRESH'], value=refresh_token,
        httponly=cfg['AUTH_COOKIE_HTTP_ONLY'], secure=cfg['AUTH_COOKIE_SECURE'],
        samesite=cfg['AUTH_COOKIE_SAMESITE'], path=cfg['AUTH_COOKIE_PATH'],
    )


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
