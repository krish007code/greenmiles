import { ArrowDownRight } from 'lucide-react';

const sections = [
    { href: '#discover', label: 'Discover' },
    { href: '#map', label: 'Map' },
    { href: '#evidence', label: 'Evidence' },
    { href: '#about', label: 'About' },
];

export function AnnouncementBar() {
    return (
        <div className="announcement-bar">
            <div className="announcement-bar__brand">
                <img src="/assets/brand-leaf.svg" width="13.5" height="15" alt="" />
                <span className="announcement-bar__title">Botanical Discovery Engine</span>
                <span className="announcement-bar__separator" aria-hidden="true" />
                <span className="announcement-bar__location">Nature-first route exploration</span>
            </div>
            <nav className="section-nav" aria-label="Page sections">
                {sections.map(({ href, label }, index) => (
                    <a className={index === 0 ? 'section-nav__link is-active' : 'section-nav__link'} href={href} key={href}>
                        {index === 2 && <ArrowDownRight aria-hidden="true" size={12} />}
                        {label}
                    </a>
                ))}
            </nav>
        </div>
    );
}
