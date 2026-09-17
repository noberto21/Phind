import csv
import json
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Q
from django.utils import timezone
from .models import TrackingRecord
from .forms import IMEITrackingForm, PhoneLocatorForm
from .services import validate_imei, simulate_device_tracking, locate_phone_number, reverse_geocode_coordinates


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def dashboard_view(request):
    records = TrackingRecord.objects.all()
    total_count = records.count()
    android_count = records.filter(target_type='android_imei').count()
    iphone_count = records.filter(target_type='iphone_appleid').count()
    phone_count = records.filter(target_type='phone_number').count()
    recent_records = records[:8]

    context = {
        'total_count': total_count,
        'android_count': android_count,
        'iphone_count': iphone_count,
        'phone_count': phone_count,
        'recent_records': recent_records,
    }
    return render(request, 'tracker/dashboard.html', context)


def imei_tracker_view(request):
    form = IMEITrackingForm()
    return render(request, 'tracker/imei.html', {'form': form})


def phone_tracker_view(request):
    form = PhoneLocatorForm()
    return render(request, 'tracker/phone.html', {'form': form})


def history_view(request):
    query = request.GET.get('q', '').strip()
    type_filter = request.GET.get('type', '').strip()

    records = TrackingRecord.objects.all()
    if query:
        records = records.filter(
            Q(query_identifier__icontains=query) |
            Q(location_name__icontains=query) |
            Q(carrier_or_brand__icontains=query) |
            Q(device_model__icontains=query)
        )
    if type_filter:
        records = records.filter(target_type=type_filter)

    return render(request, 'tracker/history.html', {
        'records': records,
        'query': query,
        'type_filter': type_filter,
    })


@csrf_exempt
def api_track_imei(request):
    if request.method not in ['POST', 'GET']:
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    params = request.POST if request.method == 'POST' else request.GET
    device_type = params.get('device_type', 'android').lower()
    imei = params.get('imei', '').strip()
    apple_id = params.get('apple_id', '').strip()
    account_email = params.get('account_email', '').strip()

    if device_type == 'android':
        if not imei:
            return JsonResponse({'success': False, 'error': 'Please provide a 15-digit IMEI number.'}, status=400)
        is_valid, clean_imei, msg = validate_imei(imei)
        if not is_valid:
            return JsonResponse({'success': False, 'error': msg}, status=400)
        identifier = clean_imei
        record_type = 'android_imei'
    elif device_type == 'iphone':
        if not apple_id:
            return JsonResponse({'success': False, 'error': 'Please provide an Apple ID / iCloud email.'}, status=400)
        identifier = apple_id
        record_type = 'iphone_appleid'
    else:
        return JsonResponse({'success': False, 'error': 'Invalid device type specified.'}, status=400)

    result = simulate_device_tracking(device_type, identifier, account_email)

    # Persist record in database
    ip = get_client_ip(request)
    beacon_token_str = ""
    beacon_url = ""
    try:
        record = TrackingRecord.objects.create(
            target_type=record_type,
            query_identifier=identifier,
            carrier_or_brand=f"{result['brand']} ({result['carrier']})",
            device_model=result['model'],
            latitude=result['latitude'],
            longitude=result['longitude'],
            location_name=result['location_name'],
            status='Located (Cellular/TAC)',
            accuracy_meters=result['accuracy_meters'],
            ip_address=ip,
            notes=f"Tracked via interactive console. Account: {account_email or 'Anonymous'}"
        )
        beacon_token_str = str(record.beacon_token)
        beacon_url = request.build_absolute_uri(f"/beacon/{beacon_token_str}/")
    except Exception as e:
        print(f"Warning: could not save record: {e}")

    result['record_id'] = record.id if 'record' in locals() else None
    result['beacon_token'] = beacon_token_str
    result['beacon_url'] = beacon_url
    return JsonResponse(result)


@csrf_exempt
def api_sync_device_gps(request):
    """
    Direct Hardware GPS synchronization from browser/device sensors.
    Provides meter-level accuracy (e.g. 3-10m) using HTML5 Geolocation API.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8')) if request.content_type == 'application/json' else request.POST
        lat = float(data.get('latitude'))
        lng = float(data.get('longitude'))
        accuracy = float(data.get('accuracy', 5.0))
        altitude = float(data.get('altitude')) if data.get('altitude') is not None else None
        heading = float(data.get('heading')) if data.get('heading') is not None else None
        speed = float(data.get('speed')) if data.get('speed') is not None else None
        device_name = data.get('device_name', 'Live Hardware GPS Device')
        identifier = data.get('identifier', 'Current-Device-Sensor')
    except (ValueError, TypeError, KeyError) as e:
        return JsonResponse({'success': False, 'error': f'Invalid coordinate parameters: {str(e)}'}, status=400)

    # High-precision reverse geocoding to exact street
    detailed_address = reverse_geocode_coordinates(lat, lng)

    # Save high-accuracy tracking record
    ip = get_client_ip(request)
    record = TrackingRecord.objects.create(
        target_type='android_imei',
        query_identifier=identifier,
        carrier_or_brand='Hardware GNSS / Wi-Fi Grid',
        device_model=device_name,
        latitude=round(lat, 6),
        longitude=round(lng, 6),
        altitude=round(altitude, 2) if altitude is not None else None,
        heading=round(heading, 1) if heading is not None else None,
        speed=round(speed, 2) if speed is not None else None,
        location_name=detailed_address,
        status=f'High Accuracy GPS (±{int(round(accuracy))}m)',
        accuracy_meters=int(round(accuracy)),
        is_live_gps=True,
        last_ping=timezone.now(),
        ip_address=ip,
        notes=f"Synced directly with device GPS sensor. Precision: ±{accuracy:.1f}m."
    )

    google_find_my_url = f"https://www.google.com/android/find?u=0&hl=en&source=android-browser&q={lat},{lng}"
    google_maps_url = f"https://www.google.com/maps?q={lat},{lng}"
    apple_find_my_url = f"https://www.icloud.com/find?q={lat},{lng}"

    return JsonResponse({
        'success': True,
        'record_id': record.id,
        'beacon_token': str(record.beacon_token),
        'latitude': round(lat, 6),
        'longitude': round(lng, 6),
        'accuracy_meters': int(round(accuracy)),
        'location_name': detailed_address,
        'status': f'Locked (±{int(round(accuracy))}m precision)',
        'google_find_my_url': google_find_my_url,
        'google_maps_url': google_maps_url,
        'apple_find_my_url': apple_find_my_url
    })


def beacon_ping_view(request, token):
    """
    Mobile-optimized landing page sent to lost device.
    Prompts target device to authorize GPS and streams exact coordinates back to the tracker.
    """
    record = get_object_or_404(TrackingRecord, beacon_token=token)
    return render(request, 'tracker/beacon_ping.html', {
        'token': str(token),
        'record': record
    })


@csrf_exempt
def api_beacon_report(request, token):
    """
    Receives high-accuracy GPS coordinates reported by target device via beacon link.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    record = get_object_or_404(TrackingRecord, beacon_token=token)

    try:
        data = json.loads(request.body.decode('utf-8')) if request.content_type == 'application/json' else request.POST
        lat = float(data.get('latitude'))
        lng = float(data.get('longitude'))
        accuracy = float(data.get('accuracy', 8.0))
        altitude = float(data.get('altitude')) if data.get('altitude') is not None else None
    except (ValueError, TypeError, KeyError) as e:
        return JsonResponse({'success': False, 'error': f'Invalid data: {str(e)}'}, status=400)

    # Detailed address
    detailed_address = reverse_geocode_coordinates(lat, lng)

    record.latitude = round(lat, 6)
    record.longitude = round(lng, 6)
    record.altitude = round(altitude, 2) if altitude is not None else None
    record.accuracy_meters = int(round(accuracy))
    record.location_name = detailed_address
    record.status = f'Beacon GPS Locked (±{int(round(accuracy))}m)'
    record.is_live_gps = True
    record.last_ping = timezone.now()
    record.notes += f"\n[Ping {timezone.now().strftime('%H:%M:%S')}] Coordinates reported by target device."
    record.save()

    return JsonResponse({
        'success': True,
        'message': 'Location telemetry successfully synchronized with tracker dashboard.'
    })


def api_beacon_status(request, token):
    """
    Polled by tracker dashboard to check if target device has reported its location.
    """
    record = get_object_or_404(TrackingRecord, beacon_token=token)
    return JsonResponse({
        'success': True,
        'is_live_gps': record.is_live_gps,
        'status': record.status,
        'latitude': record.latitude,
        'longitude': record.longitude,
        'accuracy_meters': record.accuracy_meters,
        'location_name': record.location_name,
        'last_ping': record.last_ping.isoformat() if record.last_ping else None
    })


@csrf_exempt
def api_track_phone(request):
    if request.method not in ['POST', 'GET']:
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    params = request.POST if request.method == 'POST' else request.GET
    phone_number = params.get('phone_number', '').strip()
    user_location = params.get('user_location', '').strip()

    if not phone_number:
        return JsonResponse({'success': False, 'error': 'Please enter a phone number in international format.'}, status=400)

    result = locate_phone_number(phone_number, user_location)
    if not result.get('success'):
        return JsonResponse(result, status=400)

    # Persist record in database
    ip = get_client_ip(request)
    try:
        TrackingRecord.objects.create(
            target_type='phone_number',
            query_identifier=result['formatted_number'],
            carrier_or_brand=result['carrier'],
            device_model='Cellular Subscriber',
            latitude=result['target_lat'],
            longitude=result['target_lng'],
            location_name=result['resolved_address'],
            status='Located',
            accuracy_meters=500,
            distance_km=result.get('distance_km'),
            ip_address=ip,
            notes=f"Carrier: {result['carrier']}, Timezones: {', '.join(result.get('timezones', []))}"
        )
    except Exception as e:
        print(f"Warning: could not save record: {e}")

    return JsonResponse(result)


def api_delete_record(request, record_id):
    if request.method in ['POST', 'DELETE']:
        record = get_object_or_404(TrackingRecord, id=record_id)
        record.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Record deleted successfully.'})
    return redirect('history')


def api_clear_history(request):
    if request.method == 'POST':
        TrackingRecord.objects.all().delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'All tracking records cleared.'})
    return redirect('history')


def export_history_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="tracking_history.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Type', 'Identifier', 'Carrier/Brand', 'Model', 'Latitude', 'Longitude', 'Location Name', 'Accuracy (m)', 'Live GPS', 'Distance (km)', 'Timestamp'])

    for rec in TrackingRecord.objects.all():
        writer.writerow([
            rec.id,
            rec.get_target_type_display(),
            rec.query_identifier,
            rec.carrier_or_brand,
            rec.device_model,
            rec.latitude,
            rec.longitude,
            rec.location_name,
            rec.accuracy_meters,
            'Yes' if rec.is_live_gps else 'No',
            rec.distance_km or '',
            rec.created_at.strftime("%Y-%m-%d %H:%M:%S")
        ])

    return response


def export_history_json(request):
    records = []
    for rec in TrackingRecord.objects.all():
        records.append({
            'id': rec.id,
            'target_type': rec.target_type,
            'type_display': rec.get_target_type_display(),
            'query_identifier': rec.query_identifier,
            'carrier_or_brand': rec.carrier_or_brand,
            'device_model': rec.device_model,
            'latitude': rec.latitude,
            'longitude': rec.longitude,
            'location_name': rec.location_name,
            'accuracy_meters': rec.accuracy_meters,
            'is_live_gps': rec.is_live_gps,
            'distance_km': rec.distance_km,
            'timestamp': rec.created_at.isoformat()
        })
    return JsonResponse(records, safe=False, json_dumps_params={'indent': 2})
