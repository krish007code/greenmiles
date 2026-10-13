import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from 'react';
import { AlertTriangle, Leaf, LoaderCircle } from 'lucide-react';

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: 'primary' | 'secondary' | 'quiet';
};

export function Button({ className = '', variant = 'primary', ...props }: ButtonProps) {
    return <button className={`button button--${variant} ${className}`} {...props} />;
}

type CardProps = HTMLAttributes<HTMLElement> & {
    children: ReactNode;
    tone?: 'paper' | 'white';
};

export function Card({ children, className = '', tone = 'paper', ...props }: CardProps) {
    return (
        <section className={`card card--${tone} ${className}`} {...props}>
            {children}
        </section>
    );
}

export function Badge({ children, className = '' }: { children: ReactNode; className?: string }) {
    return <span className={`badge ${className}`}>{children}</span>;
}

export type StateKind = 'empty' | 'loading' | 'error';

const stateIcons = {
    empty: Leaf,
    loading: LoaderCircle,
    error: AlertTriangle,
};

export function StateMessage({
    kind,
    title,
    description,
}: {
    kind: StateKind;
    title: string;
    description: string;
}) {
    const Icon = stateIcons[kind];
    return (
        <div className={`state-message state-message--${kind}`} role={kind === 'error' ? 'alert' : 'status'}>
            <span className="state-message__icon" aria-hidden="true">
                <Icon size={18} strokeWidth={1.8} className={kind === 'loading' ? 'spin' : undefined} />
            </span>
            <div>
                <h3>{title}</h3>
                <p>{description}</p>
            </div>
        </div>
    );
}
