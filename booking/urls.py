from django.urls import path
from . import views

app_name = 'booking'

urlpatterns = [
    path('', views.home, name='home'),
    path('organizations/', views.organization_list, name='organization_list'),
    path('organization/<slug:slug>/', views.organization_detail, name='organization_detail'),
    path('book/<int:slot_id>/', views.book_slot, name='book_slot'),
    path('my-bookings/', views.user_bookings, name='user_bookings'),
    path('cancel-booking/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/add-slot/', views.add_time_slot, name='add_time_slot'),
    path('login/', views.user_login, name='login'),
    path('register/', views.user_register, name='register'),
    path('logout/', views.user_logout, name='logout'),
]