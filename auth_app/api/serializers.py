from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers


User = get_user_model()

GENERIC_INPUT_ERROR = 'Please check your input and try again.'


class LoginSerializer(serializers.Serializer):
    """Validate credentials and resolve the matching active user."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs['email'], password=attrs['password'])
        if user is None or not user.is_active:
            raise serializers.ValidationError(GENERIC_INPUT_ERROR)
        attrs['user'] = user
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """Validate the password-reset request input (email field only)."""

    email = serializers.EmailField()


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
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(GENERIC_INPUT_ERROR)
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['confirmed_password']:
            raise serializers.ValidationError({'confirmed_password': GENERIC_INPUT_ERROR})
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirmed_password')
        email = validated_data['email']
        return User.objects.create_user(
            username=email, email=email,
            password=validated_data['password'], is_active=False,
        )
