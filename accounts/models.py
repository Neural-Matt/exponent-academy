from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserRole(models.TextChoices):
    LEARNER = 'LEARNER', 'Learner'
    TRAINER = 'TRAINER', 'Trainer'
    HR_ADMIN = 'HR_ADMIN', 'HR Admin'
    TEAM_LEAD = 'TEAM_LEAD', 'Team Lead'


class UserManager(BaseUserManager):
    def create_user(self, staff_number, password=None, **extra_fields):
        if not staff_number:
            raise ValueError('Staff number is required')
        user = self.model(staff_number=staff_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, staff_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', UserRole.HR_ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(staff_number, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    staff_number = models.CharField(max_length=50, unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True, default='')
    department = models.CharField(max_length=150, blank=True, default='')
    job_title = models.CharField(max_length=150, blank=True, default='')
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.LEARNER,
    )
    date_joined = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    must_reset_password = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'staff_number'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['staff_number']

    def __str__(self):
        return f'{self.staff_number} – {self.get_full_name()}'

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    def get_short_name(self):
        return self.first_name
