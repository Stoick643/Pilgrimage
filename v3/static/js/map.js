/**
 * Couch Traveller V3 — Map module
 *
 * Features:
 * - Numbered markers with day title info windows
 * - Auto-zoom (fit bounds)
 * - Satellite/terrain toggle
 * - Travel mode toggle (driving / transit / walking)
 * - Total distance & duration
 * - Day-by-day distance breakdown
 * - Click marker → scroll to day card
 * - Click day card → bounce marker
 * - Animated route reveal
 * - Mini static maps per day card (matched by index)
 */

(function () {
    'use strict';

    // --- State ---
    let map = null;
    let markers = [];
    let directionsRenderer = null;
    let currentTravelMode = 'DRIVING';
    let locations = [];     // [{name, lat, lng}, ...]
    let dayTitles = [];     // ["Day 1: Ancient Rome", ...]

    // --- HTML escaping to prevent XSS ---
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }

    // --- Public init (called by Google Maps callback) ---
    window.initMap = function () {
        const config = window.mapConfig;
        if (!config || !config.cities.length) return;

        // Collect day titles from DOM
        dayTitles = [];
        document.querySelectorAll('#streamContent .day-card').forEach(function (card) {
            const h3 = card.querySelector('.day-text h3');
            dayTitles.push(h3 ? h3.textContent : card.dataset.city);
        });

        // Geocode and build map
        fetch('/api/geocode?cities=' + encodeURIComponent(config.cities.join(',')))
            .then(function (r) { return r.json(); })
            .then(function (data) {
                locations = data.locations;
                if (!locations || !locations.length) {
                    document.getElementById('map').innerHTML =
                        '<p class="text-center text-muted py-5">Map unavailable — geocoding failed</p>';
                    return;
                }
                buildMap();
                addMiniMaps();
            })
            .catch(function (err) {
                console.warn('Map init failed:', err);
                document.getElementById('map').innerHTML =
                    '<p class="text-center text-muted py-5">Map unavailable</p>';
            });
    };

    // --- Build map ---
    function buildMap() {
        map = new google.maps.Map(document.getElementById('map'), {
            zoom: 6,
            center: { lat: locations[0].lat, lng: locations[0].lng },
            mapTypeControl: true,
            mapTypeControlOptions: {
                style: google.maps.MapTypeControlStyle.HORIZONTAL_BAR,
                mapTypeIds: ['roadmap', 'satellite', 'terrain'],
            },
        });

        directionsRenderer = new google.maps.DirectionsRenderer({
            map: map,
            suppressMarkers: true,  // We draw our own numbered markers
        });

        // Draw route or markers
        if (locations.length >= 2) {
            drawRoute(function () {
                animateMarkers();
            });
        } else {
            addNumberedMarkers();
            fitBounds();
        }

        // Wire up travel mode buttons
        document.querySelectorAll('[data-travel-mode]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                document.querySelectorAll('[data-travel-mode]').forEach(function (b) {
                    b.classList.remove('active');
                });
                btn.classList.add('active');
                currentTravelMode = btn.dataset.travelMode;
                drawRoute();
            });
        });

        // Wire up day card clicks → bounce marker
        document.querySelectorAll('#streamContent .day-card').forEach(function (card, index) {
            card.style.cursor = 'pointer';
            card.addEventListener('click', function () {
                if (markers[index]) {
                    bounceMarker(index);
                    map.panTo(markers[index].getPosition());
                    map.setZoom(10);
                }
            });
        });
    }

    // --- Numbered markers ---
    function addNumberedMarkers() {
        // Clear existing
        markers.forEach(function (m) { m.setMap(null); });
        markers = [];

        locations.forEach(function (loc, i) {
            const marker = new google.maps.Marker({
                position: { lat: loc.lat, lng: loc.lng },
                map: map,
                title: dayTitles[i] || loc.name,
                label: {
                    text: String(i + 1),
                    color: 'white',
                    fontWeight: 'bold',
                },
                zIndex: i + 1,
            });

            // Info window with day title (escaped)
            const safeTitle = escapeHtml(dayTitles[i] || loc.name);
            const infoContent = '<div style="max-width:220px">' +
                '<strong>Day ' + (i + 1) + '</strong><br>' +
                safeTitle +
                '</div>';
            const infoWindow = new google.maps.InfoWindow({ content: infoContent });

            marker.addListener('click', function () {
                infoWindow.open(map, marker);
                scrollToDayCard(i);
            });

            markers.push(marker);
        });
    }

    // --- Draw route ---
    function drawRoute(onComplete) {
        const ds = new google.maps.DirectionsService();

        const waypoints = locations.slice(1, -1).map(function (l) {
            return {
                location: new google.maps.LatLng(l.lat, l.lng),
                stopover: true,
            };
        });

        ds.route({
            origin: new google.maps.LatLng(locations[0].lat, locations[0].lng),
            destination: new google.maps.LatLng(locations[locations.length - 1].lat, locations[locations.length - 1].lng),
            waypoints: waypoints,
            optimizeWaypoints: false,  // Keep day order
            travelMode: currentTravelMode,
        }, function (result, status) {
            if (status !== 'OK') {
                console.warn('Directions failed:', status);
                addNumberedMarkers();
                fitBounds();
                return;
            }

            directionsRenderer.setDirections(result);
            addNumberedMarkers();
            fitBounds();
            showRouteStats(result);

            if (onComplete) onComplete();
        });
    }

    // --- Fit bounds ---
    function fitBounds() {
        if (!locations.length) return;
        const bounds = new google.maps.LatLngBounds();
        locations.forEach(function (l) {
            bounds.extend({ lat: l.lat, lng: l.lng });
        });
        map.fitBounds(bounds, 50);  // 50px padding
    }

    // --- Route stats ---
    function showRouteStats(result) {
        const route = result.routes[0];
        const legs = route.legs;

        let totalDist = 0;
        let totalDur = 0;
        let breakdownHtml = '';

        legs.forEach(function (leg, i) {
            totalDist += leg.distance.value;
            totalDur += leg.duration.value;

            const fromCity = escapeHtml(leg.start_address.split(',')[0]);
            const toCity = escapeHtml(leg.end_address.split(',')[0]);

            breakdownHtml +=
                '<tr>' +
                '<td><span class="badge bg-secondary">' + (i + 1) + '</span> ' +
                fromCity + ' → ' + toCity + '</td>' +
                '<td class="text-end text-nowrap">' + escapeHtml(leg.distance.text) + '</td>' +
                '<td class="text-end text-nowrap">' + escapeHtml(leg.duration.text) + '</td>' +
                '</tr>';
        });

        const totalDistKm = Math.round(totalDist / 1000);
        const totalHours = Math.floor(totalDur / 3600);
        const totalMins = Math.round((totalDur % 3600) / 60);
        const totalTimeStr = totalHours > 0
            ? totalHours + 'h ' + totalMins + 'min'
            : totalMins + 'min';

        const modeLabel = { DRIVING: 'driving', TRANSIT: 'transit', WALKING: 'walking' };

        const statsEl = document.getElementById('routeStats');
        if (statsEl) {
            statsEl.innerHTML =
                '<div class="card card-body bg-light mt-3">' +
                '<h6 class="mb-2"><i class="bi bi-signpost-split"></i> Route Summary ' +
                '<span class="text-muted fw-normal">(' + (modeLabel[currentTravelMode] || 'driving') + ')</span></h6>' +
                '<p class="mb-2"><strong>' + totalDistKm + ' km</strong> total · <strong>' + totalTimeStr + '</strong> travel time</p>' +
                '<table class="table table-sm table-borderless mb-0">' +
                '<thead><tr><th>Leg</th><th class="text-end">Distance</th><th class="text-end">Time</th></tr></thead>' +
                '<tbody>' + breakdownHtml + '</tbody>' +
                '</table></div>';
        }
    }

    // --- Animated marker reveal ---
    function animateMarkers() {
        markers.forEach(function (m) { m.setVisible(false); });

        markers.forEach(function (marker, i) {
            setTimeout(function () {
                marker.setVisible(true);
                marker.setAnimation(google.maps.Animation.DROP);
            }, i * 400);
        });
    }

    // --- Bounce marker ---
    function bounceMarker(index) {
        const marker = markers[index];
        if (!marker) return;
        marker.setAnimation(google.maps.Animation.BOUNCE);
        setTimeout(function () {
            marker.setAnimation(null);
        }, 1400);  // ~2 bounces
    }

    // --- Click marker → scroll to day card ---
    function scrollToDayCard(index) {
        const cards = document.querySelectorAll('#streamContent .day-card');
        if (cards[index]) {
            cards[index].scrollIntoView({ behavior: 'smooth', block: 'center' });
            // Brief highlight
            cards[index].classList.add('day-card-highlight');
            setTimeout(function () {
                cards[index].classList.remove('day-card-highlight');
            }, 1500);
        }
    }

    // --- Mini static maps per day card (matched by index, not name) ---
    function addMiniMaps() {
        const apiKey = window.mapConfig.apiKey;
        if (!apiKey) return;

        const cards = document.querySelectorAll('#streamContent .day-card');

        cards.forEach(function (card, i) {
            const placeholder = card.querySelector('.minimap-placeholder');
            if (!placeholder) return;

            // Match by index — locations and day cards are in the same order
            const loc = locations[i];
            if (!loc) return;

            const center = loc.lat + ',' + loc.lng;
            const safeCity = escapeHtml(card.dataset.city || loc.name);

            const url = 'https://maps.googleapis.com/maps/api/staticmap' +
                '?center=' + center +
                '&zoom=12&size=350x180' +
                '&markers=color:red|' + center +
                '&maptype=roadmap' +
                '&key=' + apiKey;

            const img = document.createElement('img');
            img.src = url;
            img.alt = 'Map: ' + safeCity;
            img.className = 'img-fluid rounded';
            img.loading = 'lazy';
            img.style.maxWidth = '100%';
            img.onerror = function () {
                // Hide on error (invalid API key, quota exceeded, etc.)
                placeholder.innerHTML = '';
            };

            const wrapper = document.createElement('div');
            wrapper.className = 'minimap mt-2';
            wrapper.appendChild(img);
            placeholder.innerHTML = '';
            placeholder.appendChild(wrapper);
        });
    }

})();
