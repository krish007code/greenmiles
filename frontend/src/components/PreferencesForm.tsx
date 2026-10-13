import { useState, type FormEvent } from 'react';
import { LocateFixed, MapPin, Route, Trees } from 'lucide-react';
import type { RouteRequest } from '../api/client';
import { Button } from './ui';

export function PreferencesForm({
    onGenerate,
    isLoading,
}: {
    onGenerate: (request: RouteRequest) => Promise<void>;
    isLoading: boolean;
}) {
    const [distance, setDistance] = useState(7.5);
    const [canopyFocus, setCanopyFocus] = useState(true);
    const [startPoint, setStartPoint] = useState('');
    const [validationMessage, setValidationMessage] = useState('');

    async function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        const coordinates = startPoint.split(',').map((part) => Number(part.trim()));
        if (coordinates.length !== 2 || coordinates.some((coordinate) => !Number.isFinite(coordinate))) {
            setValidationMessage('Enter a start point as latitude, longitude.');
            return;
        }
        const [latitude, longitude] = coordinates;
        if (latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
            setValidationMessage('Latitude must be between −90 and 90; longitude between −180 and 180.');
            return;
        }
        setValidationMessage('');
        await onGenerate({
            start_latitude: latitude,
            start_longitude: longitude,
            target_distance_m: distance * 1000,
        });
    }

    return (
        <section className="preferences-card" aria-label="Route preferences">
            <form className="preferences-form" onSubmit={handleSubmit}>
                <label className="preference-field preference-field--location">
                    <span className="field-label"><MapPin size={13} aria-hidden="true" /> Trailhead / start point</span>
                    <span className="location-input-wrap">
                        <input className="text-input" type="text" name="start" placeholder="Latitude, longitude" autoComplete="off" value={startPoint} onChange={(event) => setStartPoint(event.target.value)} aria-describedby="start-hint" />
                        <button className="input-action" type="button" aria-label="Use current location" title="Current-location lookup is not available yet" disabled>
                            <LocateFixed size={16} aria-hidden="true" />
                        </button>
                    </span>
                </label>

                <label className="preference-field preference-field--distance" htmlFor="target-distance">
                    <span className="field-label"><Route size={14} aria-hidden="true" /> Target loop</span>
                    <span className="distance-value">{distance.toFixed(1)} km</span>
                    <input
                        className="distance-slider"
                        id="target-distance"
                        name="distance"
                        type="range"
                        min="1"
                        max="20"
                        step="0.5"
                        value={distance}
                        onChange={(event) => setDistance(Number(event.target.value))}
                        aria-label="Target loop distance in kilometers"
                    />
                    <span className="range-hints" aria-hidden="true"><span>1 km</span><span>20 km</span></span>
                </label>

                <label className="preference-field preference-field--canopy" htmlFor="canopy-focus">
                    <span className="field-label"><Trees size={15} aria-hidden="true" /> Vegetation priority</span>
                    <span className="toggle-row">
                        <span>Dense canopy focus</span>
                        <input
                            className="toggle-input"
                            id="canopy-focus"
                            type="checkbox"
                            checked={canopyFocus}
                            onChange={(event) => setCanopyFocus(event.target.checked)}
                        />
                    </span>
                </label>

                <p className="coordinate-hint" id="start-hint">Coordinates are entered as latitude, longitude. Location search is not connected.</p>

                <Button type="submit" className="preferences-form__submit" disabled={isLoading} aria-busy={isLoading}>
                    <Route size={15} aria-hidden="true" /> {isLoading ? 'Searching…' : 'Generate'}
                </Button>
            </form>
            <p className="form-note" aria-live="polite">{validationMessage || 'Vegetation priority is not yet applied by the route engine.'}</p>
        </section>
    );
}
