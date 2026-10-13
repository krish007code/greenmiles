export interface RouteRequest {
    start_latitude: number;
    start_longitude: number;
    target_distance_m: number;
    tolerance_m?: number;
    max_snap_distance_m?: number;
    max_candidates?: number;
}

export interface RouteResponse {
    status: 'ok' | 'no_route';
    routes: RankedRoute[];
    start_snap: {
        requested_coordinate: [number, number];
        snapped_coordinate: [number, number];
        snap_distance_m: number;
        max_snap_distance_m: number;
    } | null;
    graph_statistics: Record<string, unknown>;
    diagnostics: Record<string, unknown>;
    ranking_status: string;
    rejected_candidates: Array<{ index: number; reason: string }>;
}

export interface RankedRoute {
    route_id: string;
    geometry: {
        type: 'LineString';
        coordinates: [number, number][];
    };
    distance_m: number;
    start_snap: Record<string, unknown>;
    end_snap: Record<string, unknown>;
    metrics: {
        route_distance_m: number;
        distance_status: string;
        distance_limitation: string;
        estimated_duration_min: number;
        pace_min_per_km: number;
        duration_limitation: string;
        surface: CoverageMetric;
        surface_distance_breakdown_m: Record<string, number>;
        access: CoverageMetric;
        smoothness: CoverageMetric;
        lighting: CoverageMetric;
        green_space_tagged_distance_m: number;
        green_space_tagged_percentage: number | null;
        green_space_evidence_status: string;
        green_space_limitation: string;
    };
    ranking_score: number | null;
    ranking_status: string;
    ranking_contributions: Array<{
        metric: string;
        raw_value: number | null;
        normalized_value: number | null;
        configured_weight: number;
        contribution: number;
        status: string;
    }>;
    provenance: {
        osm_element_ids: string[];
        source_filenames: string[];
        source_types: string[];
        attribution: string[];
        licenses: string[];
        synthetic_test_data: boolean;
    };
    limitations: string[];
}

export interface CoverageMetric {
    total_distance_m: number;
    known_distance_m: number;
    unknown_distance_m: number;
    known_percentage: number;
    status: 'complete' | 'incomplete';
    limitation: string;
}

export class ApiError extends Error {
    readonly status: number;
    readonly code?: string;

    constructor(message: string, status: number, code?: string) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.code = code;
    }
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

function errorMessage(payload: unknown, status: number): { message: string; code?: string } {
    if (typeof payload === 'object' && payload !== null && 'detail' in payload) {
        const detail = (payload as { detail?: unknown }).detail;
        if (typeof detail === 'string') return { message: detail };
        if (typeof detail === 'object' && detail !== null) {
            const value = detail as { message?: unknown; code?: unknown };
            if (typeof value.message === 'string') {
                return {
                    message: value.message,
                    code: typeof value.code === 'string' ? value.code : undefined,
                };
            }
        }
    }
    return { message: `The route service returned HTTP ${status}.` };
}

export async function generateRoutes(
    request: RouteRequest,
    signal?: AbortSignal,
): Promise<RouteResponse> {
    let response: Response;
    try {
        response = await fetch(`${API_BASE_URL}/api/routes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request),
            signal,
        });
    } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') throw error;
        throw new ApiError('The route service could not be reached. Check that the local API is running.', 0, 'network_error');
    }

    const payload: unknown = await response.json().catch(() => null);
    if (!response.ok) {
        const failure = errorMessage(payload, response.status);
        throw new ApiError(failure.message, response.status, failure.code);
    }
    return payload as RouteResponse;
}

export async function fetchRouteKml(
    routeId: string,
    signal?: AbortSignal,
): Promise<{ blob: Blob; filename: string }> {
    let response: Response;
    try {
        response = await fetch(`${API_BASE_URL}/api/routes/${encodeURIComponent(routeId)}/kml`, { signal });
    } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') throw error;
        throw new ApiError('The route export service could not be reached. Check that the local API is running.', 0, 'network_error');
    }

    if (!response.ok) {
        const payload: unknown = await response.json().catch(() => null);
        const failure = errorMessage(payload, response.status);
        throw new ApiError(failure.message, response.status, failure.code);
    }

    const disposition = response.headers.get('Content-Disposition');
    const filename = disposition?.match(/filename="([A-Za-z0-9._-]+)"/i)?.[1] ?? `${routeId}.kml`;
    return { blob: await response.blob(), filename };
}
