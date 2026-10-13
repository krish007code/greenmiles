import { Leaf } from 'lucide-react';

export function HeroSection() {
    return (
        <section className="hero-card" aria-labelledby="hero-title">
            <img className="hero-card__mark" src="/assets/botanical-mark.svg" alt="" width="105" height="111" />
            <div className="hero-card__intro">
                <div className="hero-card__eyebrow-row">
                    <span className="hero-card__eyebrow"><Leaf size={11} aria-hidden="true" />Nature-first route discovery</span>
                    <span className="hero-card__eyebrow-note">Grounded in mapped evidence</span>
                </div>
                <h1 id="hero-title">Find your path. <span>Follow the green.</span></h1>
                <p>Discover running loops shaped around your distance and the natural spaces along your path.</p>
            </div>
        </section>
    );
}
