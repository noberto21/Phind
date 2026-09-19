/**
 * CyberTrack Pro - Interactive Tracking Frontend Engine
 * High-Accuracy Find My Device & Hardware GPS Geolocation
 */

// Global Map instances cache
const CyberTrackMaps = {
    imeiMap: null,
    imeiMarker: null,
    imeiCircle: null,
    lastCoords: null,
    phoneMap: null,
    phoneMarkers: [],
    phoneRoute: null,
    beaconPollingInterval: null
};

// Web Audio API Ring Chime Context
let audioCtx = null;
let isRinging = false;

function playFindMyDeviceSound() {
    try {
        if (!audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioCtx.state === 'suspended') {
            audioCtx.resume();
        }

        const playTone = (freq, startTime, duration) => {
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(freq, startTime);

            gain.gain.setValueAtTime(0.01, startTime);
            gain.gain.exponentialRampToValueAtTime(0.3, startTime + 0.05);
            gain.gain.exponentialRampToValueAtTime(0.001, startTime + duration);

            osc.connect(gain);
            gain.connect(audioCtx.destination);
            osc.start(startTime);
            osc.stop(startTime + duration);
        };

        const now = audioCtx.currentTime;
        // Ascending locator sequence (repeats 3 times)
        for (let loop = 0; loop < 4; loop++) {
            const offset = now + loop * 0.9;
            playTone(880, offset + 0.0, 0.18);
            playTone(1320, offset + 0.22, 0.18);
            playTone(1760, offset + 0.44, 0.35);
        }

        const chimeBtn = document.getElementById('playChimeBtn');
        if (chimeBtn) {
            chimeBtn.classList.remove('btn-outline-warning');
            chimeBtn.classList.add('btn-warning');
            chimeBtn.innerHTML = '<i class="fa-solid fa-volume-high fa-beat me-1"></i> Ringing...';
            setTimeout(() => {
                chimeBtn.classList.remove('btn-warning');
                chimeBtn.classList.add('btn-outline-warning');
                chimeBtn.innerHTML = '<i class="fa-solid fa-bell me-1"></i> Ring Device';
            }, 3600);
        }
    } catch (e) {
        console.warn('Audio synthesis failed:', e);
    }
}

// Utility: get CSRF token from cookie if needed
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Format current time HH:MM:SS
function getCurrentTimeString() {
    const now = new Date();
    return now.toTimeString().split(' ')[0];
}

// Log line to terminal console
function logToTerminal(terminalEl, stage, text, type = 'info') {
    if (!terminalEl) return;
    const timeStr = getCurrentTimeString();
    const line = document.createElement('div');
    line.className = 'terminal-line';
    
    let textClass = 'terminal-text';
    if (type === 'success') textClass = 'terminal-success';
    if (type === 'error') textClass = 'terminal-error';
    if (type === 'warn') textClass = 'terminal-warn';

    line.innerHTML = `
        <span class="terminal-time">[${timeStr}]</span>
        <span class="terminal-stage">&lt;${stage}&gt;</span>
        <span class="${textClass}">${text}</span>
    `;
    terminalEl.appendChild(line);
    terminalEl.scrollTop = terminalEl.scrollHeight;
}

// Initialize Leaflet Map helper
function initLeafletMap(containerId, defaultLat = 0, defaultLng = 0, zoom = 3) {
    const container = document.getElementById(containerId);
    if (!container) return null;

    const map = L.map(containerId, {
        attributionControl: false
    }).setView([defaultLat, defaultLng], zoom);

    // Use OpenStreetMap tiles (no API key required)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        subdomains: 'abc'
    }).addTo(map);

    L.control.attribution({ position: 'bottomright' })
        .addAttribution('&copy; <a href="https://openstreetmap.org">OSM</a>')
        .addTo(map);

    return map;
}

// Plot high-accuracy pin on map
function plotImeiOnMap(lat, lng, label, sublabel, accuracyMeters = 10, isLiveGps = false) {
    const map = CyberTrackMaps.imeiMap;
    if (!map) return;

    CyberTrackMaps.lastCoords = [lat, lng];
    map.invalidateSize();

    const zoomLevel = isLiveGps ? 17 : 14;
    map.flyTo([lat, lng], zoomLevel, { duration: 1.5 });

    if (CyberTrackMaps.imeiMarker) map.removeLayer(CyberTrackMaps.imeiMarker);
    if (CyberTrackMaps.imeiCircle) map.removeLayer(CyberTrackMaps.imeiCircle);

    const pinColor = isLiveGps ? '#10b981' : '#f59e0b';
    const iconHtml = `
        <div style="background-color:${pinColor}; width:22px; height:22px; border-radius:50%; border:3px solid #fff; box-shadow:0 0 18px ${pinColor}; animation: pulse 1.2s infinite;"></div>
    `;
    const customIcon = L.divIcon({
        html: iconHtml,
        className: 'custom-beacon-pin',
        iconSize: [22, 22],
        iconAnchor: [11, 11]
    });

    CyberTrackMaps.imeiMarker = L.marker([lat, lng], { icon: customIcon }).addTo(map);
    CyberTrackMaps.imeiCircle = L.circle([lat, lng], {
        radius: isLiveGps ? Math.max(accuracyMeters, 15) : (accuracyMeters || 1500),
        color: pinColor,
        fillColor: pinColor,
        fillOpacity: isLiveGps ? 0.22 : 0.12,
        weight: isLiveGps ? 2 : 1.5
    }).addTo(map);

    const accuracyBadge = isLiveGps ? 
        `<span class="badge bg-success mt-1"><i class="fa-solid fa-crosshairs me-1"></i> Live Hardware GPS (±${accuracyMeters}m)</span>` :
        `<span class="badge bg-warning text-dark mt-1"><i class="fa-solid fa-tower-cell me-1"></i> Simulated Cellular HLR (±${accuracyMeters}m)</span>`;

    CyberTrackMaps.imeiMarker.bindPopup(`
        <div class="p-1">
            <strong class="text-cyan">${label}</strong><br>
            <span class="fs-8 text-secondary">${sublabel}</span><br>
            ${accuracyBadge}
        </div>
    `).openPopup();

    const highAccBadge = document.getElementById('highAccuracyBadge');
    const simBadge = document.getElementById('simulatedBadge');
    if (isLiveGps) {
        if (highAccBadge) {
            highAccBadge.classList.remove('d-none');
            highAccBadge.innerHTML = `<i class="fa-solid fa-crosshairs me-1"></i> Live GPS (±${accuracyMeters}m)`;
        }
        if (simBadge) simBadge.classList.add('d-none');
    } else {
        if (highAccBadge) highAccBadge.classList.add('d-none');
        if (simBadge) {
            simBadge.classList.remove('d-none');
            simBadge.innerHTML = `<i class="fa-solid fa-tower-cell me-1"></i> Simulated Cellular HLR (±${accuracyMeters}m)`;
        }
    }
}

// Start polling for remote device beacon
function startBeaconPolling(token) {
    if (CyberTrackMaps.beaconPollingInterval) {
        clearInterval(CyberTrackMaps.beaconPollingInterval);
    }

    const terminal = document.getElementById('trackerTerminal');
    const badge = document.getElementById('beaconPollBadge');

    CyberTrackMaps.beaconPollingInterval = setInterval(async () => {
        try {
            const res = await fetch(`/api/beacon-status/${token}/`);
            const data = await res.json();
            if (data.success && data.is_live_gps) {
                clearInterval(CyberTrackMaps.beaconPollingInterval);
                CyberTrackMaps.beaconPollingInterval = null;

                if (badge) {
                    badge.className = 'badge bg-success border border-success fs-9';
                    badge.innerHTML = '<i class="fa-solid fa-check-double me-1"></i> Target Synchronized';
                }

                logToTerminal(terminal, 'BEACON_SYNC', `High-accuracy GPS fix reported by target device! Precision: ±${data.accuracy_meters}m.`, 'success');
                logToTerminal(terminal, 'ADDRESS', data.location_name, 'info');

                plotImeiOnMap(data.latitude, data.longitude, 'Remote Device (Verified)', data.location_name, data.accuracy_meters, true);

                // Update Telemetry display
                document.getElementById('telCoords').textContent = `${data.latitude}, ${data.longitude}`;
                document.getElementById('telLocation').textContent = data.location_name;
                document.getElementById('telStatus').textContent = `Live GPS (±${data.accuracy_meters}m)`;
            }
        } catch (e) {
            console.warn('Beacon poll error:', e);
        }
    }, 3500);
}

// ==========================================
// 1. IMEI & Device Tracker Handler
// ==========================================
function initImeiTracker() {
    const imeiForm = document.getElementById('imeiTrackForm');
    if (!imeiForm) return;

    const terminal = document.getElementById('trackerTerminal');
    const progressBar = document.getElementById('trackerProgressBar');
    const trackBtn = document.getElementById('trackSubmitBtn');
    const telemetryCard = document.getElementById('telemetryCard');
    const beaconCard = document.getElementById('beaconCard');

    // Initialize Map with global view
    CyberTrackMaps.imeiMap = initLeafletMap('imeiMapContainer', 20.0, 0.0, 2);

    // Recenter Button
    const recenterBtn = document.getElementById('mapRecenterBtn');
    if (recenterBtn) {
        recenterBtn.addEventListener('click', () => {
            if (CyberTrackMaps.lastCoords && CyberTrackMaps.imeiMap) {
                CyberTrackMaps.imeiMap.panTo(CyberTrackMaps.lastCoords);
            }
        });
    }

    // Play locator chime button
    const chimeBtn = document.getElementById('playChimeBtn');
    if (chimeBtn) {
        chimeBtn.addEventListener('click', playFindMyDeviceSound);
    }

    // Direct Hardware GPS Sync button
    const syncGpsBtn = document.getElementById('syncHardwareGpsBtn');
    if (syncGpsBtn) {
        syncGpsBtn.addEventListener('click', () => {
            if (!navigator.geolocation) {
                alert('Geolocation is not supported by your browser.');
                return;
            }

            syncGpsBtn.disabled = true;
            syncGpsBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Calibrating Satellites...';
            terminal.innerHTML = '';
            progressBar.style.width = '10%';
            logToTerminal(terminal, 'GNSS_INIT', 'Interrogating device hardware GPS sensor and Wi-Fi positioning grid...', 'info');

            navigator.geolocation.getCurrentPosition(
                async (pos) => {
                    const lat = pos.coords.latitude;
                    const lng = pos.coords.longitude;
                    const accuracy = pos.coords.accuracy;
                    const altitude = pos.coords.altitude;
                    const heading = pos.coords.heading;
                    const speed = pos.coords.speed;

                    progressBar.style.width = '60%';
                    logToTerminal(terminal, 'GNSS_LOCK', `Hardware GNSS fix acquired! Raw: ${lat.toFixed(6)}, ${lng.toFixed(6)} (accuracy ±${Math.round(accuracy)}m).`, 'success');
                    logToTerminal(terminal, 'REVERSE_GEO', 'Querying OpenCage geospatial database for exact street address...', 'info');

                    try {
                        const res = await fetch('/api/sync-device-gps/', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': getCookie('csrftoken')
                            },
                            body: JSON.stringify({
                                latitude: lat,
                                longitude: lng,
                                accuracy: accuracy,
                                altitude: altitude,
                                heading: heading,
                                speed: speed,
                                device_name: navigator.userAgent.includes('Mobile') ? 'Connected Smartphone' : 'Connected Workstation',
                                identifier: 'Device-Hardware-Sensor'
                            })
                        });

                        const data = await res.json();
                        progressBar.style.width = '100%';

                        if (data.success) {
                            logToTerminal(terminal, 'STREET_SOLVED', data.location_name, 'success');
                            logToTerminal(terminal, 'COMPLETE', `High Accuracy Find My Device Lock: Precision ±${data.accuracy_meters} meters.`, 'success');

                            plotImeiOnMap(data.latitude, data.longitude, 'Live Hardware Sensor', data.location_name, data.accuracy_meters, true);

                            // Populate telemetry card
                            if (telemetryCard) {
                                telemetryCard.classList.remove('d-none');
                                document.getElementById('telBrand').textContent = 'Hardware Sensor';
                                document.getElementById('telModel').textContent = 'Direct GNSS Chipset';
                                document.getElementById('telCarrier').textContent = 'Satellite Constellation / Wi-Fi';
                                document.getElementById('telCoords').textContent = `${data.latitude}, ${data.longitude}`;
                                document.getElementById('telLocation').textContent = data.location_name;
                                document.getElementById('telStatus').textContent = `Live GPS Locked (±${data.accuracy_meters}m)`;
                                document.getElementById('telStatus').className = 'badge bg-success bg-opacity-25 text-success border border-success me-1';
                                document.getElementById('telBattery').textContent = '100% Active';

                                const noticeTitle = document.getElementById('telemetryModeTitle');
                                const noticeDesc = document.getElementById('telemetryModeDesc');
                                const noticeBanner = document.getElementById('telemetryNotice');
                                if (noticeTitle && noticeDesc && noticeBanner) {
                                    noticeBanner.className = 'alert alert-success bg-success bg-opacity-10 border-success border-opacity-25 p-2 mb-3 d-flex align-items-center justify-content-between fs-8';
                                    noticeTitle.className = 'text-success';
                                    noticeTitle.textContent = "Live Hardware GPS Telemetry:";
                                    noticeDesc.textContent = `High precision satellite fix (±${data.accuracy_meters}m) verified directly via device onboard hardware GNSS chipset.`;
                                }

                                document.getElementById('telGmapsLink').href = data.google_maps_url;
                                const findMy = document.getElementById('telFindMyLink');
                                findMy.href = data.google_find_my_url;
                                findMy.classList.remove('d-none');
                            }
                        } else {
                            throw new Error(data.error || 'Failed to sync GPS');
                        }
                    } catch (e) {
                        logToTerminal(terminal, 'ERROR', `Sync error: ${e.message}`, 'error');
                    } finally {
                        syncGpsBtn.disabled = false;
                        syncGpsBtn.innerHTML = '<i class="fa-solid fa-location-crosshairs me-1"></i> Sync Hardware GPS';
                    }
                },
                (err) => {
                    syncGpsBtn.disabled = false;
                    syncGpsBtn.innerHTML = '<i class="fa-solid fa-location-crosshairs me-1"></i> Sync Hardware GPS';
                    logToTerminal(terminal, 'ERR_GPS', `Hardware location access rejected or unavailable: ${err.message}`, 'error');
                },
                {
                    enableHighAccuracy: true,
                    timeout: 15000,
                    maximumAge: 0
                }
            );
        });
    }

    // Device selector radio change
    const deviceRadios = document.querySelectorAll('input[name="device_type"]');
    const androidFields = document.getElementById('androidFields');
    const iphoneFields = document.getElementById('iphoneFields');

    deviceRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            if (e.target.value === 'android') {
                androidFields.classList.remove('d-none');
                iphoneFields.classList.add('d-none');
                document.getElementById('trackBtnText').textContent = 'Track Android Device';
            } else {
                androidFields.classList.add('d-none');
                iphoneFields.classList.remove('d-none');
                document.getElementById('trackBtnText').textContent = 'Track iPhone (Find My)';
            }
        });
    });

    // Sample Fill Button
    const sampleBtn = document.getElementById('fillSampleImei');
    if (sampleBtn) {
        sampleBtn.addEventListener('click', () => {
            const activeType = document.querySelector('input[name="device_type"]:checked').value;
            if (activeType === 'android') {
                const samples = ['354595804618131', '355773902211342', '867234051892341'];
                document.getElementById('imeiInput').value = samples[Math.floor(Math.random() * samples.length)];
                document.getElementById('accountEmailInput').value = 'target.device@gmail.com';
            } else {
                document.getElementById('appleIdInput').value = 'target.user@icloud.com';
            }
        });
    }

    // Copy Beacon Link Button
    const copyBeaconBtn = document.getElementById('copyBeaconBtn');
    if (copyBeaconBtn) {
        copyBeaconBtn.addEventListener('click', () => {
            const urlInput = document.getElementById('beaconUrlInput');
            urlInput.select();
            navigator.clipboard.writeText(urlInput.value);
            copyBeaconBtn.innerHTML = '<i class="fa-solid fa-check me-1"></i> Copied!';
            setTimeout(() => {
                copyBeaconBtn.innerHTML = '<i class="fa-solid fa-copy me-1"></i> Copy Link';
            }, 2000);
        });
    }

    // Form Submit Handler
    imeiForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const deviceType = document.querySelector('input[name="device_type"]:checked').value;
        const imei = document.getElementById('imeiInput')?.value.trim();
        const appleId = document.getElementById('appleIdInput')?.value.trim();
        const accountEmail = document.getElementById('accountEmailInput')?.value.trim();

        if (deviceType === 'android' && !imei) {
            logToTerminal(terminal, 'ERR', 'Please enter a 15-digit IMEI number.', 'error');
            return;
        }
        if (deviceType === 'iphone' && !appleId) {
            logToTerminal(terminal, 'ERR', 'Please enter an Apple ID email address.', 'error');
            return;
        }

        // Lock button & Reset UI
        trackBtn.disabled = true;
        trackBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span> Interrogating Network...`;
        terminal.innerHTML = '';
        progressBar.style.width = '5%';
        logToTerminal(terminal, 'SYS', 'Initiating tracking sequence for target hardware...', 'info');

        const targetRegion = document.getElementById('targetRegionSelect')?.value || 'auto';
        let clientTimezone = '';
        try {
            clientTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone || '';
        } catch (e) {}

        const formData = new FormData();
        formData.append('device_type', deviceType);
        formData.append('imei', imei);
        formData.append('apple_id', appleId);
        formData.append('account_email', accountEmail);
        formData.append('target_region', targetRegion);
        formData.append('client_timezone', clientTimezone);

        try {
            const response = await fetch('/api/track-imei/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: formData
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                logToTerminal(terminal, 'ERROR', data.error || 'Tracking failed.', 'error');
                progressBar.style.width = '100%';
                progressBar.classList.add('bg-danger');
                trackBtn.disabled = false;
                trackBtn.innerHTML = `<i class="fa-solid fa-satellite-dish me-2"></i> Track Device`;
                return;
            }

            // Animate step logs sequentially
            const steps = data.steps || [];
            for (let i = 0; i < steps.length; i++) {
                const step = steps[i];
                await new Promise(r => setTimeout(r, 380));
                progressBar.style.width = `${step.progress}%`;
                const logType = i === steps.length - 1 ? 'success' : 'info';
                logToTerminal(terminal, step.stage, step.text, logType);
            }

            // Note in terminal about simulated telemetry vs live GPS
            logToTerminal(terminal, 'SIMULATION_NOTE', `Carrier sector simulated (±${data.accuracy_meters}m). For live moving GPS, use Beacon link below or Sync Hardware GPS.`, 'info');

            // Display Remote Beacon Link for target phone
            if (data.beacon_url && beaconCard) {
                beaconCard.classList.remove('d-none');
                document.getElementById('beaconUrlInput').value = data.beacon_url;
                document.getElementById('openBeaconDirectBtn').href = data.beacon_url;
                startBeaconPolling(data.beacon_token);
            }

            // Update Telemetry display card
            if (telemetryCard) {
                telemetryCard.classList.remove('d-none');
                document.getElementById('telBrand').textContent = data.brand;
                document.getElementById('telModel').textContent = data.model;
                document.getElementById('telCarrier').textContent = data.carrier;
                document.getElementById('telCoords').textContent = `${data.latitude}, ${data.longitude}`;
                document.getElementById('telLocation').textContent = data.location_name;
                document.getElementById('telStatus').textContent = `Simulated HLR (±${data.accuracy_meters}m)`;
                document.getElementById('telStatus').className = 'badge bg-warning bg-opacity-25 text-warning border border-warning me-1';
                document.getElementById('telBattery').textContent = data.battery_level;

                const noticeTitle = document.getElementById('telemetryModeTitle');
                const noticeDesc = document.getElementById('telemetryModeDesc');
                const noticeBanner = document.getElementById('telemetryNotice');
                if (noticeTitle && noticeDesc && noticeBanner) {
                    noticeBanner.className = 'alert alert-warning bg-warning bg-opacity-10 border-warning border-opacity-25 p-2 mb-3 d-flex align-items-center justify-content-between fs-8';
                    noticeTitle.className = 'text-warning';
                    noticeTitle.textContent = "Simulated Cellular Telemetry:";
                    noticeDesc.textContent = `Coordinates approximated via ${data.carrier} network routing near ${data.location_name}. For meter-level real-time satellite GPS, use "Sync Hardware GPS" or the Remote Beacon Link.`;
                }

                const findMyLink = document.getElementById('telFindMyLink');
                if (findMyLink) {
                    findMyLink.href = data.find_my_url;
                    findMyLink.classList.remove('d-none');
                }
                const gmapsLink = document.getElementById('telGmapsLink');
                if (gmapsLink) {
                    gmapsLink.href = data.google_maps_url;
                }
            }

            // Render Map
            plotImeiOnMap(data.latitude, data.longitude, `${data.brand} ${data.model}`, data.location_name, data.accuracy_meters, false);

        } catch (err) {
            logToTerminal(terminal, 'FATAL', `Network communication error: ${err.message}`, 'error');
        } finally {
            trackBtn.disabled = false;
            trackBtn.innerHTML = `<i class="fa-solid fa-satellite-dish me-2"></i> Track Device`;
        }
    });
}

// ==========================================
// 2. Phone Locator Handler
// ==========================================
function initPhoneLocator() {
    const phoneForm = document.getElementById('phoneLocateForm');
    if (!phoneForm) return;

    const phoneBtn = document.getElementById('phoneSubmitBtn');
    const phoneResults = document.getElementById('phoneResultsCard');

    CyberTrackMaps.phoneMap = initLeafletMap('phoneMapContainer', 0, 20, 2);

    // Sample Phone Numbers
    const sampleBtn = document.getElementById('fillSamplePhone');
    if (sampleBtn) {
        sampleBtn.addEventListener('click', () => {
            const samples = [
                { num: '+254722000000', loc: 'Nairobi, Kenya' },
                { num: '+442079460991', loc: 'London, UK' },
                { num: '+14155552671', loc: 'San Francisco, CA' },
                { num: '+27117109000', loc: 'Johannesburg, South Africa' }
            ];
            const chosen = samples[Math.floor(Math.random() * samples.length)];
            document.getElementById('phoneNumberInput').value = chosen.num;
            document.getElementById('userLocationInput').value = chosen.loc;
        });
    }

    phoneForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const phoneNumber = document.getElementById('phoneNumberInput')?.value.trim();
        const userLocation = document.getElementById('userLocationInput')?.value.trim();

        if (!phoneNumber) {
            alert('Please enter a phone number in international format.');
            return;
        }

        phoneBtn.disabled = true;
        phoneBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span> Geocoding Number...`;

        const formData = new FormData();
        formData.append('phone_number', phoneNumber);
        formData.append('user_location', userLocation);

        try {
            const response = await fetch('/api/track-phone/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: formData
            });

            const data = await response.json();
            if (!response.ok || !data.success) {
                alert(data.error || 'Failed to locate phone number.');
                return;
            }

            // Populate Results Card
            if (phoneResults) {
                phoneResults.classList.remove('d-none');
                document.getElementById('resPhoneNum').textContent = data.formatted_number;
                document.getElementById('resCarrier').textContent = data.carrier;
                document.getElementById('resCountry').textContent = data.location_name;
                document.getElementById('resResolvedAddress').textContent = data.resolved_address;
                document.getElementById('resCoords').textContent = `${data.target_lat}, ${data.target_lng}`;

                const distEl = document.getElementById('resDistance');
                if (distEl) {
                    if (data.distance_km !== null && data.distance_km !== undefined) {
                        distEl.textContent = `${data.distance_km} km`;
                        document.getElementById('distContainer')?.classList.remove('d-none');
                    } else {
                        document.getElementById('distContainer')?.classList.add('d-none');
                    }
                }

                const dirLink = document.getElementById('resDirectionsLink');
                if (dirLink) {
                    dirLink.href = data.directions_url;
                }
            }

            // Render Map with Target & Route
            const map = CyberTrackMaps.phoneMap;
            if (map) {
                map.invalidateSize();
                CyberTrackMaps.phoneMarkers.forEach(m => map.removeLayer(m));
                CyberTrackMaps.phoneMarkers = [];
                if (CyberTrackMaps.phoneRoute) map.removeLayer(CyberTrackMaps.phoneRoute);

                const targetMarker = L.marker([data.target_lat, data.target_lng])
                    .addTo(map)
                    .bindPopup(`
                        <div class="p-1">
                            <strong class="text-cyan">${data.formatted_number}</strong><br>
                            <span>Carrier: ${data.carrier}</span><br>
                            <span class="fs-8 text-secondary">${data.resolved_address}</span>
                        </div>
                    `);
                CyberTrackMaps.phoneMarkers.push(targetMarker);

                if (data.user_coords) {
                    const userMarker = L.marker([data.user_coords.lat, data.user_coords.lng])
                        .addTo(map)
                        .bindPopup(`<strong>Your Location:</strong> ${data.user_coords.formatted}`);
                    CyberTrackMaps.phoneMarkers.push(userMarker);

                    const latlngs = [
                        [data.user_coords.lat, data.user_coords.lng],
                        [data.target_lat, data.target_lng]
                    ];

                    CyberTrackMaps.phoneRoute = L.polyline(latlngs, {
                        color: '#00f0ff',
                        weight: 3,
                        dashArray: '6, 8',
                        opacity: 0.85
                    }).addTo(map);

                    map.fitBounds(latlngs, { padding: [50, 50] });
                    targetMarker.openPopup();
                } else {
                    map.flyTo([data.target_lat, data.target_lng], 10, { duration: 1.5 });
                    targetMarker.openPopup();
                }
            }

        } catch (err) {
            alert(`Error locating phone number: ${err.message}`);
        } finally {
            phoneBtn.disabled = false;
            phoneBtn.innerHTML = `<i class="fa-solid fa-magnifying-glass-location me-2"></i> Locate Phone`;
        }
    });
}

// ==========================================
// 3. Tracking History Interactive Actions
// ==========================================
function initHistoryPage() {
    const deleteBtns = document.querySelectorAll('.delete-record-btn');
    deleteBtns.forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const recordId = btn.getAttribute('data-id');
            if (!confirm('Are you sure you want to delete this tracking record?')) return;

            try {
                const res = await fetch(`/api/delete/${recordId}/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                const data = await res.json();
                if (data.success) {
                    const row = document.getElementById(`record-row-${recordId}`);
                    if (row) row.remove();
                }
            } catch (err) {
                console.error(err);
            }
        });
    });

    const clearHistoryBtn = document.getElementById('clearAllHistoryBtn');
    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener('click', async () => {
            if (!confirm('Warning: This will permanently delete ALL tracking logs. Proceed?')) return;
            try {
                const res = await fetch('/api/clear-history/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                const data = await res.json();
                if (data.success) {
                    window.location.reload();
                }
            } catch (err) {
                console.error(err);
            }
        });
    }
}

// Document Ready
document.addEventListener('DOMContentLoaded', () => {
    initImeiTracker();
    initPhoneLocator();
    initHistoryPage();
});
