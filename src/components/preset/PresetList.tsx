import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors, DragEndEvent } from '@dnd-kit/core';
import { arrayMove, SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { Plus, Download, Upload } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { PresetListItem } from './PresetListItem';
import { ScrollArea } from '@/components/ui/scroll-area';
import type { Preset } from '@/services/presetService';

interface PresetListProps {
    presets: Preset[];
    selectedPresetId: number | null;
    onSelectPreset: (preset: Preset) => void;
    onCreatePreset: () => void;
    onUpdatePresets: (presets: Preset[]) => void;
    onToggleActive: (id: number, isActive: boolean) => void;
    onRename: (id: number, newName: string) => void;
    onDelete: (id: number) => void;
    onDuplicate: (preset: Preset) => void;
    onExport: () => void;
    onImport: () => void;
}

export function PresetList({
    presets,
    selectedPresetId,
    onSelectPreset,
    onCreatePreset,
    onUpdatePresets,
    onToggleActive,
    onRename,
    onDelete,
    onDuplicate,
    onExport,
    onImport,
}: PresetListProps) {
    const sensors = useSensors(
        useSensor(PointerSensor),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    const handleDragEnd = (event: DragEndEvent) => {
        const { active, over } = event;

        if (over && active.id !== over.id) {
            const oldIndex = presets.findIndex((p) => p.id === active.id);
            const newIndex = presets.findIndex((p) => p.id === over.id);

            const newPresets = arrayMove(presets, oldIndex, newIndex).map((p, index) => ({
                ...p,
                sort_order: index,
            }));

            onUpdatePresets(newPresets);
        }
    };

    return (
        <div className="flex flex-col h-full border-r bg-card">
            {/* 头部操作栏 */}
            <div className="p-4 border-b space-y-2">
                <h2 className="text-lg font-semibold">预设列表</h2>
                <div className="flex gap-2">
                    <Button onClick={onCreatePreset} size="sm" className="flex-1">
                        <Plus className="w-4 h-4 mr-1" />
                        新建
                    </Button>
                    <Button onClick={onExport} size="sm" variant="outline">
                        <Download className="w-4 h-4" />
                    </Button>
                    <Button onClick={onImport} size="sm" variant="outline">
                        <Upload className="w-4 h-4" />
                    </Button>
                </div>
            </div>

            {/* 预设列表 */}
            <ScrollArea className="flex-1 p-4">
                {presets.length === 0 ? (
                    <div className="text-center text-muted-foreground py-8">
                        <p className="text-sm">暂无预设</p>
                        <p className="text-xs mt-1">点击"新建"创建第一个预设</p>
                    </div>
                ) : (
                    <DndContext
                        sensors={sensors}
                        collisionDetection={closestCenter}
                        onDragEnd={handleDragEnd}
                    >
                        <SortableContext
                            items={presets.map((p) => p.id)}
                            strategy={verticalListSortingStrategy}
                        >
                            <div className="space-y-2">
                                {presets.map((preset) => (
                                    <PresetListItem
                                        key={preset.id}
                                        preset={preset}
                                        isSelected={preset.id === selectedPresetId}
                                        onSelect={() => onSelectPreset(preset)}
                                        onToggleActive={onToggleActive}
                                        onRename={onRename}
                                        onDelete={onDelete}
                                        onDuplicate={onDuplicate}
                                    />
                                ))}
                            </div>
                        </SortableContext>
                    </DndContext>
                )}
            </ScrollArea>
        </div>
    );
}
