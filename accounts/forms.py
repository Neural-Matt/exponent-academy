import csv
import io

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import SetPasswordForm  # noqa: F401 – re-exported


class LoginForm(forms.Form):
    staff_number = forms.CharField(
        label='Staff Number',
        max_length=50,
        widget=forms.TextInput(attrs={'autofocus': True, 'placeholder': 'Staff Number'}),
    )
    password = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Password'}),
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        staff_number = self.cleaned_data.get('staff_number')
        password = self.cleaned_data.get('password')

        if staff_number and password:
            self.user_cache = authenticate(
                self.request,
                staff_number=staff_number,
                password=password,
            )
            if self.user_cache is None:
                raise forms.ValidationError('Invalid staff number or password.')
            if not self.user_cache.is_active:
                raise forms.ValidationError('This account is inactive.')
        return self.cleaned_data

    def get_user(self):
        return self.user_cache


REQUIRED_CSV_FIELDS = {'staff_number', 'first_name', 'last_name'}
OPTIONAL_CSV_FIELDS = {'department', 'job_title', 'phone'}
ALL_CSV_FIELDS = REQUIRED_CSV_FIELDS | OPTIONAL_CSV_FIELDS


class BulkUploadForm(forms.Form):
    csv_file = forms.FileField(
        label='CSV File',
        help_text=(
            'Upload a CSV file with columns: staff_number, first_name, last_name, '
            'department, job_title, phone'
        ),
    )

    def clean_csv_file(self):
        uploaded = self.cleaned_data['csv_file']
        if not uploaded.name.lower().endswith('.csv'):
            raise forms.ValidationError('Only CSV files are accepted.')

        try:
            raw = uploaded.read().decode('utf-8-sig')  # handle BOM
        except UnicodeDecodeError:
            raise forms.ValidationError('File must be UTF-8 encoded.')

        reader = csv.DictReader(io.StringIO(raw))
        if reader.fieldnames is None:
            raise forms.ValidationError('The CSV file is empty.')

        headers = {h.strip().lower() for h in reader.fieldnames}
        missing = REQUIRED_CSV_FIELDS - headers
        if missing:
            raise forms.ValidationError(
                f'Missing required column(s): {", ".join(sorted(missing))}'
            )

        rows = []
        for i, row in enumerate(reader, start=2):  # row 1 is the header
            normalised = {k.strip().lower(): v.strip() for k, v in row.items() if k}
            if not normalised.get('staff_number'):
                raise forms.ValidationError(f'Row {i}: staff_number is required.')
            if not normalised.get('first_name'):
                raise forms.ValidationError(f'Row {i}: first_name is required.')
            if not normalised.get('last_name'):
                raise forms.ValidationError(f'Row {i}: last_name is required.')
            rows.append(normalised)

        if not rows:
            raise forms.ValidationError('The CSV file contains no data rows.')

        # Return parsed rows so the view doesn't have to re-parse
        return rows
