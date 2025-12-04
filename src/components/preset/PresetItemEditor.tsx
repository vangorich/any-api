import { useState, useEffect } from 'react';
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors, DragEndEvent } from '@dnd-kit/core';
import { arrayMove, SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { Plus, Download, Upload } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { PresetItemRow } from './PresetItemRow';
import { PresetItemEditDialog } from './PresetItemEditDialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import type { Preset, PresetItem } from '@/services/presetService';
import { presetService } from '@/services/presetService';
import { format } from 'date-fns';
import { toZonedTime } from 'date-fns-tz';
import { useToast } from '@/hooks/useToast';
import { exportToJSON, importFromJSON } from '@/utils/exportImport';

interface PresetItemEditorProps {
    preset: Preset;
    onItemsChange: () => void;
}

export function PresetItemEditor({ preset, onItemsChange }: PresetItemEditorProps) {
    const [editingItem, setEditingItem] = useState<PresetItem | Partial<PresetItem> | null>(null);
    const [isDialogOpen, setIsDialogOpen] = useState(false);
    const [items, setItems] = useState<PresetItem[]>([]);
    const [isSyncing, setIsSyncing] = useState(false);
    const { toast } = useToast();

    const sensors = useSensors(
        useSensor(PointerSensor),
        useSensor(KeyboardSensor)
    );

    // 同步preset.items到本地状态
    useEffect(() => {
        setItems(preset.items || []);
    }, [preset.id, preset.items]);

    const handleDragEnd = async (event: DragEndEvent) => {
        const { active, over } = event;
        if (over && active.id !== over.id) {
            const oldIndex = items.findIndex((item) => item.id === active.id);
            const newIndex = items.findIndex((item) => item.id === over.id);
            const newItems = arrayMove(items, oldIndex, newIndex);

            // 立即更新本地状态（真正的乐观更新，不刷新页面）
            setItems(newItems);

            try {
                // 后台异步更新排序
                await Promise.all(newItems.map(
                    (item, index) =>
                        presetService.updatePresetItem(preset.id, item.id, { sort_order: index })
                ));
                // 不再同步 Preset.content，只更新 PresetItem 表
            } catch (error) {
                toast({ variant: 'error', title: '排序失败' });
                // 失败时恢复原状态
                setItems(preset.items || []);
            }
        }
    };

    const handleAddItem = () => {
        const newItem: Partial<PresetItem> = {
            role: 'system',
            type: 'normal',
            name: '新建条目',
            content: '',
            sort_order: items.length,
            enabled: true,
        };
        setEditingItem(newItem);
        setIsDialogOpen(true);
    };

    const handleEditItem = (item: PresetItem) => {
        setEditingItem(item);
        setIsDialogOpen(true);
    };

    /**
     * 修改说明（第3步）：
     * - 移除了 updatePresetContent 方法
     * - 现在只直接操作 PresetItem 表
     * - 不再维护 Preset.content 的双重存储
     * - 这确保了数据一致性，避免同步问题
     */
    const handleSaveItem = async (item: PresetItem | Partial<PresetItem>) => {
        try {
            let newOrUpdatedItem: PresetItem;
            if ('id' in item && item.id) {
                // Update existing item
                newOrUpdatedItem = await presetService.updatePresetItem(preset.id, item.id, item);
                const updatedItems = items.map(i => i.id === newOrUpdatedItem.id ? newOrUpdatedItem : i);
                setItems(updatedItems);
            } else {
                // Create new item
                newOrUpdatedItem = await presetService.createPresetItem(preset.id, item as any);
                const updatedItems = [...items, newOrUpdatedItem];
                setItems(updatedItems);
            }

            setIsDialogOpen(false);
            setEditingItem(null);
            toast({ variant: 'success', title: '保存成功' });
        } catch (error) {
            toast({ variant: 'error', title: '保存失败' });
        }
    };

    const handleDeleteItem = async (itemId: number) => {
        try {
            await presetService.deletePresetItem(preset.id, itemId);
            const updatedItems = items.filter(i => i.id !== itemId);
            setItems(updatedItems); // Optimistic update locally
            toast({ variant: 'success', title: '删除成功' });
        } catch (error) {
            toast({ variant: 'error', title: '删除失败' });
            onItemsChange(); // Revert on failure
        }
    };

    const handleDuplicateItem = async (item: PresetItem) => {
        try {
            const newItem = await presetService.createPresetItem(preset.id, {
                ...item,
                name: `${item.name} (副本)`,
                sort_order: items.length,
            });
            const updatedItems = [...items, newItem];
            setItems(updatedItems);
            toast({ variant: 'success', title: '复制成功' });
        } catch (error) {
            toast({ variant: 'error', title: '复制失败' });
        }
    };

    const handleToggleEnabled = async (item: PresetItem, enabled: boolean) => {
        try {
            await presetService.updatePresetItem(preset.id, item.id, { enabled });
            const updatedItems = items.map(i => i.id === item.id ? { ...i, enabled } : i);
            setItems(updatedItems);
        } catch (error) {
            toast({ variant: 'error', title: '更新失败' });
            onItemsChange(); // Revert on failure
        }
    };

    const handleExportItems = () => {
        const presetItems = items.map((item) => ({
            name: item.name,
            creator_username: item.creator_username || 'unknown',
            created_at: format(toZonedTime(new Date(item.created_at), 'Asia/Shanghai'), 'yyyy-MM-dd HH:mm:ss'),
            updated_at: format(toZonedTime(new Date(item.updated_at), 'Asia/Shanghai'), 'yyyy-MM-dd HH:mm:ss'),
            enabled: item.enabled,
            role: item.role,
            type: item.type,
            content: item.content,
        }));

        const exportData = {
            name: preset.name,
            type: 'preset',
            creator_username: (preset as any).creator_username || 'unknown',
            created_at: format(toZonedTime(new Date(preset.created_at), 'Asia/Shanghai'), 'yyyy-MM-dd HH:mm:ss'),
            updated_at: format(toZonedTime(new Date(preset.updated_at), 'Asia/Shanghai'), 'yyyy-MM-dd HH:mm:ss'),
            enabled: preset.is_active,
            content: {
                preset: presetItems,
                regex: [],
            }
        };

        exportToJSON(exportData, `gproxy-preset-items-${preset.name}`);
        toast({
            variant: 'success',
            title: '导出成功',
            description: `成功导出 ${items.length} 个条目`,
        });
    };

    const handleImportItems = async () => {
        try {
            setIsSyncing(true);
            const importedData = await importFromJSON<any>();
            let itemsToImport = [];

            // Handle both array of items and full preset object
            if (Array.isArray(importedData)) {
                itemsToImport = importedData;
            } else if (importedData.type === 'preset' && importedData.content && Array.isArray(importedData.content.preset)) {
                itemsToImport = importedData.content.preset;
            } else {
                throw new Error('文件格式不兼容');
            }

            // 批量导入预设项
            const createdItems: PresetItem[] = [];
            for (const item of itemsToImport) {
                const createdItem = await presetService.createPresetItem(preset.id, {
                    name: item.name,
                    role: item.role,
                    type: item.type,
                    content: item.content,
                    enabled: item.enabled,
                    sort_order: items.length + itemsToImport.indexOf(item),
                });
                createdItems.push(createdItem);
            }

            // 更新本地状态
            setItems([...items, ...createdItems]);
            
            toast({
                variant: 'success',
                title: '导入成功',
                description: `成功导入 ${itemsToImport.length} 个条目`,
            });
        } catch (error) {
            toast({
                variant: 'error',
                title: '导入失败',
                description: error instanceof Error ? error.message : '未知错误',
            });
        } finally {
            setIsSyncing(false);
        }
    };

    return (
        <div className="flex flex-col h-full">
            {/* 头部 */}
            <div className="p-4 border-b">
                <div className="flex items-center justify-between">
                    <div>
                        <h2 className="text-lg font-semibold">预设内部条目</h2>
                        <p className="text-sm text-muted-foreground mt-1">
                            当前共 {items.length} 个条目
                        </p>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button 
                            onClick={handleExportItems} 
                            variant="outline" 
                            size="sm" 
                            disabled={items.length === 0}
                        >
                            <Download className="w-4 h-4 mr-2" />
                            导出
                        </Button>
                        <Button 
                            onClick={handleImportItems} 
                            variant="outline" 
                            size="sm"
                            disabled={isSyncing}
                        >
                            <Upload className="w-4 h-4 mr-2" />
                            {isSyncing ? '导入中...' : '导入'}
                        </Button>
                        <Button onClick={handleAddItem} size="sm">
                            <Plus className="w-4 h-4 mr-2" />
                            添加条目
                        </Button>
                    </div>
                </div>
            </div>

            {/* 条目列表 */}
            <ScrollArea className="flex-1 p-4">
                {items.length === 0 ? (
                    <div className="text-center text-muted-foreground py-8">
                        <p className="text-sm">暂无条目</p>
                        <p className="text-xs mt-1">点击"添加条目"创建第一条条目</p>
                    </div>
                ) : (
                    <DndContext
                        sensors={sensors}
                        collisionDetection={closestCenter}
                        onDragEnd={handleDragEnd}
                    >
                        <SortableContext
                            items={items.map((item) => item.id)}
                            strategy={verticalListSortingStrategy}
                        >
                            <div className="space-y-2">
                                {items.map((item) => (
                                    <PresetItemRow
                                        key={item.id}
                                        item={item}
                                        onEdit={handleEditItem}
                                        onDelete={() => handleDeleteItem(item.id)}
                                        onDuplicate={handleDuplicateItem}
                                        onToggle={handleToggleEnabled}
                                    />
                                ))}
                            </div>
                        </SortableContext>
                    </DndContext>
                )}
            </ScrollArea>

            {/* 编辑对话框 */}
            {editingItem && (
                <PresetItemEditDialog
                    item={editingItem as PresetItem}
                    open={isDialogOpen}
                    onOpenChange={setIsDialogOpen}
                    onSave={handleSaveItem}
                />
            )}
        </div>
    );
}
