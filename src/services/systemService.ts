import apiClient from '@/utils/api';

export interface SystemConfig {
    site_name: string;
    server_url: string;
    allow_registration: boolean;
    allow_password_login: boolean;
    require_email_verification: boolean;
    enable_turnstile: boolean;
    enable_captcha: boolean;
    turnstile_site_key: string | null;
    email_whitelist_enabled: boolean;
    email_whitelist: string[];
}

export const getSystemConfig = async (): Promise<SystemConfig> => {
    const response = await apiClient.get('/system/config');
    return response.data;
};