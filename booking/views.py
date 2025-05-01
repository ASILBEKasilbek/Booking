from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import (
    Organization, TimeSlot, Booking, Region, Category, WorkingHours,
    RecurringTimeSlot, Notification, Profile, Announcement, Review, OrganizationStats
)
from .forms import UserRegisterForm, BookingForm, TimeSlotForm
import pytz


def home(request):
    regions = Region.objects.filter(is_active=True, is_featured=True)[:6]
    categories = Category.objects.filter(is_active=True, is_featured=True)[:6]
    announcements = Announcement.objects.filter(
        is_active=True,
        start_date__lte=timezone.now().date(),
        end_date__gte=timezone.now().date()
    ).order_by('-priority', '-created_at')[:3]
    return render(request, 'home.html', {
        'regions': regions,
        'categories': categories,
        'announcements': announcements,
    })


def organization_list(request):
    organizations = Organization.objects.filter(is_active=True, is_verified=True).select_related('region', 'category')
    
    region_id = request.GET.get('region')
    category_id = request.GET.get('category')
    search_query = request.GET.get('q')
    
    if region_id:
        organizations = organizations.filter(region_id=region_id)
    if category_id:
        organizations = organizations.filter(category_id=category_id)
    if search_query:
        organizations = organizations.filter(
            Q(name__icontains=search_query) | 
            Q(address__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    
    paginator = Paginator(organizations, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    regions = Region.objects.filter(is_active=True)
    categories = Category.objects.filter(is_active=True)
    return render(request, 'organization_list.html', {
        'page_obj': page_obj,
        'regions': regions,
        'categories': categories,
        'search_query': search_query,
    })


def organization_detail(request, slug):
    organization = get_object_or_404(Organization, slug=slug, is_active=True, is_verified=True)
    time_slots = TimeSlot.objects.filter(
        organization=organization,
        start_time__gte=timezone.now(),
        is_booked=False
    ).select_related('organization').order_by('start_time')
    
    working_hours = WorkingHours.objects.filter(organization=organization).order_by('day_of_week')
    reviews = Review.objects.filter(organization=organization, is_approved=True).select_related('user')[:5]
    
    return render(request, 'organization_detail.html', {
        'organization': organization,
        'time_slots': time_slots,
        'working_hours': working_hours,
        'reviews': reviews,
    })


@login_required
def book_slot(request, slot_id):
    time_slot = get_object_or_404(TimeSlot, id=slot_id, is_booked=False)
    
    working_hours = WorkingHours.objects.filter(
        organization=time_slot.organization,
        day_of_week=time_slot.start_time.strftime('%A'),
        is_closed=False,
        opening_time__lte=time_slot.start_time.time(),
        closing_time__gte=time_slot.end_time.time()
    )
    if not working_hours.exists():
        messages.error(request, 'Bu vaqt tashkilot ish vaqtidan tashqarida.')
        return redirect('booking:organization_detail', slug=time_slot.organization.slug)
    
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            active_bookings = Booking.objects.filter(
                user=request.user,
                time_slot__organization=time_slot.organization,
                status__in=['pending', 'confirmed']
            ).count()
            if active_bookings >= 3:
                messages.error(request, 'Siz bu tashkilotda 3 tadan ortiq navbat band qila olmaysiz.')
                return redirect('booking:organization_detail', slug=time_slot.organization.slug)
            
            try:
                booking = form.save(commit=False)
                booking.user = request.user
                booking.time_slot = time_slot
                booking.status = 'pending'
                booking.clean()
                booking.save()
                
                time_slot.current_bookings += 1
                if time_slot.current_bookings >= time_slot.max_bookings:
                    time_slot.is_booked = True
                time_slot.save()
                
                Notification.objects.create(
                    user=request.user,
                    booking=booking,
                    message=f"{time_slot.organization.name} da {time_slot.start_time.strftime('%Y-%m-%d %H:%M')} vaqtiga navbat band qilindi.",
                    notification_type='email'
                )
                
                today = timezone.now().date()
                stats, created = OrganizationStats.objects.get_or_create(
                    organization=time_slot.organization,
                    date=today,
                    defaults={'total_bookings': 1}
                )
                if not created:
                    stats.total_bookings += 1
                    stats.save()
                
                messages.success(request, 'Navbat muvaffaqiyatli band qilindi!')
                return redirect('booking:user_bookings')
            except ValidationError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'Forma xatolarni o‘z ichiga oladi.')
    else:
        form = BookingForm()
    return render(request, 'booking_form.html', {'form': form, 'time_slot': time_slot})


@login_required
def user_bookings(request):
    bookings = Booking.objects.filter(user=request.user).select_related('time_slot__organization').order_by('-created_at')
    paginator = Paginator(bookings, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'user_bookings.html', {'page_obj': page_obj})


@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    if booking.status not in ['pending', 'confirmed']:
        messages.error(request, 'Bu navbatni bekor qilib bo‘lmaydi.')
        return redirect('booking:user_bookings')
    
    if request.method == 'POST':
        booking.status = 'cancelled'
        booking.cancellation_reason = request.POST.get('cancellation_reason', '')
        booking.save()
        
        time_slot = booking.time_slot
        time_slot.current_bookings = max(0, time_slot.current_bookings - 1)
        time_slot.is_booked = time_slot.current_bookings >= time_slot.max_bookings
        time_slot.save()
        
        Notification.objects.create(
            user=request.user,
            booking=booking,
            message=f"{time_slot.organization.name} da {time_slot.start_time.strftime('%Y-%m-%d %H:%M')} vaqtiga navbat bekor qilindi.",
            notification_type='email'
        )
        
        today = timezone.now().date()
        stats, created = OrganizationStats.objects.get_or_create(
            organization=time_slot.organization,
            date=today,
            defaults={'cancelled_bookings': 1}
        )
        if not created:
            stats.cancelled_bookings += 1
            stats.save()
        
        messages.success(request, 'Navbat bekor qilindi!')
        return redirect('booking:user_bookings')
    return render(request, 'cancel_booking.html', {'booking': booking})


@login_required
def admin_dashboard(request):
    if not request.user.is_authenticated or not request.user.managed_organizations.exists():
        messages.error(request, 'Sizda boshqariladigan tashkilot yo‘q.')
        return redirect('booking:home')
    
    organizations = request.user.managed_organizations.select_related('region', 'category')
    bookings = Booking.objects.filter(
        time_slot__organization__in=organizations
    ).select_related('time_slot__organization', 'user').order_by('-created_at')[:10]
    
    today = timezone.now().date()
    stats = OrganizationStats.objects.filter(
        organization__in=organizations,
        date__gte=today - timedelta(days=30)
    ).select_related('organization').order_by('-date')
    
    return render(request, 'admin_dashboard.html', {
        'organizations': organizations,
        'bookings': bookings,
        'stats': stats,
    })

@login_required
def add_time_slot(request):
    if not request.user.is_authenticated or not request.user.managed_organizations.exists():
        messages.error(request, 'Sizda boshqariladigan tashkilot yo‘q.')
        return redirect('booking:home')
    
    organization = request.user.managed_organizations.first()
    if request.method == 'POST':
        form = TimeSlotForm(request.POST)
        if form.is_valid():
            time_slot = form.save(commit=False)
            time_slot.organization = organization
            try:
                time_slot.clean()
                time_slot.save()
                messages.success(request, 'Vaqt sloti qo‘shildi!')
                return redirect('booking:admin_dashboard')
            except ValidationError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'Forma xatolarni o‘z ichiga oladi.')
    else:
        form = TimeSlotForm()
    return render(request, 'add_time_slot.html', {'form': form, 'organization': organization})

@login_required
def generate_recurring_slots(request):
    if not request.user.is_authenticated or not request.user.managed_organizations.exists():
        messages.error(request, 'Sizda boshqariladigan tashkilot yo‘q.')
        return redirect('booking:home')
    
    organization = request.user.managed_organizations.first()
    recurring_slots = RecurringTimeSlot.objects.filter(organization=organization)
    today = timezone.now().date()
    end_date = today + timedelta(days=30)
    
    for slot in recurring_slots:
        current_date = today
        while current_date <= end_date:
            if current_date.strftime('%A') == slot.day_of_week:
                start_datetime = datetime.combine(current_date, slot.start_time)
                start_datetime = timezone.make_aware(start_datetime, timezone=pytz.timezone('Asia/Tashkent'))
                if slot.end_date and current_date > slot.end_date:
                    continue
                if not TimeSlot.objects.filter(
                    organization=organization,
                    start_time=start_datetime
                ).exists():
                    try:
                        time_slot = TimeSlot(
                            organization=organization,
                            start_time=start_datetime,
                            duration=slot.duration,
                            max_bookings=slot.max_bookings
                        )
                        time_slot.clean()
                        time_slot.save()
                    except ValidationError:
                        continue
            current_date += timedelta(days=1)
    
    messages.success(request, 'Takrorlanadigan vaqt slotlari generatsiya qilindi!')
    return redirect('booking:admin_dashboard')

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
                timezone='Asia/Tashkent',
                notification_preferences={'email': True, 'telegram': False}
            )
            login(request, user)
            messages.success(request, 'Ro‘yxatdan o‘tdingiz!')
            return redirect('booking:home')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = UserRegisterForm()
    return render(request, 'register.html', {'form': form})

def user_logout(request):
    logout(request)
    messages.success(request, 'Tizimdan chiqdingiz.')
    return redirect('booking:home')

@login_required
def user_profile(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        # Agar profil mavjud bo‘lmasa, yangi profil yaratamiz
        profile = Profile.objects.create(
            user=request.user,
            timezone='Asia/Tashkent',
            notification_preferences={'email': True, 'telegram': False}
        )
    
    if request.method == 'POST':
        profile.first_name = request.POST.get('first_name', profile.first_name)
        profile.last_name = request.POST.get('last_name', profile.last_name)
        profile.phone_number = request.POST.get('phone_number', profile.phone_number) or ''
        profile.language_preference = request.POST.get('language_preference', profile.language_preference)
        profile.timezone = request.POST.get('timezone', profile.timezone)
        try:
            profile.clean()
            profile.save()
            messages.success(request, 'Profil yangilandi!')
            return redirect('booking:user_profile')
        except ValidationError as e:
            messages.error(request, str(e))
    return render(request, 'user_profile.html', {'profile': profile})

@login_required
def submit_review(request, organization_id):
    organization = get_object_or_404(Organization, id=organization_id, is_verified=True)
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment', '')
        is_anonymous = request.POST.get('is_anonymous', False) == 'on'
        
        if not rating or int(rating) < 1 or int(rating) > 5:
            messages.error(request, 'Baholash 1 dan 5 gacha bo‘lishi kerak.')
            return redirect('booking:organization_detail', slug=organization.slug)
        
        try:
            Review.objects.create(
                user=request.user,
                organization=organization,
                rating=rating,
                comment=comment,
                is_anonymous=is_anonymous
            )
            messages.success(request, 'Sharh yuborildi! Tasdiqlangach ko‘rinadi.')
            return redirect('booking:organization_detail', slug=organization.slug)
        except ValidationError as e:
            messages.error(request, str(e))
    
    return render(request, 'submit_review.html', {'organization': organization})