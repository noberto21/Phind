from django.contrib import admin
from .models import TrackingRecord


@admin.register(TrackingRecord)
class TrackingRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'target_type', 'query_identifier', 'carrier_or_brand', 'location_name', 'latitude', 'longitude', 'status', 'created_at')
    list_filter = ('target_type', 'status', 'created_at')
    search_fields = ('query_identifier', 'location_name', 'carrier_or_brand', 'device_model')
    readonly_fields = ('created_at',)
