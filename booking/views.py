from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Organization, TimeSlot, Booking, Region, Category
from .forms import UserRegisterForm, BookingForm, TimeSlotForm
from django.utils import timezone

def home(request):
    regions = Region.objects.filter(is_active=True, is_featured=True)
    categories = Category.objects.filter(is_active=True, is_featured=True)
    return render(request, 'home.html', {'regions': regions, 'categories': categories})

def organization_list(request):
    organizations = Organization.objects.filter(is_active=True)
    region_id = request.GET.get('region')
    category_id = request.GET.get('category')
    if region_id:
        organizations = organizations.filter(region_id=region_id)
    if category_id:
        organizations = organizations.filter(category_id=category_id)
    regions = Region.objects.filter(is_active=True)
    categories = Category.objects.filter(is_active=True)
    return render(request, 'organization_list.html', {
        'organizations': organizations,
        'regions': regions,
        'categories': categories,
    })

def organization_detail(request, slug):
    organization = get_object_or_404(Organization, slug=slug, is_active=True)
    time_slots = TimeSlot.objects.filter(organization=organization, start_time__gte=timezone.now(), is_booked=False)
    return render(request, 'organization_detail.html', {
        'organization': organization,
        'time_slots': time_slots,
    })

@login_required
def book_slot(request, slot_id):
    time_slot = get_object_or_404(TimeSlot, id=slot_id, is_booked=False)
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.user = request.user
            booking.time_slot = time_slot
            booking.status = 'pending'
            booking.save()
            time_slot.current_bookings += 1
            if time_slot.current_bookings >= time_slot.max_bookings:
                time_slot.is_booked = True
            time_slot.save()
            messages.success(request, 'Navbat muvaffaqiyatli band qilindi!')
            return redirect('booking:user_bookings')
    else:
        form = BookingForm()
    return render(request, 'booking_form.html', {'form': form, 'time_slot': time_slot})

@login_required
def user_bookings(request):
    bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'user_bookings.html', {'bookings': bookings})

@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    if request.method == 'POST':
        booking.status = 'cancelled'
        booking.cancellation_reason = request.POST.get('cancellation_reason', '')
        booking.save()
        time_slot = booking.time_slot
        time_slot.current_bookings -= 1
        time_slot.is_booked = False
        time_slot.save()
        messages.success(request, 'Navbat bekor qilindi!')
        return redirect('booking:user_bookings')
    return render(request, 'cancel_booking.html', {'booking': booking})

@login_required
def admin_dashboard(request):
    if not request.user.managed_organizations.exists():
        messages.error(request, 'Sizda boshqariladigan tashkilot yo‘q.')
        return redirect('booking:home')
    organizations = request.user.managed_organizations.all()
    return render(request, 'admin_dashboard.html', {'organizations': organizations})

@login_required
def add_time_slot(request):
    if not request.user.managed_organizations.exists():
        messages.error(request, 'Sizda boshqariladigan tashkilot yo‘q.')
        return redirect('booking:home')
    if request.method == 'POST':
        form = TimeSlotForm(request.POST)
        if form.is_valid():
            time_slot = form.save(commit=False)
            time_slot.organization = request.user.managed_organizations.first()
            time_slot.save()
            messages.success(request, 'Vaqt sloti qo‘shildi!')
            return redirect('booking:admin_dashboard')
    else:
        form = TimeSlotForm()
    return render(request, 'add_time_slot.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Tizimga kirdingiz!')
            return redirect('booking:home')
        else:
            messages.error(request, 'Noto‘g‘ri login yoki parol.')
    return render(request, 'login.html')

def user_register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(
                user=user,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                phone_number=form.cleaned_data['phone_number'],
            )
            login(request, user)
            messages.success(request, 'Ro‘yxatdan o‘tdingiz!')
            return redirect('booking:home')
    else:
        form = UserRegisterForm()
    return render(request, 'register.html', {'form': form})

def user_logout(request):
    logout(request)
    messages.success(request, 'Tizimdan chiqdingiz.')
    return redirect('booking:home')