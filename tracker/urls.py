from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('imei/', views.imei_tracker_view, name='imei_tracker'),
    path('phone/', views.phone_tracker_view, name='phone_tracker'),
    path('history/', views.history_view, name='history'),
    
    # High-Accuracy Find My Device & GPS Sync APIs
    path('api/sync-device-gps/', views.api_sync_device_gps, name='api_sync_device_gps'),
    path('beacon/<uuid:token>/', views.beacon_ping_view, name='beacon_ping'),
    path('api/beacon-report/<uuid:token>/', views.api_beacon_report, name='api_beacon_report'),
    path('api/beacon-status/<uuid:token>/', views.api_beacon_status, name='api_beacon_status'),

    # Device & Phone Tracking APIs
    path('api/track-imei/', views.api_track_imei, name='api_track_imei'),
    path('api/track-phone/', views.api_track_phone, name='api_track_phone'),
    path('api/delete/<int:record_id>/', views.api_delete_record, name='api_delete_record'),
    path('api/clear-history/', views.api_clear_history, name='api_clear_history'),
    path('history/export/csv/', views.export_history_csv, name='export_csv'),
    path('history/export/json/', views.export_history_json, name='export_json'),
]
