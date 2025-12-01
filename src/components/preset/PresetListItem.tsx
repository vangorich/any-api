import { useState } from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical, Pencil, Trash2, Copy } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { confirm } from '@/components/ui/ConfirmDialog';
import type { Preset } from '@/services/presetService';

interface PresetListItemProps {
    preset: Preset;
    isSelected: boolean;
    onSelect: () => void;
    onToggleActive: (id: number, isActive: boolean) => void;
    onRename: (id: number, newName: string) => void;
    onDelete: (id: number) => void;
    onDuplicate: (preset: Preset) => void;
}

export function PresetListItem({
    preset,
    isSelected,
    onSelect,
    onToggleActive,
    onRename,
    onDelete,
    onDuplicate,
}: PresetListItemProps) {
    const [isEditing, setIsEditing] = useState(false);
    const [editName, setEditName] = useState(preset.name);

    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging,
    } = useSortable({ id: preset.id });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
    };

    const handleRename = () => {
        if (editName.trim() && editName !== preset.name) {
            onRename(preset.id, editName.trim());
        }
        setIsEditing(false);
    };

    return (
        <div
            ref={setNodeRef}
            style={style}
            className={cn(
                "flex items-center gap-2 p-3 rounded-md border transition-colors cursor-pointer group",
                isSelected ? "bg-primary/10 border-primary" : "hover:bg-accent/50",
                isDragging && "shadow-lg ring-2 ring-primary"
            )}
            onClick={onSelect}
        >
            {/* 拖动手柄 */}
            <div
                {...attributes}
                {...listeners}
                className="cursor-grab active:cursor-grabbing opacity-50 hover:opacity-100"
                onClick={(e) => e.stopPropagation()}
            >
                <GripVertical className="w-4 h-4" />
            </div>

            {/* 预设名称 */}
            <div className="flex-1 min-w-0">
                {isEditing ? (
                    <Input
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        onBlur={handleRename}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter') handleRename();
                            if (e.key === 'Escape') setIsEditing(false);
                        }}
                        className="h-7 text-sm"
                        onClick={(e) => e.stopPropagation()}
                        autoFocus
                    />
                ) : (
                    <span className="text-sm font-medium truncate block">
                        {preset.name}
                    </span>
                )}
            </div>

            {/* 操作按钮 */}
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100">
                <Switch
                    checked={preset.is_active}
                    onCheckedChange={(checked) => onToggleActive(preset.id, checked)}
                    onClick={(e) => e.stopPropagation()}
                />
                <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={(e) => {
                        e.stopPropagation();
                        setIsEditing(true);
                    }}
                >
                    <Pencil className="w-3 h-3" />
                </Button>
                <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={(e) => {
                        e.stopPropagation();
                        onDuplicate(preset);
                    }}
                >
                    <Copy className="w-3 h-3" />
                </Button>
                <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 text-destructive"
                    onClick={async (e) => {
                        e.stopPropagation();
                        if (await confirm({ title: "删除预设项", description: "确定要删除这个预设项吗？", confirmText: "删除" })) {
                            onDelete(preset.id);
                        }
                    }}
                >
                    <Trash2 className="w-3 h-3" />
                </Button>
            </div>
        </div>
    );
}
