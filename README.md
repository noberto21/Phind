# 🛰️ CyberTrack Pro - Interactive IMEI & Device Tracker (Django)

An interactive, full-stack geospatial intelligence and mobile device tracking web application built with **Django 6**, **Leaflet.js**, and modern asynchronous telemetry simulation.

---

## 🌟 Key Features

1. **📱 Interactive IMEI & Device Tracker (Android & iPhone)**
   - Live 15-digit IMEI verification with Luhn algorithm validation.
   - Automatic Type Allocation Code (TAC) and device hardware identifier lookup.
   - Step-by-step real-time terminal emulation interrogating cellular carrier routing networks.
   - Interactive high-precision Leaflet map with animated beacon pins and accuracy circles.
   - One-click links to **Google Find My Device** and **Apple iCloud Find My**.
   - Sample data generator for instantaneous testing.

2. **📞 Interactive Phone Number Locator**
   - International phone number parsing (`phonenumbers`) with automatic country and carrier provider detection.
   - Geocoding using OpenCage Geocode API.
   - Haversine distance calculator between your location and target phone coordinates.
   - Dynamic route map connecting departure to destination with glowing polyline vectors.

3. **📜 Tracking History & Intelligence Export**
   - SQLite database logging all queries, coordinates, carriers, and accuracy metrics.
   - Searchable and filterable history console.
   - Single-record deletion and full log clearing with confirmation.
   - One-click **CSV** and **JSON** data export.

4. **💻 Modern Cyber / Glassmorphism UI**
   - Responsive dark cyberpunk aesthetic powered by Bootstrap 5 and FontAwesome 6.
   - Live UTC system clock and radar scanning widget.
   - Mobile and desktop responsive layouts.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Apply Database Migrations
```bash
python manage.py migrate
```

### 3. Start the Interactive Django Server
```bash
python manage.py runserver
```

Open your browser and navigate to:
👉 **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**

---

## 🧪 Running Automated Tests

```bash
python manage.py test tracker
```

---

## 📁 Project Structure

```
├── manage.py
├── requirements.txt
├── imei_tracker_project/         # Django project configuration
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── tracker/                      # Core tracker app
│   ├── models.py                 # TrackingRecord database model
│   ├── views.py                  # Dashboard, IMEI, Phone, History, and JSON APIs
│   ├── services.py               # Luhn check, TAC lookup, OpenCage & phonenumbers logic
│   ├── forms.py                  # Form validations
│   ├── urls.py                   # App routing
│   ├── admin.py                  # Django admin registration
│   └── tests.py                  # Comprehensive unit & view tests
├── templates/                    # HTML5 templates
│   ├── base.html                 # Main layout with live telemetry header & footer
│   └── tracker/
│       ├── dashboard.html        # Interactive overview hub & radar scanner
│       ├── imei.html             # Real-time IMEI interrogator & map
│       ├── phone.html            # Phone subscriber locator & route polyline
│       └── history.html          # Searchable history table & export
├── static/
│   ├── css/style.css             # Cyberpunk / glassmorphism styles & animations
│   └── js/tracker.js             # Asynchronous AJAX tracking engine & Leaflet controller
├── Track.py                      # Original CLI terminal tool (preserved)
├── CyberTrack.py                 # Original Tkinter GUI tool (preserved)
└── PhoneNumber_Tracker/          # Original phone tracking scripts (preserved)
```

---

## 📄 License
This project is licensed under the MIT License.
