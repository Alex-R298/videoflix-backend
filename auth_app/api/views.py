from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    LoginSerializer,
    PasswordConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
)
from .utils import (
    delete_jwt_cookies,
    generate_tokens_for_user,
    get_user_from_uidb64,
    send_activation_email,
    send_password_reset_email,
    set_access_cookie,
    set_jwt_cookies,
)


LOGOUT_OK_MESSAGE = (
    'Logout successful! All tokens will be deleted. '
    'Refresh token is now invalid.'
)


class RegisterView(APIView):
    """``POST /api/register/`` — create an inactive user and mail the link."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Validate input, create the user and trigger the activation mail.

        Args:
            request: DRF request with ``email``, ``password``, ``confirmed_password``.

        Returns:
            HTTP 201 with ``{user, token}``; the token is informational only.
        """
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        send_activation_email(user, request)
        token = default_token_generator.make_token(user)
        return Response(
            {'user': serializer.data, 'token': token},
            status=status.HTTP_201_CREATED,
        )


@method_decorator(ensure_csrf_cookie, name='dispatch')
class LoginView(APIView):
    """``POST /api/login/`` — authenticate and set HttpOnly JWT cookies."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Authenticate the credentials and respond with JWT cookies.

        Args:
            request: DRF request with ``email`` and ``password``.

        Returns:
            HTTP 200 with ``{detail, user}`` and ``access_token`` /
            ``refresh_token`` cookies attached.
        """
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        access, refresh = generate_tokens_for_user(user)
        response = Response({
            'detail': 'Login successful',
            'user': {'id': user.id, 'username': user.username},
        }, status=status.HTTP_200_OK)
        set_jwt_cookies(response, access, refresh)
        return response


class LogoutView(APIView):
    """``POST /api/logout/`` — blacklist the refresh token and clear cookies."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Blacklist the user's refresh token and remove the JWT cookies.

        Args:
            request: DRF request; must carry the ``refresh_token`` cookie.

        Returns:
            HTTP 200 on success, HTTP 400 if the cookie is missing or invalid.
        """
        raw = request.COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH'])
        if not raw:
            return Response({'detail': 'Refresh token missing.'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            RefreshToken(raw).blacklist()
        except TokenError:
            return Response({'detail': 'Refresh token invalid.'},
                            status=status.HTTP_400_BAD_REQUEST)
        response = Response({'detail': LOGOUT_OK_MESSAGE}, status=status.HTTP_200_OK)
        delete_jwt_cookies(response)
        return response


class ActivateAccountView(APIView):
    """``GET /api/activate/<uidb64>/<token>/`` — activate a registered user."""

    permission_classes = [AllowAny]

    def get(self, request, uidb64, token):
        """Validate the activation link and flip ``is_active`` to True.

        Args:
            request: DRF request.
            uidb64: Base64-encoded user PK from the email link.
            token: One-time activation token from the email link.

        Returns:
            HTTP 200 with a success message, or HTTP 400 when the link is invalid.
        """
        user = get_user_from_uidb64(uidb64)
        if user is None or not default_token_generator.check_token(user, token):
            return Response({'detail': 'Activation failed.'},
                            status=status.HTTP_400_BAD_REQUEST)
        user.is_active = True
        user.save(update_fields=['is_active'])
        return Response({'message': 'Account successfully activated.'},
                        status=status.HTTP_200_OK)


class TokenRefreshView(APIView):
    """``POST /api/token/refresh/`` — issue a new access token from the cookie."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Validate the refresh cookie and return a fresh access token.

        Args:
            request: DRF request; must carry the ``refresh_token`` cookie.

        Returns:
            HTTP 200 with ``{detail, access}`` and an updated access cookie,
            HTTP 400 when the cookie is missing, HTTP 401 when invalid.
        """
        raw = request.COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE_REFRESH'])
        if not raw:
            return Response({'detail': 'Refresh token missing.'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            refresh = RefreshToken(raw)
        except TokenError:
            return Response({'detail': 'Refresh token invalid.'},
                            status=status.HTTP_401_UNAUTHORIZED)
        access = str(refresh.access_token)
        response = Response({'detail': 'Token refreshed', 'access': access},
                            status=status.HTTP_200_OK)
        set_access_cookie(response, access)
        return response


class PasswordResetRequestView(APIView):
    """``POST /api/password_reset/`` — mail a reset link if the address exists."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Send a password-reset mail without leaking whether the email exists.

        Args:
            request: DRF request with the ``email`` field.

        Returns:
            HTTP 200 with the same response in both cases; the mail is only
            actually dispatched when a user with that address exists.
        """
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_user_model().objects.filter(email=serializer.validated_data['email']).first()
        if user is not None:
            send_password_reset_email(user, request)
        return Response(
            {'detail': 'An email has been sent to reset your password.'},
            status=status.HTTP_200_OK,
        )


class PasswordConfirmView(APIView):
    """``POST /api/password_confirm/<uidb64>/<token>/`` — set the new password."""

    permission_classes = [AllowAny]

    def post(self, request, uidb64, token):
        """Validate the reset link and persist the new password.

        Args:
            request: DRF request with ``new_password`` and ``confirm_password``.
            uidb64: Base64-encoded user PK from the email link.
            token: One-time reset token from the email link.

        Returns:
            HTTP 200 on success, HTTP 400 on an invalid link or input.
        """
        user = get_user_from_uidb64(uidb64)
        if user is None or not default_token_generator.check_token(user, token):
            return Response({'detail': 'Invalid reset link.'},
                            status=status.HTTP_400_BAD_REQUEST)
        serializer = PasswordConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        return Response(
            {'detail': 'Your Password has been successfully reset.'},
            status=status.HTTP_200_OK,
        )
