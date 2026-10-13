import { MapPin, Trees } from 'lucide-react';
import { useEffect, useMemo } from 'react';
import { MapContainer, Polyline, ScaleControl, TileLayer, ZoomControl, useMap } from 'react-leaflet';
import type { RankedRoute } from '../api/client';

const mapCenter: [number, number] = [48.161, 11.503];

function FitRoute({ positions, center }: { positions: [number, number][]; center?: [number, number] }) {
    const map = useMap();

    useEffect(() => {
        if (positions.length > 1) {
            map.fitBounds(positions, { padding: [40, 40], maxZoom: 16 });
        } else if (center) {
            map.setView([center[1], center[0]], 14);
        }
    }, [center, map, positions]);

    return null;
}

export function MapPanel({ routes, selectedRouteId, center }: { routes: RankedRoute[]; selectedRouteId?: string; center?: [number, number] }) {
    const selectedRoute = routes.find((route) => route.route_id === selectedRouteId);
    const routePositions = useMemo(
        () => selectedRoute?.geometry.coordinates.map(([longitude, latitude]) => [latitude, longitude] as [number, number]) ?? [],
        [selectedRoute],
    );
    return (
        <section className="map-panel" id="map" aria-labelledby="map-title">
            <div className="map-frame">
                <div className="map-frame__topline">
                    <div className="map-pill">
                        <MapPin size={14} aria-hidden="true" />
                        <span id="map-title">{selectedRoute ? 'Selected route' : 'Map preview'}</span>
                        <span className="map-pill__divider" aria-hidden="true" />
                        <span className="map-pill__subtext">{selectedRoute ? 'Route overlay active' : 'No route overlay'}</span>
                    </div>
                    <div className="map-layer-pill"><Trees size={13} aria-hidden="true" /> OpenStreetMap</div>
                </div>
                <div className="map-canvas" aria-label={selectedRoute ? 'OpenStreetMap showing the selected generated route in Munich.' : 'OpenStreetMap centered on Munich. No generated route is displayed.'}>
                    <MapContainer
                        center={center ? [center[1], center[0]] : mapCenter}
                        zoom={14}
                        scrollWheelZoom={false}
                        zoomControl={false}
                        className="leaflet-map"
                    >
                        <TileLayer
                            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
                            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                        />
                        <FitRoute positions={routePositions} center={center} />
                        {selectedRoute && <Polyline positions={routePositions} pathOptions={{ color: '#3a693a', weight: 5, opacity: 0.9 }} />}
                        <ZoomControl position="topright" />
                        <ScaleControl position="bottomleft" metric imperial={false} />
                    </MapContainer>
                </div>
                <div className="map-caption">
                    <span className="map-caption__dot" aria-hidden="true" />
                    <span>{selectedRoute ? `Showing the returned route (${(selectedRoute.distance_m / 1000).toFixed(2)} km).` : 'Base map centered on Munich. No generated route or canopy layer is displayed.'}</span>
                </div>
            </div>
        </section>
    );
}
