import { Turnstile, TurnstileInstance } from '@marsidev/react-turnstile';
import { forwardRef } from 'react';

interface TurnstileWidgetProps {
    siteKey: string;
    onVerify: (token: string) => void;
    onError?: () => void;
    theme?: 'light' | 'dark' | 'auto';
    size?: 'normal' | 'compact';
    appearance?: 'always' | 'execute' | 'interaction-only';
    className?: string;
}

const TurnstileWidget = forwardRef<TurnstileInstance, TurnstileWidgetProps>(({
    siteKey,
    onVerify,
    onError,
    theme = 'auto',
    size = 'normal',
    appearance = 'always',
    className = ''
}, ref) => {
    const containerClasses = [
        'flex',
        'justify-center',
        className,
        appearance !== 'interaction-only' ? 'my-4' : '',
    ].filter(Boolean).join(' ');

    return (
        <div className={containerClasses}>
            <Turnstile
                ref={ref}
                siteKey={siteKey}
                onSuccess={onVerify}
                onError={onError}
                options={{
                    theme,
                    size,
                    appearance,
                }}
            />
        </div>
    );
});

TurnstileWidget.displayName = 'TurnstileWidget';

export default TurnstileWidget;
