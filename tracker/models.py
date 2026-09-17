import uuid
from django.db import models


class TrackingRecord(models.Model):
    DEVICE_TYPES = [
        ('android_imei', 'Android (IMEI)'),
        ('iphone_appleid', 'iPhone (Apple ID)'),
        ('phone_number', 'Phone Number'),
    ]

    target_type = models.CharField(max_length=30, choices=DEVICE_TYPES, default='android_imei')
    query_identifier = models.CharField(max_length=100, verbose_name="Target Identifier (IMEI/Phone/AppleID)")
    carrier_or_brand = models.CharField(max_length=100, blank=True, default='')
    device_model = models.CharField(max_length=100, blank=True, default='')
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    location_name = models.CharField(max_length=255, blank=True, default='')
    status = models.CharField(max_length=50, default='Located')
    accuracy_meters = models.IntegerField(default=15)
    distance_km = models.FloatField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # High-Accuracy Find My Device & Beacon Fields
    beacon_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    is_live_gps = models.BooleanField(default=False, verbose_name="Verified Hardware GPS")
    altitude = models.FloatField(null=True, blank=True)
    heading = models.FloatField(null=True, blank=True)
    speed = models.FloatField(null=True, blank=True)
    last_ping = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Tracking Record'
        verbose_name_plural = 'Tracking Records'

    def __str__(self):
        gps_tag = " [GPS ±5m]" if self.is_live_gps else ""
        return f"{self.get_target_type_display()}: {self.query_identifier} ({self.status}){gps_tag}"
