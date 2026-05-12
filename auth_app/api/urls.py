from django.urls import path

from .views import (
    ActivateAccountView,
    LoginView,
    LogoutView,
    PasswordResetRequestView,
    RegisterView,
    TokenRefreshView,
)


urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('activate/<str:uidb64>/<str:token>/', ActivateAccountView.as_view(), name='activate'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('password_reset/', PasswordResetRequestView.as_view(), name='password-reset'),
]
