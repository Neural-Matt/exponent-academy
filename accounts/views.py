import uuid

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.shortcuts import get_object_or_404, redirect, render

from .forms import BulkUploadForm, LoginForm
from .models import User, UserRole


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user, backend='accounts.backends.StaffNumberBackend')
        if user.must_reset_password:
            return redirect('password_reset_required')
        return redirect('dashboard')

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def password_reset_required_view(request):
    """Force password change on first login."""
    if not request.user.must_reset_password:
        return redirect('dashboard')

    form = SetPasswordForm(user=request.user, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        request.user.must_reset_password = False
        request.user.save(update_fields=['must_reset_password'])
        messages.success(request, 'Password updated successfully. Please log in again.')
        logout(request)
        return redirect('login')

    return render(request, 'accounts/password_reset_required.html', {'form': form})


@login_required
def dashboard_view(request):
    return render(request, 'accounts/dashboard.html')


@login_required
def bulk_upload_view(request):
    if request.user.role != UserRole.HR_ADMIN and not request.user.is_superuser:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')

    form = BulkUploadForm(request.POST or None, request.FILES or None)
    results = None

    if request.method == 'POST' and form.is_valid():
        rows = form.cleaned_data['csv_file']
        results = _process_bulk_upload(rows)
        messages.success(
            request,
            f'Bulk upload complete: {results["created"]} created, '
            f'{results["skipped"]} skipped (already exist).',
        )

    return render(request, 'accounts/bulk_upload.html', {'form': form, 'results': results})


def _process_bulk_upload(rows):
    created = 0
    skipped = 0
    details = []

    for row in rows:
        staff_number = row['staff_number']
        if User.objects.filter(staff_number=staff_number).exists():
            skipped += 1
            details.append({'staff_number': staff_number, 'status': 'skipped', 'reason': 'already exists'})
            continue

        # Generate a secure random default password
        default_password = uuid.uuid4().hex

        user = User(
            staff_number=staff_number,
            first_name=row.get('first_name', ''),
            last_name=row.get('last_name', ''),
            phone=row.get('phone', ''),
            department=row.get('department', ''),
            job_title=row.get('job_title', ''),
            role=UserRole.LEARNER,
            must_reset_password=True,
        )
        user.set_password(default_password)
        user.save()
        created += 1
        details.append({
            'staff_number': staff_number,
            'status': 'created',
            'name': user.get_full_name(),
            'default_password': default_password,
        })

    return {'created': created, 'skipped': skipped, 'details': details}
