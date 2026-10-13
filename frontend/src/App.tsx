import { AnnouncementBar } from './components/AnnouncementBar';
import { DiscoveryPanel } from './components/DiscoveryPanel';
import { HeroSection } from './components/HeroSection';
import { MapPanel } from './components/MapPanel';
import { PreferencesForm } from './components/PreferencesForm';
import { useState } from 'react';
import { ApiError, generateRoutes, type RouteRequest, type RouteResponse } from './api/client';

export default function App() {
    const [requestState, setRequestState] = useState<'idle' | 'loading' | 'error' | 'no_route' | 'success'>('idle');
    const [routeResponse, setRouteResponse] = useState<RouteResponse | null>(null);
    const [errorMessage, setErrorMessage] = useState('');
    const [requestedStart, setRequestedStart] = useState<[number, number] | undefined>();

    async function handleGenerate(request: RouteRequest) {
        setRequestState('loading');
        setRouteResponse(null);
        setErrorMessage('');
        setRequestedStart([request.start_longitude, request.start_latitude]);
        try {
            const response = await generateRoutes(request);
            setRouteResponse(response);
            setRequestState(response.status === 'ok' ? 'success' : 'no_route');
        } catch (error) {
            setErrorMessage(error instanceof ApiError ? error.message : 'Route generation failed unexpectedly.');
            setRequestState('error');
        }
    }

    return (
        <div className="app-shell">
            <header className="page-header">
                <AnnouncementBar />
                <div className="hero-experience">
                    <HeroSection />
                    <PreferencesForm onGenerate={handleGenerate} isLoading={requestState === 'loading'} />
                </div>
            </header>
            <main className="main-content">
                <div className="workspace">
                    <MapPanel routes={routeResponse?.routes ?? []} selectedRouteId={routeResponse?.routes[0]?.route_id} center={routeResponse?.start_snap?.snapped_coordinate ?? requestedStart} />
                    <DiscoveryPanel state={requestState} response={routeResponse} errorMessage={errorMessage} />
                </div>
            </main>
            <footer className="site-footer" id="about">
                <div className="site-footer__brand">
                    <img src="/assets/brand-leaf.svg" width="15" height="17" alt="" />
                    <span>GreenMiles</span>
                </div>
                <p>Nature-first route exploration, grounded in what the map actually knows.</p>
            </footer>
        </div>
    );
}
