from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import LoginSerializer, RegisterSerializer
from .utils import (
    delete_jwt_cookies,
    generate_tokens_for_user,
    send_activation_email,
    set_jwt_cookies,
)


LOGOUT_OK_MESSAGE = (
    'Logout successful! All tokens will be deleted. '
    'Refresh token is now invalid.'
)


class RegisterView(APIView):
    """POST /api/register/ — create an inactive user and send the activation mail."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        send_activation_email(user, request)
        token = default_token_generator.make_token(user)
        return Response(
            {'user': serializer.data, 'token': token},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """POST /api/login/ — authenticate the user and set HttpOnly JWT cookies."""

    permission_classes = [AllowAny]

    def post(self, request):
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
    """POST /api/logout/ — blacklist the refresh token and clear JWT cookies."""

    permission_classes = [AllowAny]

    def post(self, request):
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
