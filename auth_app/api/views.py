from django.contrib.auth.tokens import default_token_generator
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RegisterSerializer
from .utils import send_activation_email


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
