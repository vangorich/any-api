import apiClient from '@/utils/api';

export interface PresetItem {
    id: number;
    role: 'system' | 'user' | 'assistant';
    type: 'normal' | 'user_input' | 'history';
    name: string;
    content: string;
    sort_order: number;
    enabled: boolean;
    creator_username?: string;
    created_at: string;
    updated_at: string;
}

export interface Preset {
    id: number;
    name: string;
    is_active: boolean;
    sort_order: number;
    created_at: string;
    updated_at: string;
    items: PresetItem[];
    content?: string;
}

export interface PresetCreate {
    name: string;
    is_active: boolean;
    sort_order: number;
    content?: string;
}

export interface PresetUpdate extends PresetCreate { }

class PresetService {
    /**
     * 获取所有预设
     */
    async getPresets(): Promise<Preset[]> {
        const response = await apiClient.get<Preset[]>('/presets/');
        return response.data;
    }

    /**
     * 创建新预设
     */
    async createPreset(data: PresetCreate): Promise<Preset> {
        const response = await apiClient.post<Preset>('/presets/', data);
        return response.data;
    }

    /**
     * 更新预设
     */
    async updatePreset(id: number, data: PresetUpdate): Promise<Preset> {
        const response = await apiClient.put<Preset>(`/presets/${id}`, data);
        return response.data;
    }

    /**
     * 删除预设
     */
    async deletePreset(id: number): Promise<void> {
        await apiClient.delete(`/presets/${id}`);
    }

    // --- Preset Item Methods ---

    /**
     * 创建预设条目
     */
    async createPresetItem(presetId: number, data: Omit<PresetItem, 'id' | 'creator_username' | 'created_at' | 'updated_at'>): Promise<PresetItem> {
        const response = await apiClient.post<PresetItem>(`/presets/${presetId}/items/`, data);
        return response.data;
    }

    /**
     * 更新预设条目
     */
    async updatePresetItem(presetId: number, itemId: number, data: Partial<Omit<PresetItem, 'id' | 'creator_username' | 'created_at' | 'updated_at'>>): Promise<PresetItem> {
        const response = await apiClient.put<PresetItem>(`/presets/${presetId}/items/${itemId}`, data);
        return response.data;
    }

    /**
     * 删除预设条目
     */
    async deletePresetItem(presetId: number, itemId: number): Promise<void> {
        await apiClient.delete(`/presets/${presetId}/items/${itemId}`);
    }
}

export const presetService = new PresetService();
