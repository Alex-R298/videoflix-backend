from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers


User = get_user_model()

GENERIC_INPUT_ERROR = 'Please check your input and try again.'


class LoginSerializer(serializers.Serializer):
    """Validate login credentials and attach the resolved active user."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Authenticate the credentials and store the user on ``attrs``.

        Args:
            attrs: Raw input dict containing ``email`` and ``password``.

        Returns:
            The same dict, extended with ``attrs['user']``.

        Raises:
            ValidationError: With a generic message when the credentials are
            wrong or the user is not active (no leaking which case it is).
        """
        user = authenticate(username=attrs['email'], password=attrs['password'])
        if user is None or not user.is_active:
            raise serializers.ValidationError(GENERIC_INPUT_ERROR)
        attrs['user'] = user
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """Validate the body of the password-reset request (email only)."""

    email = serializers.EmailField()


class PasswordConfirmSerializer(serializers.Serializer):
    """Validate the new password fields for the password-reset confirm step."""

    new_password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        """Ensure ``new_password`` and ``confirm_password`` match.

        Args:
            attrs: Raw input dict.

        Returns:
            The same dict when both fields match.

        Raises:
            ValidationError: When the fields do not match.
        """
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': GENERIC_INPUT_ERROR})
        return attrs


class RegisterSerializer(serializers.ModelSerializer):
    """Validate registration input and create an inactive user."""

    password = serializers.CharField(write_only=True, required=True)
    confirmed_password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'password', 'confirmed_password')
        read_only_fields = ('id',)
        extra_kwargs = {'email': {'required': True, 'allow_blank': False}}

    def validate_email(self, value):
        """Reject the email if a user with the same address already exists.

        Args:
            value: Submitted email address.

        Returns:
            The same value, untouched, when it is unique.

        Raises:
            ValidationError: With a generic message if the email is taken.
        """
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(GENERIC_INPUT_ERROR)
        return value

    def validate(self, attrs):
        """Ensure ``password`` and ``confirmed_password`` match.

        Args:
            attrs: Raw input dict.

        Returns:
            The same dict when the passwords match.

        Raises:
            ValidationError: When the passwords differ.
        """
        if attrs['password'] != attrs['confirmed_password']:
            raise serializers.ValidationError({'confirmed_password': GENERIC_INPUT_ERROR})
        return attrs

    def create(self, validated_data):
        """Create the new inactive user; username is set to the email.

        Args:
            validated_data: Cleaned data from ``is_valid()``.

        Returns:
            The newly created ``User`` instance with ``is_active=False``.
        """
        validated_data.pop('confirmed_password')
        email = validated_data['email']
        return User.objects.create_user(
            username=email, email=email,
            password=validated_data['password'], is_active=False,
        )
