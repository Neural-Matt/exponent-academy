from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from accounts.backends import StaffNumberBackend
from accounts.forms import BulkUploadForm, LoginForm
from accounts.models import UserRole

User = get_user_model()


def _make_uploaded_file(content, name='employees.csv'):
    return SimpleUploadedFile(name, content.encode('utf-8'), content_type='text/csv')


class UserModelTest(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(
            staff_number='EMP001',
            password='testpass123',
            first_name='Alice',
            last_name='Smith',
        )
        self.assertEqual(user.staff_number, 'EMP001')
        self.assertEqual(user.get_full_name(), 'Alice Smith')
        self.assertTrue(user.check_password('testpass123'))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertEqual(user.role, UserRole.LEARNER)

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            staff_number='ADMIN001',
            password='adminpass123',
            first_name='Bob',
            last_name='Admin',
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.role, UserRole.HR_ADMIN)

    def test_staff_number_is_unique(self):
        User.objects.create_user(staff_number='DUP001', password='pass')
        with self.assertRaises(Exception):
            User.objects.create_user(staff_number='DUP001', password='other')

    def test_str(self):
        user = User.objects.create_user(
            staff_number='EMP002', password='p', first_name='Carol', last_name='Jones'
        )
        self.assertIn('EMP002', str(user))

    def test_username_field(self):
        self.assertEqual(User.USERNAME_FIELD, 'staff_number')


class StaffNumberBackendTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            staff_number='EMP010', password='correct', first_name='Dan', last_name='Brown'
        )
        self.backend = StaffNumberBackend()

    def test_authenticate_correct(self):
        user = self.backend.authenticate(None, staff_number='EMP010', password='correct')
        self.assertEqual(user, self.user)

    def test_authenticate_wrong_password(self):
        user = self.backend.authenticate(None, staff_number='EMP010', password='wrong')
        self.assertIsNone(user)

    def test_authenticate_unknown_user(self):
        user = self.backend.authenticate(None, staff_number='UNKNOWN', password='any')
        self.assertIsNone(user)

    def test_authenticate_inactive_user(self):
        self.user.is_active = False
        self.user.save()
        user = self.backend.authenticate(None, staff_number='EMP010', password='correct')
        self.assertIsNone(user)

    def test_get_user(self):
        user = self.backend.get_user(self.user.pk)
        self.assertEqual(user, self.user)

    def test_get_user_invalid_id(self):
        user = self.backend.get_user(99999)
        self.assertIsNone(user)


class LoginFormTest(TestCase):
    def setUp(self):
        User.objects.create_user(
            staff_number='EMP020', password='mypassword', first_name='Eve', last_name='Clark'
        )

    def test_valid_login(self):
        form = LoginForm(data={'staff_number': 'EMP020', 'password': 'mypassword'})
        self.assertTrue(form.is_valid())
        self.assertIsNotNone(form.get_user())

    def test_invalid_password(self):
        form = LoginForm(data={'staff_number': 'EMP020', 'password': 'wrong'})
        self.assertFalse(form.is_valid())

    def test_unknown_staff_number(self):
        form = LoginForm(data={'staff_number': 'UNKNOWN', 'password': 'any'})
        self.assertFalse(form.is_valid())


class BulkUploadFormTest(TestCase):
    def test_valid_csv(self):
        csv_file = _make_uploaded_file(
            'staff_number,first_name,last_name,department\nEMP030,Frank,Green,IT\n'
        )
        form = BulkUploadForm(data={}, files={'csv_file': csv_file})
        self.assertTrue(form.is_valid(), form.errors)
        rows = form.cleaned_data['csv_file']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['staff_number'], 'EMP030')

    def test_missing_required_column(self):
        csv_file = _make_uploaded_file('staff_number,first_name\nEMP031,Grace\n')
        form = BulkUploadForm(data={}, files={'csv_file': csv_file})
        self.assertFalse(form.is_valid())
        self.assertIn('last_name', str(form.errors))

    def test_empty_csv(self):
        csv_file = _make_uploaded_file('staff_number,first_name,last_name\n')
        form = BulkUploadForm(data={}, files={'csv_file': csv_file})
        self.assertFalse(form.is_valid())

    def test_non_csv_file(self):
        f = SimpleUploadedFile('data.txt', b'not a csv', content_type='text/plain')
        form = BulkUploadForm(data={}, files={'csv_file': f})
        self.assertFalse(form.is_valid())


class BulkUploadViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.hr_admin = User.objects.create_user(
            staff_number='HR001',
            password='hrpass',
            first_name='HR',
            last_name='Admin',
            role=UserRole.HR_ADMIN,
        )
        self.learner = User.objects.create_user(
            staff_number='LEA001',
            password='learnerpass',
            first_name='Learner',
            last_name='User',
            role=UserRole.LEARNER,
        )

    def _login(self, user, password):
        self.client.post(
            reverse('login'),
            {'staff_number': user.staff_number, 'password': password},
        )

    def test_unauthenticated_redirects(self):
        response = self.client.get(reverse('bulk_upload'))
        self.assertRedirects(response, '/accounts/login/?next=/accounts/bulk-upload/')

    def test_learner_denied(self):
        self._login(self.learner, 'learnerpass')
        response = self.client.get(reverse('bulk_upload'))
        self.assertRedirects(response, reverse('dashboard'))

    def test_hr_admin_can_access(self):
        self._login(self.hr_admin, 'hrpass')
        response = self.client.get(reverse('bulk_upload'))
        self.assertEqual(response.status_code, 200)

    def test_bulk_upload_creates_users(self):
        self._login(self.hr_admin, 'hrpass')
        csv_file = _make_uploaded_file(
            'staff_number,first_name,last_name,department,job_title,phone\n'
            'NEW001,New,User,Engineering,Dev,+1234\n'
        )
        response = self.client.post(reverse('bulk_upload'), {'csv_file': csv_file})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(staff_number='NEW001').exists())
        new_user = User.objects.get(staff_number='NEW001')
        self.assertTrue(new_user.must_reset_password)
        self.assertEqual(new_user.department, 'Engineering')

    def test_bulk_upload_skips_existing(self):
        self._login(self.hr_admin, 'hrpass')
        csv_file = _make_uploaded_file(
            f'staff_number,first_name,last_name\n{self.learner.staff_number},Learner,User\n'
        )
        response = self.client.post(reverse('bulk_upload'), {'csv_file': csv_file})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(staff_number=self.learner.staff_number).count(), 1)


class PasswordResetRequiredViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            staff_number='EMP050',
            password='oldpass123',
            first_name='Henry',
            last_name='Ford',
            must_reset_password=True,
        )

    def test_redirects_to_reset_on_first_login(self):
        response = self.client.post(
            reverse('login'),
            {'staff_number': 'EMP050', 'password': 'oldpass123'},
            follow=True,
        )
        self.assertRedirects(response, reverse('password_reset_required'))

    def test_password_change_clears_flag(self):
        self.client.post(
            reverse('login'),
            {'staff_number': 'EMP050', 'password': 'oldpass123'},
        )
        response = self.client.post(
            reverse('password_reset_required'),
            {'new_password1': 'newSecurePass99!', 'new_password2': 'newSecurePass99!'},
        )
        self.user.refresh_from_db()
        self.assertFalse(self.user.must_reset_password)
