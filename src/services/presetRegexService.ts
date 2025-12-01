import apiClient from '@/utils/api';

export interface PresetRegexRule {
    id: number;
    preset_id: number;
    name: string;
    pattern: string;
    replacement: string;
    type: 'pre' | 'post';
    is_active: boolean;
    sort_order: number;
    creator_username?: string;
    created_at: string;
    updated_at: string;
}

export interface PresetRegexRuleCreate {
    name: string;
    pattern: string;
    replacement: string;
    type: 'pre' | 'post';
    is_active: boolean;
    sort_order: number;
}

export interface PresetRegexRuleUpdate extends PresetRegexRuleCreate { }

class PresetRegexService {
    /**
     * 获取预设的所有正则规则
     */
    async getPresetRegexRules(presetId: number): Promise<PresetRegexRule[]> {
        const response = await apiClient.get<PresetRegexRule[]>(`/presets/${presetId}/regex/`);
        return response.data;
    }

    /**
     * 创建预设的正则规则
     */
    async createPresetRegexRule(presetId: number, data: PresetRegexRuleCreate): Promise<PresetRegexRule> {
        const response = await apiClient.post<PresetRegexRule>(`/presets/${presetId}/regex/`, data);
        return response.data;
    }

    /**
     * 更新预设的正则规则
     */
    async updatePresetRegexRule(presetId: number, ruleId: number, data: PresetRegexRuleUpdate): Promise<PresetRegexRule> {
        const response = await apiClient.put<PresetRegexRule>(`/presets/${presetId}/regex/${ruleId}`, data);
        return response.data;
    }

    /**
     * 删除预设的正则规则
     */
    async deletePresetRegexRule(presetId: number, ruleId: number): Promise<void> {
        await apiClient.delete(`/presets/${presetId}/regex/${ruleId}`);
    }
}

export const presetRegexService = new PresetRegexService();
