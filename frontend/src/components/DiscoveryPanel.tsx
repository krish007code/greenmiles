import { ArrowRight, Check, Download, Leaf, Sparkles } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Button, Card, Badge, StateMessage } from './ui';
import { ApiError, fetchRouteKml, type RouteResponse, type RankedRoute } from '../api/client';

const evidenceTypes = ['Route distance', 'Mapped greenery', 'Surface', 'Pedestrian access', 'Smoothness', 'Lighting'];

function describeNoRoute(response: RouteResponse | null): string {
    const diagnostics = response?.diagnostics ?? {};
    const reason = diagnostics.reason;
    if (reason === 'no_loop_within_distance_tolerance') {
        const states = diagnostics.search_states;
        const nodes = diagnostics.snapped_component_node_count;
        const edges = diagnostics.snapped_component_edge_count;
        const cycleRank = diagnostics.snapped_component_cycle_rank;
        return `No loop matched the requested distance range. Search states: ${String(states ?? 'not reported')}. Snapped component: ${String(nodes ?? 'unknown')} nodes, ${String(edges ?? 'unknown')} edges, cycle rank ${String(cycleRank ?? 'unknown')}. This is a graph limitation, not a safety or greenery assessment.`;
    }
    if (typeof diagnostics.message === 'string') return diagnostics.message;
    if (typeof reason === 'string') return reason.replaceAll('_', ' ');
    return 'The graph has no eligible loop in the requested distance range. This is not a safety or greenery assessment.';
}

function RouteCard({ route, index }: { route: RankedRoute; index: number }) {
    const metrics = route.metrics;
    return (
        <Card className="route-empty-card route-result-card" tone="white">
            <div className="route-result-card__topline">
                <Badge>{index === 0 ? 'Highest evidence score' : `Candidate ${index + 1}`}</Badge>
                {route.ranking_score !== null && <span className="route-result-card__score">{route.ranking_score.toFixed(1)}<small> / 100</small></span>}
            </div>
            <h3 className="route-result-card__title">Route candidate {index + 1}</h3>
            <p className="route-result-card__description">A generated loop from the current OSM graph; mapped tags do not establish safety or legal access.</p>
            <div className="route-result-card__metrics">
                <span><small>DISTANCE</small>{(metrics.route_distance_m / 1000).toFixed(2)} km</span>
                <span><small>EST. TIME</small>{metrics.estimated_duration_min.toFixed(0)} min</span>
                <span><small>GREEN TAGS</small>{metrics.green_space_tagged_percentage === null ? 'Unknown' : `${metrics.green_space_tagged_percentage.toFixed(0)}%`}</span>
            </div>
            <p className="route-result-card__footnote">Ranking: {route.ranking_status.replaceAll('_', ' ')}. {route.provenance.source_filenames.join(', ') || 'Source filename unavailable.'}</p>
            <a className="text-link" href="#map">View on map <ArrowRight size={14} aria-hidden="true" /></a>
        </Card>
    );
}

function evidenceValue(route: RankedRoute | undefined, item: string): string {
    if (!route) return 'Not available';
    const { metrics } = route;
    if (item === 'Route distance') return `${(metrics.route_distance_m / 1000).toFixed(2)} km`;
    if (item === 'Mapped greenery') {
        return metrics.green_space_tagged_percentage === null
            ? 'Unknown — no edge evidence'
            : `${metrics.green_space_tagged_percentage.toFixed(1)}% of route-edge distance`;
    }
    const coverage = item === 'Surface' ? metrics.surface
        : item === 'Pedestrian access' ? metrics.access
            : item === 'Smoothness' ? metrics.smoothness
                : metrics.lighting;
    return `${coverage.known_percentage.toFixed(1)}% tagged · ${coverage.unknown_distance_m.toFixed(0)} m unknown`;
}

export function DiscoveryPanel({
    state,
    response,
    errorMessage,
}: {
    state: 'idle' | 'loading' | 'error' | 'no_route' | 'success';
    response: RouteResponse | null;
    errorMessage: string;
}) {
    const routes = response?.routes ?? [];
    const route = routes[0];
    const [exportState, setExportState] = useState<'idle' | 'loading' | 'error' | 'downloaded'>('idle');
    const [exportMessage, setExportMessage] = useState('');

    useEffect(() => {
        setExportState('idle');
        setExportMessage('');
    }, [route?.route_id]);

    async function handleDownload() {
        if (!route || exportState === 'loading') return;
        setExportState('loading');
        setExportMessage('');
        try {
            const { blob, filename } = await fetchRouteKml(route.route_id);
            const objectUrl = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = objectUrl;
            link.download = filename;
            document.body.append(link);
            link.click();
            link.remove();
            window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
            setExportState('downloaded');
            setExportMessage(`${filename} is ready in your downloads.`);
        } catch (error) {
            setExportState('error');
            setExportMessage(error instanceof ApiError ? error.message : 'KML export failed unexpectedly.');
        }
    }

    return (
        <div className="results-column" id="discover">
            <section className="route-section" aria-labelledby="routes-title">
                <div className="section-heading">
                    <h2 id="routes-title"><span className="section-heading__dot" aria-hidden="true" />Your Next Run</h2>
                    <Badge>{state === 'success' ? `${routes.length} route${routes.length === 1 ? '' : 's'} returned` : state === 'loading' ? 'Searching' : state === 'error' ? 'Service unavailable' : state === 'no_route' ? 'No loop found' : 'Ready to search'}</Badge>
                </div>
                {routes.length > 0 ? routes.map((item, index) => <RouteCard key={item.route_id} route={item} index={index} />) : (
                    <Card className="route-empty-card" tone="white">
                        {state === 'loading' ? (
                            <StateMessage kind="loading" title="Searching mapped paths" description="The route graph is being checked for connected loops within the requested distance." />
                        ) : state === 'error' ? (
                            <StateMessage kind="error" title="Route search failed" description={errorMessage || 'The route service could not complete the request.'} />
                        ) : state === 'no_route' ? (
                            <StateMessage kind="empty" title="No loop found for this request" description={describeNoRoute(response)} />
                        ) : (
                            <StateMessage kind="empty" title="Enter coordinates to find a loop" description="Only route candidates produced by the local OSM graph will be shown here." />
                        )}
                        <a className="text-link" href="#map">Explore the map <ArrowRight size={14} aria-hidden="true" /></a>
                    </Card>
                )}
            </section>

            <Card className="evidence-card" id="evidence">
                <div className="evidence-card__heading">
                    <div>
                        <h2><Leaf size={16} aria-hidden="true" /> Know Your Route</h2>
                        <p>OpenStreetMap evidence &amp; ground truth</p>
                    </div>
                    <Badge>{route ? 'Route evidence' : 'Awaiting a route'}</Badge>
                </div>
                <ul className="evidence-list">
                    {evidenceTypes.map((item) => (
                        <li className="evidence-list__item" key={item}>
                            <span><Check size={13} aria-hidden="true" />{item}</span>
                            <span className="evidence-list__value">{evidenceValue(route, item)}</span>
                        </li>
                    ))}
                </ul>
                <p className="evidence-card__note">{route ? 'Coverage reports mapped tag completeness, not the quality of those tags. Missing values remain unknown; they do not imply unsafe access or a lack of greenery.' : 'Evidence is shown only when supplied by real route data. Unknown values are not inferred.'}</p>
            </Card>

            <section className="botanical-card" aria-label="Nature imagery">
                <img src="/assets/botanical-landscape.jpeg" alt="A green riparian landscape with a trail" width="512" height="279" />
                <div className="botanical-card__caption">
                    <span>Botanical context</span>
                    <p>Illustrative nature photography—not route evidence.</p>
                </div>
            </section>

            <Card className="explanation-card">
                <h2><Sparkles size={16} aria-hidden="true" /> Why this route?</h2>
                <StateMessage
                    kind="empty"
                    title="No explanation yet"
                    description="An explanation can be shown after a real route and its mapped evidence are available."
                />
                <span className="explanation-card__footnote">AI explanations are not connected in this phase.</span>
            </Card>

            <Card className="export-card" tone="white">
                <div className="export-card__copy">
                    <h2>Take your route with you</h2>
                    <p>{route ? 'Download the generated route geometry with its available metrics and OSM attribution.' : 'Generate a route first; only routes returned by this session can be exported.'}</p>
                </div>
                <Button
                    variant="secondary"
                    type="button"
                    disabled={!route || exportState === 'loading'}
                    aria-describedby="export-note"
                    aria-busy={exportState === 'loading'}
                    onClick={handleDownload}
                >
                    <Download size={14} aria-hidden="true" /> {exportState === 'loading' ? 'Preparing…' : 'Download KML'}
                </Button>
                <span
                    id="export-note"
                    className={`export-card__status${exportState === 'error' ? ' export-card__status--error' : ''}`}
                    role={exportState === 'error' ? 'alert' : 'status'}
                    aria-live={exportState === 'error' ? 'assertive' : 'polite'}
                >
                    {exportMessage || (!route ? 'KML export unavailable until a route is generated.' : '')}
                </span>
            </Card>
        </div>
    );
}
