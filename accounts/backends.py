from django.contrib.auth import get_user_model

User = get_user_model()


class StaffNumberBackend:
    """Authenticate using staff_number instead of username."""

    def authenticate(self, request, staff_number=None, password=None, **kwargs):
        if staff_number is None:
            staff_number = kwargs.get(User.USERNAME_FIELD)
        if staff_number is None or password is None:
            return None
        try:
            user = User.objects.get(staff_number=staff_number)
        except User.DoesNotExist:
            # Run the default password hasher to reduce timing attack surface
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def user_can_authenticate(self, user):
        return user.is_active

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
