from django.contrib import admin
from .models import (
    Region, Category, Organization, WorkingHours, TimeSlot, RecurringTimeSlot,
    Booking, Profile, Announcement, Notification, Review, OrganizationStats
)


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent', 'is_featured', 'is_active', 'created_at')
    list_filter = ('is_active', 'is_featured', 'parent')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent', 'is_featured', 'display_order', 'is_active')
    list_filter = ('is_active', 'is_featured', 'parent')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('display_order', 'name')


class WorkingHoursInline(admin.TabularInline):
    model = WorkingHours
    extra = 1
    fields = ('day_of_week', 'opening_time', 'closing_time', 'is_closed')


class TimeSlotInline(admin.TabularInline):
    model = TimeSlot
    extra = 1
    fields = ('start_time', 'duration', 'max_bookings', 'current_bookings', 'is_booked')
    readonly_fields = ('current_bookings', 'is_booked')


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'region', 'category', 'is_verified', 'is_active', 'created_at')
    list_filter = ('is_active', 'is_verified', 'region', 'category')
    search_fields = ('name', 'address', 'email', 'phone')
    inlines = [WorkingHoursInline, TimeSlotInline]
    actions = ['mark_as_verified', 'mark_as_unverified']

    def mark_as_verified(self, request, queryset):
        queryset.update(is_verified=True)
    mark_as_verified.short_description = "Tanlangan tashkilotlarni tasdiqlash"

    def mark_as_unverified(self, request, queryset):
        queryset.update(is_verified=False)
    mark_as_unverified.short_description = "Tanlangan tashkilotlarni tasdiqlanmagan qilish"


@admin.register(WorkingHours)
class WorkingHoursAdmin(admin.ModelAdmin):
    list_display = ('organization', 'day_of_week', 'opening_time', 'closing_time', 'is_closed')
    list_filter = ('organization', 'day_of_week', 'is_closed')
    search_fields = ('organization__name',)
    ordering = ('organization', 'day_of_week')


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ('organization', 'start_time', 'end_time', 'duration', 'max_bookings', 'current_bookings', 'is_booked')
    list_filter = ('organization', 'is_booked', 'start_time')
    search_fields = ('organization__name',)
    date_hierarchy = 'start_time'
    ordering = ('start_time',)


@admin.register(RecurringTimeSlot)
class RecurringTimeSlotAdmin(admin.ModelAdmin):
    list_display = ('organization', 'day_of_week', 'start_time', 'duration', 'max_bookings', 'end_date')
    list_filter = ('organization', 'day_of_week')
    search_fields = ('organization__name',)
    ordering = ('organization', 'day_of_week', 'start_time')


class BookingInline(admin.TabularInline):
    model = Booking
    extra = 0
    fields = ('user', 'time_slot', 'status', 'booking_code', 'queue_position')
    readonly_fields = ('booking_code',)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'time_slot', 'status', 'booking_code', 'created_at')
    list_filter = ('status', 'time_slot__organization', 'created_at')
    search_fields = ('user__username', 'booking_code', 'time_slot__organization__name')
    date_hierarchy = 'created_at'
    actions = ['mark_as_confirmed', 'mark_as_cancelled', 'mark_as_completed']

    def mark_as_confirmed(self, request, queryset):
        queryset.update(status='confirmed')
    mark_as_confirmed.short_description = "Tanlangan navbatlarni tasdiqlash"

    def mark_as_cancelled(self, request, queryset):
        queryset.update(status='cancelled')
    mark_as_cancelled.short_description = "Tanlangan navbatlarni bekor qilish"

    def mark_as_completed(self, request, queryset):
        queryset.update(status='completed')
    mark_as_completed.short_description = "Tanlangan navbatlarni yakunlash"


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'first_name', 'last_name', 'phone_number', 'language_preference', 'timezone')
    list_filter = ('language_preference', 'timezone')
    search_fields = ('user__username', 'first_name', 'last_name', 'phone_number', 'telegram_id')

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'region', 'priority', 'start_date', 'end_date', 'is_active')
    list_filter = ('region', 'priority', 'start_date')  # is_active olib tashlandi
    search_fields = ('title', 'content')
    date_hierarchy = 'start_date'
    ordering = ('-created_at',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'notification_type', 'sent_at', 'is_read')
    list_filter = ('notification_type', 'is_read', 'sent_at')
    search_fields = ('user__username', 'message')
    date_hierarchy = 'sent_at'
    ordering = ('-created_at',)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization', 'rating', 'is_anonymous', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'is_anonymous', 'rating', 'organization')
    search_fields = ('user__username', 'organization__name', 'comment')
    actions = ['approve_reviews', 'disapprove_reviews']

    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
    approve_reviews.short_description = "Tanlangan sharhlarni tasdiqlash"

    def disapprove_reviews(self, request, queryset):
        queryset.update(is_approved=False)
    disapprove_reviews.short_description = "Tanlangan sharhlarni tasdiqlanmagan qilish"


@admin.register(OrganizationStats)
class OrganizationStatsAdmin(admin.ModelAdmin):
    list_display = ('organization', 'date', 'total_bookings', 'cancelled_bookings', 'average_waiting_time', 'satisfaction_score')
    list_filter = ('organization', 'date')
    search_fields = ('organization__name',)
    date_hierarchy = 'date'
    ordering = ('-date',)