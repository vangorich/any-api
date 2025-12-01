import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '@/utils/api';
import { Plus, Trash2, Copy, Pencil, Key as KeyIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from '@/components/ui/dialog';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { useToast } from '@/hooks/useToast';
import { confirm } from '@/components/ui/ConfirmDialog';
import { Pagination } from '@/components/ui/pagination';
import { Card, CardContent } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import MaskedKey from '@/components/MaskedKey';
import { Search } from 'lucide-react';

interface ExclusiveKey {
    id: number;
    key: string;
    name: string;
    is_active: boolean;
    preset_id: number | null;
    channel_id: number | null;
    enable_regex: boolean;
    created_at: string;
}

interface Channel {
    id: number;
    name: string;
    type: string;
}

interface Preset {
    id: number;
    name: string;
}

interface PaginatedResponse<T> {
    total: number;
    items: T[];
    page: number;
    size: number;
}

export default function KeysPage() {
    // Data State
    const [exclusiveData, setExclusiveData] = useState<PaginatedResponse<ExclusiveKey>>({ items: [], total: 0, page: 1, size: 10 });
    const [presets, setPresets] = useState<Preset[]>([]);
    const [channels, setChannels] = useState<Channel[]>([]);

    // UI State
    const [searchQuery, setSearchQuery] = useState('');
    const [isExclusiveDialogOpen, setIsExclusiveDialogOpen] = useState(false);
    const [editingKey, setEditingKey] = useState<ExclusiveKey | null>(null);
    const [exclusiveForm, setExclusiveForm] = useState({
        name: '',
        is_active: true,
        preset_id: 'none',
        channel_id: 'none',
        enable_regex: false
    });

    // Selection State
    const [selectedExclusiveIds, setSelectedExclusiveIds] = useState<Set<number>>(new Set());

    const { toast } = useToast();

    // Fetch Data
    const fetchPresets = useCallback(async () => {
        const token = localStorage.getItem('token');
        try {
            const res = await axios.get<Preset[]>(`${API_BASE_URL}/presets/`, { headers: { Authorization: `Bearer ${token}` } });
            setPresets(res.data);
        } catch (error) {
            console.error('Failed to fetch presets', error);
        }
    }, []);

    const fetchChannels = useCallback(async () => {
        const token = localStorage.getItem('token');
        try {
            const res = await axios.get<Channel[]>(`${API_BASE_URL}/channels/`, { headers: { Authorization: `Bearer ${token}` } });
            setChannels(res.data);
        } catch (error) {
            console.error('Failed to fetch channels', error);
        }
    }, []);

    const fetchExclusiveKeys = useCallback(async (page = exclusiveData.page, size = exclusiveData.size, query = searchQuery) => {
        const token = localStorage.getItem('token');
        try {
            const res = await axios.get<PaginatedResponse<ExclusiveKey>>(`${API_BASE_URL}/keys/exclusive`, {
                headers: { Authorization: `Bearer ${token}` },
                params: { page, size, q: query }
            });
            setExclusiveData(res.data);
            setSelectedExclusiveIds(new Set());
        } catch (error) {
            console.error('Failed to fetch exclusive keys', error);
            toast({ variant: 'error', title: '加载专属密钥失败' });
        }
    }, [exclusiveData.page, exclusiveData.size, searchQuery, toast]);

    useEffect(() => {
        fetchPresets();
        fetchChannels();
        fetchExclusiveKeys(1, 10);
    }, []);

    // Debounced search for exclusive keys
    useEffect(() => {
        const timer = setTimeout(() => {
            fetchExclusiveKeys(1, exclusiveData.size, searchQuery);
        }, 500);
        return () => clearTimeout(timer);
    }, [searchQuery]);

    // Selection Logic
    const handleSelectAll = () => {
        if (selectedExclusiveIds.size === exclusiveData.items.length) {
            setSelectedExclusiveIds(new Set());
        } else {
            setSelectedExclusiveIds(new Set(exclusiveData.items.map(k => k.id)));
        }
    };

    const handleSelectInverse = () => {
        const newSet = new Set<number>();
        exclusiveData.items.forEach(k => {
            if (!selectedExclusiveIds.has(k.id)) newSet.add(k.id);
        });
        setSelectedExclusiveIds(newSet);
    };

    const handleSelectOne = (id: number) => {
        const newSet = new Set(selectedExclusiveIds);
        if (newSet.has(id)) newSet.delete(id);
        else newSet.add(id);
        setSelectedExclusiveIds(newSet);
    };

    // Batch Operations
    const handleBatchAction = async (action: 'enable' | 'disable' | 'delete') => {
        const ids = Array.from(selectedExclusiveIds);
        if (ids.length === 0) return;

        if (action === 'delete') {
            if (!await confirm({
                title: "批量删除",
                description: `确定要删除选中的 ${ids.length} 个密钥吗？此操作不可恢复。`,
                confirmText: "删除"
            })) return;
        }

        const token = localStorage.getItem('token');
        const headers = { Authorization: `Bearer ${token}` };
        let successCount = 0;
        let failCount = 0;

        const promises = ids.map(id => {
            const url = `${API_BASE_URL}/keys/exclusive/${id}`;
            if (action === 'delete') {
                return axios.delete(url, { headers });
            } else {
                return axios.patch(url, { is_active: action === 'enable' }, { headers });
            }
        });

        const results = await Promise.allSettled(promises);

        results.forEach(res => {
            if (res.status === 'fulfilled') successCount++;
            else failCount++;
        });

        if (successCount > 0) {
            toast({ variant: 'success', title: `成功${action === 'delete' ? '删除' : (action === 'enable' ? '启用' : '禁用')} ${successCount} 个密钥` });
        }
        if (failCount > 0) {
            toast({ variant: 'error', title: `${failCount} 个密钥操作失败` });
        }

        fetchExclusiveKeys(exclusiveData.page, exclusiveData.size);
        setSelectedExclusiveIds(new Set());
    };

    // Exclusive Key Actions
    const handleOpenExclusiveDialog = (key: ExclusiveKey | null = null) => {
        if (key) {
            setEditingKey(key);
            setExclusiveForm({
                name: key.name || '',
                is_active: key.is_active,
                preset_id: key.preset_id?.toString() || 'none',
                channel_id: key.channel_id?.toString() || 'none',
                enable_regex: key.enable_regex || false
            });
        } else {
            setEditingKey(null);
            setExclusiveForm({
                name: '',
                is_active: true,
                preset_id: 'none',
                channel_id: 'none',
                enable_regex: false
            });
        }
        setIsExclusiveDialogOpen(true);
    };

    const handleSaveExclusive = async (e: React.FormEvent) => {
        e.preventDefault();
        const token = localStorage.getItem('token');
        const headers = { Authorization: `Bearer ${token}` };

        const payload = {
            name: exclusiveForm.name,
            is_active: exclusiveForm.is_active,
            preset_id: exclusiveForm.preset_id === 'none' ? null : parseInt(exclusiveForm.preset_id),
            channel_id: exclusiveForm.channel_id === 'none' ? null : parseInt(exclusiveForm.channel_id),
            enable_regex: exclusiveForm.enable_regex
        };

        try {
            if (editingKey) {
                await axios.patch(`${API_BASE_URL}/keys/exclusive/${editingKey.id}`, payload, { headers });
                toast({ variant: 'success', title: '更新成功' });
            } else {
                await axios.post(`${API_BASE_URL}/keys/exclusive`, payload, { headers });
                toast({ variant: 'success', title: '创建成功' });
            }
            setIsExclusiveDialogOpen(false);
            fetchExclusiveKeys(exclusiveData.page, exclusiveData.size);
        } catch (error) {
            toast({ variant: 'error', title: editingKey ? '更新失败' : '创建失败' });
        }
    };

    const handleDeleteExclusive = async (id: number) => {
        if (!await confirm({ title: "删除密钥", description: "确定要删除此专属密钥吗？", confirmText: "删除" })) return;
        const token = localStorage.getItem('token');
        try {
            await axios.delete(`${API_BASE_URL}/keys/exclusive/${id}`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            fetchExclusiveKeys(exclusiveData.page, exclusiveData.size);
            toast({ variant: 'success', title: '删除成功' });
        } catch (error) {
            toast({ variant: 'error', title: '删除失败' });
        }
    };

    const handleUpdateExclusive = async (id: number, updates: Partial<ExclusiveKey>) => {
        const token = localStorage.getItem('token');
        try {
            await axios.patch(`${API_BASE_URL}/keys/exclusive/${id}`, updates, {
                headers: { Authorization: `Bearer ${token}` }
            });
            fetchExclusiveKeys(exclusiveData.page, exclusiveData.size);
            toast({ variant: 'success', title: '更新成功' });
        } catch (error) {
            toast({ variant: 'error', title: '更新失败' });
        }
    };

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text);
        toast({ title: '已复制到剪贴板' });
    };

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center gap-4">
                <div className="relative flex-1 max-w-md">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder="搜索密钥名称或 Key..."
                        className="pl-9"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                </div>
                <Button onClick={() => handleOpenExclusiveDialog()}>
                    <Plus className="w-4 h-4 mr-2" />
                    生成密钥
                </Button>
            </div>

            <Card>
                <CardContent className="p-0">
                    <div className="relative w-full overflow-x-auto">
                        <table className="w-full caption-bottom text-sm">
                            <thead className="[&_tr]:border-b">
                                <tr className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
                                    <th className="h-12 w-[50px] px-4 align-middle">
                                        <Checkbox
                                            checked={exclusiveData.items.length > 0 && selectedExclusiveIds.size === exclusiveData.items.length}
                                            onCheckedChange={handleSelectAll}
                                        />
                                    </th>
                                    <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">名称</th>
                                    <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">密钥</th>
                                    <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">绑定渠道</th>
                                    <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">绑定预设</th>
                                    <th className="h-12 px-4 text-center align-middle font-medium text-muted-foreground">启用正则</th>
                                    <th className="h-12 px-4 text-right align-middle font-medium text-muted-foreground"></th>
                                </tr>
                            </thead>
                            <tbody className="[&_tr:last-child]:border-0">
                                {exclusiveData.items.length === 0 ? (
                                    <tr>
                                        <td colSpan={7} className="p-8 text-center text-muted-foreground">
                                            <div className="flex flex-col items-center justify-center gap-2">
                                                <KeyIcon className="h-8 w-8 opacity-50" />
                                                <p>没有找到密钥</p>
                                            </div>
                                        </td>
                                    </tr>
                                ) : (
                                    exclusiveData.items.map((key) => (
                                        <tr key={key.id} className="border-b transition-colors hover:bg-muted/50 group">
                                            <td className="p-4 align-middle">
                                                <Checkbox
                                                    checked={selectedExclusiveIds.has(key.id)}
                                                    onCheckedChange={() => handleSelectOne(key.id)}
                                                />
                                            </td>
                                            <td className="p-4 align-middle font-medium">
                                                <div className="flex items-center gap-2">
                                                    <span>{key.name || '未命名'}</span>
                                                    <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => handleOpenExclusiveDialog(key)}>
                                                        <Pencil className="w-3 h-3" />
                                                    </Button>
                                                </div>
                                            </td>
                                            <td className="p-4 align-middle">
                                                <div className="flex items-center gap-2">
                                                    <MaskedKey apiKey={key.key} />
                                                    <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => copyToClipboard(key.key)}>
                                                        <Copy className="w-3 h-3" />
                                                    </Button>
                                                </div>
                                            </td>
                                            <td className="p-4 align-middle">
                                                <Select
                                                    value={key.channel_id?.toString() || "none"}
                                                    onValueChange={(val) => handleUpdateExclusive(key.id, { channel_id: val === "none" ? null : parseInt(val) })}
                                                >
                                                    <SelectTrigger className="w-[140px] h-8">
                                                        <SelectValue placeholder="选择渠道" />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        <SelectItem value="none">不绑定渠道</SelectItem>
                                                        {channels.map(c => (
                                                            <SelectItem key={c.id} value={c.id.toString()}>{c.name}</SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                            </td>
                                            <td className="p-4 align-middle">
                                                <Select
                                                    value={key.preset_id?.toString() || "none"}
                                                    onValueChange={(val) => handleUpdateExclusive(key.id, { preset_id: val === "none" ? null : parseInt(val) })}
                                                >
                                                    <SelectTrigger className="w-[140px] h-8">
                                                        <SelectValue placeholder="选择预设" />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        <SelectItem value="none">不使用预设</SelectItem>
                                                        {presets.map(p => (
                                                            <SelectItem key={p.id} value={p.id.toString()}>{p.name}</SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                            </td>
                                            <td className="p-4 align-middle">
                                                <div className="flex justify-center">
                                                    <Switch
                                                        checked={key.enable_regex}
                                                        onCheckedChange={(checked) => handleUpdateExclusive(key.id, { enable_regex: checked })}
                                                    />
                                                </div>
                                            </td>
                                            <td className="p-4 align-middle text-right">
                                                <div className="flex justify-end gap-2 items-center">
                                                    <Switch
                                                        checked={key.is_active}
                                                        onCheckedChange={(checked) => handleUpdateExclusive(key.id, { is_active: checked })}
                                                    />
                                                    <Button variant="ghost" size="icon" className="text-destructive opacity-0 group-hover:opacity-100 transition-opacity" onClick={() => handleDeleteExclusive(key.id)}>
                                                        <Trash2 className="w-4 h-4" />
                                                    </Button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </CardContent>
            </Card>

            <div className="flex justify-between items-center">
                <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" onClick={handleSelectInverse}>
                        反选
                    </Button>
                    {selectedExclusiveIds.size > 0 ? (
                        <>
                            <div className="h-4 w-[1px] bg-border mx-1" />
                            <span className="text-sm text-muted-foreground">已选择 {selectedExclusiveIds.size} 项</span>
                            <div className="h-4 w-[1px] bg-border mx-1" />
                            <Button variant="ghost" size="sm" onClick={() => handleBatchAction('enable')}>
                                启用
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleBatchAction('disable')}>
                                禁用
                            </Button>
                            <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive" onClick={() => handleBatchAction('delete')}>
                                删除
                            </Button>
                        </>
                    ) : null}
                </div>
                <Pagination
                    currentPage={exclusiveData.page}
                    totalPages={Math.ceil(exclusiveData.total / exclusiveData.size)}
                    pageSize={exclusiveData.size}
                    totalItems={exclusiveData.total}
                    onPageChange={(page) => fetchExclusiveKeys(page, exclusiveData.size)}
                    onPageSizeChange={(size) => fetchExclusiveKeys(1, size)}
                />
            </div>

            <Dialog open={isExclusiveDialogOpen} onOpenChange={setIsExclusiveDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>{editingKey ? '编辑密钥' : '生成密钥'}</DialogTitle>
                    </DialogHeader>
                    <form onSubmit={handleSaveExclusive} className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="ex-name">名称 (可选)</Label>
                            <Input
                                id="ex-name"
                                value={exclusiveForm.name}
                                onChange={(e) => setExclusiveForm({ ...exclusiveForm, name: e.target.value })}
                                placeholder="My App Key"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>绑定渠道</Label>
                            <Select
                                value={exclusiveForm.channel_id}
                                onValueChange={(val) => setExclusiveForm({ ...exclusiveForm, channel_id: val })}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder="选择渠道..." />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="none">不绑定渠道</SelectItem>
                                    {channels.map(c => (
                                        <SelectItem key={c.id} value={c.id.toString()}>{c.name}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-2">
                            <Label>绑定预设</Label>
                            <Select
                                value={exclusiveForm.preset_id}
                                onValueChange={(val) => setExclusiveForm({ ...exclusiveForm, preset_id: val })}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder="选择预设..." />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="none">不使用预设</SelectItem>
                                    {presets.map(p => (
                                        <SelectItem key={p.id} value={p.id.toString()}>{p.name}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="flex items-center justify-between">
                            <Label htmlFor="ex-regex">启用正则</Label>
                            <Switch
                                id="ex-regex"
                                checked={exclusiveForm.enable_regex}
                                onCheckedChange={(checked) => setExclusiveForm({ ...exclusiveForm, enable_regex: checked })}
                            />
                        </div>
                        <DialogFooter className="flex justify-between items-center sm:justify-between">
                            <div className="flex items-center gap-2">
                                <Switch
                                    id="ex-active"
                                    checked={exclusiveForm.is_active}
                                    onCheckedChange={(checked) => setExclusiveForm({ ...exclusiveForm, is_active: checked })}
                                />
                                <Label htmlFor="ex-active">启用</Label>
                            </div>
                            <Button type="submit">{editingKey ? '保存' : '生成'}</Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>
        </div>
    );
}
