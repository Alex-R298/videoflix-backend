from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
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


def _make_uid_and_token(user):
    """Return (uidb64, token) for a one-time email link."""
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return uidb64, token


def build_activation_link(user):
    """Build the frontend activation URL with uid and token as query params."""
    uidb64, token = _make_uid_and_token(user)
    return (
        f'{settings.FRONTEND_URL}{settings.FRONTEND_ACTIVATION_PATH}'
        f'?uid={uidb64}&token={token}'
    )


def build_password_reset_link(user):
    """Build the frontend password-reset URL with uid and token as query params."""
    uidb64, token = _make_uid_and_token(user)
    return (
        f'{settings.FRONTEND_URL}{settings.FRONTEND_PASSWORD_RESET_PATH}'
        f'?uid={uidb64}&token={token}'
    )


def _send_html_email(subject, template_base, context, recipient):
    """Render a plain + HTML email pair from templates and send it."""
    text_body = render_to_string(f'emails/{template_base}.txt', context)
    html_body = render_to_string(f'emails/{template_base}.html', context)
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )
    message.attach_alternative(html_body, 'text/html')
    message.send()


def send_activation_email(user, request=None):
    """Send the account activation email (HTML + plain) to the given user."""
    link = build_activation_link(user)
    _send_html_email(
        subject='Confirm your email',
        template_base='activation',
        context={
            'activation_link': link,
            'frontend_url': settings.FRONTEND_URL,
            'user': user,
        },
        recipient=user.email,
    )


def send_password_reset_email(user, request=None):
    """Send the password-reset email (HTML + plain) to the given user."""
    link = build_password_reset_link(user)
    _send_html_email(
        subject='Reset your Password',
        template_base='password_reset',
        context={'reset_link': link, 'user': user},
        recipient=user.email,
    )


def get_user_from_uidb64(uidb64):
    """Decode uidb64 and return the matching user, or None if not found."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        return get_user_model().objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
        return None
