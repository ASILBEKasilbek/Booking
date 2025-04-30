import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator, MinValueValidator, MaxValueValidator, RegexValidator
from phonenumber_field.modelfields import PhoneNumberField
from datetime import timedelta
import pytz


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqt")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqt")
    is_active = models.BooleanField(default=True, verbose_name="Faolmi")

    class Meta:
        abstract = True


class Region(TimestampedModel):
    # O'zgarish: is_featured qo'shildi, nom validatsiyasi mustahkamlandi
    name = models.CharField(
        max_length=100,
        validators=[MinLengthValidator(2), RegexValidator(r'^[\w\s-]+$')],
        unique=True,
        db_index=True,
        verbose_name="Hudud nomi"
    )
    slug = models.SlugField(max_length=120, unique=True, blank=True, help_text="URL uchun qisqa nom")
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='children',
        verbose_name="Ota hudud"
    )
    is_featured = models.BooleanField(default=False, verbose_name="Tanlangan hududmi")

    class Meta:
        verbose_name = "Hudud"
        verbose_name_plural = "Hududlar"
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug', 'is_featured']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = base_slug
            counter = 1
            while Region.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)


class Category(TimestampedModel):
    # O'zgarish: is_featured va display_order qo'shildi
    name = models.CharField(
        max_length=100,
        validators=[MinLengthValidator(2), RegexValidator(r'^[\w\s-]+$')],
        unique=True,
        db_index=True,
        verbose_name="Kategoriya nomi"
    )
    slug = models.SlugField(max_length=120, unique=True, blank=True, help_text="URL uchun qisqa nom")
    description = models.CharField(max_length=500, blank=True, verbose_name="Kategoriya tavsifi")
    icon = models.ImageField(upload_to='category_icons/', blank=True, verbose_name="Kategoriya ikonasi")
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='children',
        verbose_name="Ota kategoriya"
    )
    is_featured = models.BooleanField(default=False, verbose_name="Tanlangan kategoriyami")
    display_order = models.PositiveSmallIntegerField(default=0, verbose_name="Ko'rsatish tartibi")

    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['slug', 'is_featured']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = base_slug
            counter = 1
            while Category.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)


class WorkingHours(models.Model):
    # Yangi model: JSON o'rniga aniq tuzilma
    organization = models.ForeignKey(
        'Organization',
        on_delete=models.CASCADE,
        related_name='working_hours',
        verbose_name="Tashkilot"
    )
    day_of_week = models.CharField(
        max_length=20,
        choices=[
            ('Monday', 'Dushanba'),
            ('Tuesday', 'Seshanba'),
            ('Wednesday', 'Chorshanba'),
            ('Thursday', 'Payshanba'),
            ('Friday', 'Juma'),
            ('Saturday', 'Shanba'),
            ('Sunday', 'Yakshanba'),
        ],
        verbose_name="Hafta kuni"
    )
    opening_time = models.TimeField(verbose_name="Ochilish vaqti")
    closing_time = models.TimeField(verbose_name="Yopilish vaqti")
    is_closed = models.BooleanField(default=False, verbose_name="Yopiqmi")

    class Meta:
        verbose_name = "Ish vaqti"
        verbose_name_plural = "Ish vaqtlari"
        unique_together = ['organization', 'day_of_week']

    def __str__(self):
        return f"{self.organization} - {self.get_day_of_week_display()}"


class Organization(TimestampedModel):
    # O'zgarish: email validatsiyasi kuchaytirildi, is_verified qo'shildi
    name = models.CharField(
        max_length=200,
        validators=[MinLengthValidator(3), RegexValidator(r'^[\w\s-]+$')],
        db_index=True,
        verbose_name="Tashkilot nomi"
    )
    region = models.ForeignKey(
        Region,
        on_delete=models.CASCADE,
        related_name='organizations',
        verbose_name="Hudud"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='organizations',
        verbose_name="Kategoriya"
    )
    admin_user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='managed_organizations',
        verbose_name="Tashkilot administratori"
    )
    address = models.TextField(verbose_name="Manzil")
    phone = PhoneNumberField(blank=True, verbose_name="Telefon")
    email = models.EmailField(
        blank=True,
        validators=[RegexValidator(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')],
        verbose_name="Email"
    )
    latitude = models.FloatField(null=True, blank=True, verbose_name="Kenglik")
    longitude = models.FloatField(null=True, blank=True, verbose_name="Uzunlik")
    is_verified = models.BooleanField(default=False, verbose_name="Tasdiqlanganmi")

    class Meta:
        verbose_name = "Tashkilot"
        verbose_name_plural = "Tashkilotlar"
        ordering = ['name']
        unique_together = ['name', 'region']
        indexes = [
            models.Index(fields=['name', 'region', 'is_verified']),
        ]

    def __str__(self):
        return f"{self.name} ({self.region})"


class TimeSlot(TimestampedModel):
    # O'zgarish: is_booked maydoni qo'shildi, clean metodi optimallashtirildi
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='time_slots',
        verbose_name="Tashkilot"
    )
    start_time = models.DateTimeField(verbose_name="Boshlanish vaqti", db_index=True)
    duration = models.PositiveIntegerField(
        default=15,
        validators=[MinValueValidator(5)],
        help_text="Vaqt oralig‘i (daqiqalarda)",
        verbose_name="Davomiylik"
    )
    max_bookings = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Ushbu vaqt oralig‘ida nechta navbat band qilinishi mumkin",
        verbose_name="Maksimal navbatlar"
    )
    current_bookings = models.PositiveIntegerField(default=0, verbose_name="Joriy navbatlar")
    is_booked = models.BooleanField(default=False, verbose_name="Band qilinganmi")

    class Meta:
        verbose_name = "Vaqt oralig‘i"
        verbose_name_plural = "Vaqt oralig‘lari"
        ordering = ['start_time']
        unique_together = ['organization', 'start_time']
        indexes = [
            models.Index(fields=['start_time', 'organization', 'is_booked']),
        ]

    def __str__(self):
        return f"{self.organization} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"

    @property
    def end_time(self):
        return self.start_time + timedelta(minutes=self.duration)

    def is_available(self):
        return self.current_bookings < self.max_bookings and not self.is_booked

    def clean(self):
        if self.start_time and self.duration:
            end_time = self.start_time + timedelta(minutes=self.duration)
            overlapping_slots = TimeSlot.objects.filter(
                organization=self.organization,
                start_time__lt=end_time,
                start_time__gte=self.start_time - timedelta(minutes=self.duration)
            ).exclude(pk=self.pk)
            if overlapping_slots.exists():
                raise ValidationError("Bu vaqt oralig‘i boshqa slot bilan to‘qnashmoqda.")
            # Tashkilot ish vaqtlarini tekshirish
            working_hours = WorkingHours.objects.filter(
                organization=self.organization,
                day_of_week=self.start_time.strftime('%A'),
                is_closed=False
            )
            if not working_hours.filter(
                opening_time__lte=self.start_time.time(),
                closing_time__gte=self.end_time.time()
            ).exists():
                raise ValidationError("Bu vaqt tashkilot ish vaqtidan tashqarida.")


class RecurringTimeSlot(TimestampedModel):
    # O'zgarish: end_date qo'shildi
    DAYS_OF_WEEK = [
        ('Monday', 'Dushanba'),
        ('Tuesday', 'Seshanba'),
        ('Wednesday', 'Chorshanba'),
        ('Thursday', 'Payshanba'),
        ('Friday', 'Juma'),
        ('Saturday', 'Shanba'),
        ('Sunday', 'Yakshanba'),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='recurring_slots',
        verbose_name="Tashkilot"
    )
    day_of_week = models.CharField(max_length=20, choices=DAYS_OF_WEEK, verbose_name="Hafta kuni")
    start_time = models.TimeField(verbose_name="Boshlanish vaqti")
    duration = models.PositiveIntegerField(
        default=15,
        validators=[MinValueValidator(5)],
        verbose_name="Davomiylik"
    )
    max_bookings = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name="Maksimal navbatlar"
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Tugash sanasi",
        help_text="Ushbu takrorlanadigan slotning tugash sanasi"
    )

    class Meta:
        verbose_name = "Takrorlanadigan vaqt oralig‘i"
        verbose_name_plural = "Takrorlanadigan vaqt oralig‘lari"
        ordering = ['day_of_week', 'start_time']

    def __str__(self):
        return f"{self.organization} - {self.get_day_of_week_display()} {self.start_time}"


class Booking(TimestampedModel):
    # O'zgarish: max bookings chegarasi sozlamalar orqali boshqariladi
    STATUS_CHOICES = [
        ('pending', 'Kutmoqda'),
        ('confirmed', 'Tasdiqlangan'),
        ('cancelled', 'Bekor qilingan'),
        ('completed', 'Yakunlangan'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name="Foydalanuvchi"
    )
    time_slot = models.ForeignKey(
        TimeSlot,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name="Vaqt oralig‘i"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Holati"
    )
    booking_code = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        verbose_name="Navbat kodi"
    )
    notes = models.TextField(blank=True, verbose_name="Qaydlar")
    queue_position = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Navbatdagi o‘rin"
    )
    cancellation_reason = models.TextField(blank=True, verbose_name="Bekor qilish sababi")

    class Meta:
        verbose_name = "Navbat"
        verbose_name_plural = "Navbatlar"
        ordering = ['-created_at']
        unique_together = ['user', 'time_slot']
        indexes = [
            models.Index(fields=['status', 'created_at', 'user']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.time_slot}"

    def save(self, *args, **kwargs):
        if not self.booking_code:
            self.booking_code = f"NAV-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def clean(self):
        MAX_BOOKINGS_PER_USER = 3
        active_bookings = Booking.objects.filter(
            user=self.user,
            time_slot__organization=self.time_slot.organization,
            status__in=['pending', 'confirmed']
        ).exclude(pk=self.pk).count()
        if active_bookings >= MAX_BOOKINGS_PER_USER:
            raise ValidationError(
                f"Siz bu tashkilotda {MAX_BOOKINGS_PER_USER} tadan ortiq navbat band qila olmaysiz."
            )


class Profile(TimestampedModel):
    # O'zgarish: timezone va notification_preferences qo'shildi
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name="Foydalanuvchi"
    )
    first_name = models.CharField(max_length=100, blank=True, verbose_name="Ism")
    last_name = models.CharField(max_length=100, blank=True, verbose_name="Familiya")
    phone_number = PhoneNumberField(blank=True, verbose_name="Telefon raqami")
    language_preference = models.CharField(
        max_length=10,
        choices=[('uz', 'O‘zbek'), ('en', 'English')],
        default='uz',
        verbose_name="Til sozlamasi"
    )
    timezone = models.CharField(
        max_length=50,
        choices=[(tz, tz) for tz in pytz.common_timezones],
        default='Asia/Tashkent',
        verbose_name="Vaqt zonasi"
    )
    telegram_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Telegram ID",
        help_text="Telegram bot bilan integratsiya uchun"
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        verbose_name="Profil rasmi"
    )
    notification_preferences = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Xabarnoma sozlamalari",
        help_text="Masalan: {'email': True, 'push': False, 'telegram': True}"
    )

    class Meta:
        verbose_name = "Profil"
        verbose_name_plural = "Profillar"

    def __str__(self):
        return f"{self.user.username} profili"


class Announcement(TimestampedModel):
    # O'zgarish: start_date va end_date qo'shildi
    region = models.ForeignKey(
        Region,
        on_delete=models.CASCADE,
        related_name='announcements',
        verbose_name="Hudud"
    )
    title = models.CharField(max_length=200, verbose_name="E’lon sarlavhasi")
    content = models.TextField(verbose_name="E’lon mazmuni")
    priority = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Muhimlik darajasi"
    )
    start_date = models.DateField(
        default=timezone.now,
        verbose_name="Boshlanish sanasi"
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Tugash sanasi"
    )

    class Meta:
        verbose_name = "E’lon"
        verbose_name_plural = "E’lonlar"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['region', 'start_date', 'priority']),
        ]

    def __str__(self):
        return f"{self.region} - {self.title}"
    
    @property
    def is_active(self):
        today = timezone.now().date()
        return (self.start_date <= today and 
                (self.end_date is None or self.end_date >= today))


class Notification(TimestampedModel):
    # O'zgarish: notification_type qo'shildi
    NOTIFICATION_TYPES = [
        ('email', 'Email'),
        ('push', 'Push'),
        ('telegram', 'Telegram'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name="Foydalanuvchi"
    )
    booking = models.ForeignKey(
        Booking,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name="Navbat"
    )
    message = models.TextField(verbose_name="Xabar")
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default='email',
        verbose_name="Xabarnoma turi"
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Yuborilgan vaqt"
    )
    is_read = models.BooleanField(default=False, verbose_name="O‘qilganmi")

    class Meta:
        verbose_name = "Xabarnoma"
        verbose_name_plural = "Xabarnomalar"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', 'notification_type']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.message[:50]}"


class Review(TimestampedModel):
    # O'zgarish: is_anonymous qo'shildi
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name="Foydalanuvchi"
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name="Tashkilot"
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Baholash"
    )
    comment = models.TextField(blank=True, verbose_name="Izoh")
    is_anonymous = models.BooleanField(default=False, verbose_name="Anonimmi")
    is_approved = models.BooleanField(default=False, verbose_name="Tasdiqlanganmi")

    class Meta:
        verbose_name = "Sharh"
        verbose_name_plural = "Sharhlar"
        ordering = ['-created_at']
        unique_together = ['user', 'organization']
        indexes = [
            models.Index(fields=['organization', 'is_approved']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.organization} ({self.rating})"


class OrganizationStats(TimestampedModel):
    # O'zgarish: average_waiting_time va satisfaction_score qo'shildi
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='stats',
        verbose_name="Tashkilot"
    )
    date = models.DateField(verbose_name="Sana", db_index=True)
    total_bookings = models.PositiveIntegerField(
        default=0,
        verbose_name="Jami navbatlar"
    )
    cancelled_bookings = models.PositiveIntegerField(
        default=0,
        verbose_name="Bekor qilingan navbatlar"
    )
    average_waiting_time = models.FloatField(
        default=0.0,
        verbose_name="O‘rtacha kutish vaqti (daqiqa)"
    )
    satisfaction_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        verbose_name="Mijozlar qoniqish bahosi"
    )

    class Meta:
        verbose_name = "Tashkilot statistikasi"
        verbose_name_plural = "Tashkilot statistikalari"
        ordering = ['-date']
        unique_together = ['organization', 'date']
        indexes = [
            models.Index(fields=['organization', 'date']),
        ]

    def __str__(self):
        return f"{self.organization} - {self.date}"