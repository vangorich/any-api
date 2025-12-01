import React, { createContext, useContext, useState, useEffect } from 'react';
import { getSystemConfig, SystemConfig } from '@/services/systemService';

interface SystemContextType {
    config: SystemConfig | null;
    loading: boolean;
}

const SystemContext = createContext<SystemContextType>({
    config: null,
    loading: true,
});

export const useSystem = () => useContext(SystemContext);

export const SystemProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [config, setConfig] = useState<SystemConfig | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchConfig = async () => {
            try {
                const systemConfig = await getSystemConfig();
                setConfig(systemConfig);
            } catch (error) {
                console.error('Failed to fetch system config:', error);
                // Set a default config on failure
                setConfig({
                    site_name: 'Any API',
                    server_url: '',
                    allow_registration: false,
                    allow_password_login: false,
                    require_email_verification: false,
                    enable_turnstile: false,
                    enable_captcha: false,
                    turnstile_site_key: null,
                    email_whitelist_enabled: false,
                    email_whitelist: [],
                });
            } finally {
                setLoading(false);
            }
        };

        fetchConfig();
    }, []);

    return (
        <SystemContext.Provider value={{ config, loading }}>
            {children}
        </SystemContext.Provider>
    );
};