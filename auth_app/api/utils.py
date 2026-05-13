from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework_simplejwt.tokens import RefreshToken


def generate_tokens_for_user(user):
    """Create a fresh JWT pair for the given user.

    Args:
        user: The Django user the tokens should be issued for.

    Returns:
        tuple[str, str]: (access_token, refresh_token) as encoded strings.
    """
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token), str(refresh)


def _set_jwt_cookie(response, key, value):
    """Attach one JWT cookie to a response using the configured options.

    Args:
        response: The DRF/Django response to mutate.
        key: Cookie name (e.g. ``access_token``).
        value: Raw JWT string.
    """
    cfg = settings.SIMPLE_JWT
    response.set_cookie(
        key=key, value=value,
        httponly=cfg['AUTH_COOKIE_HTTP_ONLY'], secure=cfg['AUTH_COOKIE_SECURE'],
        samesite=cfg['AUTH_COOKIE_SAMESITE'], path=cfg['AUTH_COOKIE_PATH'],
    )


def set_jwt_cookies(response, access_token, refresh_token):
    """Attach both JWT cookies (access + refresh) to a response.

    Args:
        response: The response object the cookies are added to.
        access_token: Encoded access token string.
        refresh_token: Encoded refresh token string.
    """
    cfg = settings.SIMPLE_JWT
    _set_jwt_cookie(response, cfg['AUTH_COOKIE'], access_token)
    _set_jwt_cookie(response, cfg['AUTH_COOKIE_REFRESH'], refresh_token)


def set_access_cookie(response, access_token):
    """Set only the access-token cookie (used by ``/api/token/refresh/``).

    Args:
        response: The response object the cookie is added to.
        access_token: Encoded access token string.
    """
    _set_jwt_cookie(response, settings.SIMPLE_JWT['AUTH_COOKIE'], access_token)


def delete_jwt_cookies(response):
    """Remove both JWT cookies from a response.

    Args:
        response: The response object the cookies are removed from.
    """
    cfg = settings.SIMPLE_JWT
    response.delete_cookie(cfg['AUTH_COOKIE'], path=cfg['AUTH_COOKIE_PATH'])
    response.delete_cookie(cfg['AUTH_COOKIE_REFRESH'], path=cfg['AUTH_COOKIE_PATH'])


def _make_uid_and_token(user):
    """Encode the user PK and create a one-time signed token.

    Args:
        user: Django user the token is bound to.

    Returns:
        tuple[str, str]: (uidb64, token) ready to embed in an email link.
    """
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return uidb64, token


def build_activation_link(user):
    """Build the frontend activation URL with uid+token query params.

    Args:
        user: The user the activation link is for.

    Returns:
        str: Full frontend URL (e.g. ``http://.../activate.html?uid=...&token=...``).
    """
    uidb64, token = _make_uid_and_token(user)
    return (
        f'{settings.FRONTEND_URL}{settings.FRONTEND_ACTIVATION_PATH}'
        f'?uid={uidb64}&token={token}'
    )


def build_password_reset_link(user):
    """Build the frontend password-reset URL with uid+token query params.

    Args:
        user: The user the reset link is for.

    Returns:
        str: Full frontend URL pointing to the confirm-password page.
    """
    uidb64, token = _make_uid_and_token(user)
    return (
        f'{settings.FRONTEND_URL}{settings.FRONTEND_PASSWORD_RESET_PATH}'
        f'?uid={uidb64}&token={token}'
    )


def _send_html_email(subject, template_base, context, recipient):
    """Render plain+HTML email templates and dispatch the message.

    Args:
        subject: Email subject line.
        template_base: Filename stem under ``templates/emails/`` (e.g. ``activation``).
        context: Mapping passed to both templates.
        recipient: Email address of the recipient.
    """
    text_body = render_to_string(f'emails/{template_base}.txt', context)
    html_body = render_to_string(f'emails/{template_base}.html', context)
    message = EmailMultiAlternatives(
        subject=subject, body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL, to=[recipient],
    )
    message.attach_alternative(html_body, 'text/html')
    message.send()


def send_activation_email(user, request=None):
    """Send the account activation email to the user.

    Args:
        user: The freshly registered user.
        request: Unused; kept for backwards compatibility with views.
    """
    _send_html_email(
        subject='Confirm your email',
        template_base='activation',
        context={
            'activation_link': build_activation_link(user),
            'frontend_url': settings.FRONTEND_URL,
            'user': user,
        },
        recipient=user.email,
    )


def send_password_reset_email(user, request=None):
    """Send the password-reset email to the user.

    Args:
        user: The user requesting the reset.
        request: Unused; kept for backwards compatibility with views.
    """
    _send_html_email(
        subject='Reset your Password',
        template_base='password_reset',
        context={'reset_link': build_password_reset_link(user), 'user': user},
        recipient=user.email,
    )


def get_user_from_uidb64(uidb64):
    """Resolve a user from a base64-encoded primary key.

    Args:
        uidb64: Base64-encoded user PK from an email link.

    Returns:
        The matching ``User`` instance, or ``None`` if decoding fails or no
        user with that PK exists.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        return get_user_model().objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
        return None
