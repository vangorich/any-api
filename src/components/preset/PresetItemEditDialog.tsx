import { useState, useEffect } from 'react';
import { Switch } from '@/components/ui/switch';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import type { PresetItem } from '@/services/presetService';

interface PresetItemEditDialogProps {
    item: PresetItem;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSave: (item: PresetItem) => void;
}

const roleOptions = [
    { value: 'system', label: '系统 (System)', icon: '🔧' },
    { value: 'user', label: '用户 (User)', icon: '👤' },
    { value: 'assistant', label: '助手 (Assistant)', icon: '🤖' },
];

const typeOptions = [
    { value: 'normal', label: '普通', description: '直接注入此条目' },
    { value: 'user_input', label: '用户输入', description: '插入最后一条用户消息' },
    { value: 'history', label: '历史', description: '插入历史对话（除最后一条用户消息）' },
];

export function PresetItemEditDialog({
    item,
    open,
    onOpenChange,
    onSave,
}: PresetItemEditDialogProps) {
    const [formData, setFormData] = useState<PresetItem>(item);

    // Sync formData when item prop changes
    useEffect(() => {
        setFormData(item);
    }, [item]);

    const handleSave = () => {
        onSave(formData);
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle className="text-2xl">编辑预设消息</DialogTitle>
                    <DialogDescription>
                        配置预设消息的角色、类型和内容。支持使用变量如 {'{'} roll 2d6 {'}'}, {'{'} random::A::B::C {'}'}
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-6 py-4">
                    {/* 消息名称 */}
                    <div className="space-y-2">
                        <Label htmlFor="name">消息名称</Label>
                        <Input
                            id="name"
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            placeholder="为此消息命名..."
                            onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                    e.preventDefault();
                                    handleSave();
                                }
                            }}
                        />
                    </div>

                    {/* 角色选择 - 使用Select下拉框并保留图标 */}
                    <div className="space-y-2">
                        <Label htmlFor="role">角色</Label>
                        <Select
                            value={formData.role}
                            onValueChange={(value) => setFormData({ ...formData, role: value as any })}
                        >
                            <SelectTrigger id="role">
                                <SelectValue>
                                    <div className="flex items-center gap-2">
                                        <span className="text-lg">
                                            {roleOptions.find(o => o.value === formData.role)?.icon}
                                        </span>
                                        <span>
                                            {roleOptions.find(o => o.value === formData.role)?.label}
                                        </span>
                                    </div>
                                </SelectValue>
                            </SelectTrigger>
                            <SelectContent>
                                {roleOptions.map((option) => (
                                    <SelectItem key={option.value} value={option.value}>
                                        <div className="flex items-center gap-2">
                                            <span className="text-lg">{option.icon}</span>
                                            <span>{option.label}</span>
                                        </div>
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    {/* 类型选择 - 使用Select下拉框 */}
                    <div className="space-y-2">
                        <Label htmlFor="type">类型</Label>
                        <Select
                            value={formData.type}
                            onValueChange={(value) => setFormData({ ...formData, type: value as any })}
                        >
                            <SelectTrigger id="type">
                                <SelectValue>
                                    {typeOptions.find(o => o.value === formData.type)?.label}
                                </SelectValue>
                            </SelectTrigger>
                            <SelectContent>
                                {typeOptions.map((option) => (
                                    <SelectItem key={option.value} value={option.value}>
                                        <div className="flex flex-col items-start">
                                            <span className="font-medium">{option.label}</span>
                                            <span className="text-xs text-muted-foreground">{option.description}</span>
                                        </div>
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    {/* 内容编辑 - 仅在类型为normal时显示 */}
                    {formData.type === 'normal' && (
                        <div className="space-y-2">
                            <Label htmlFor="content">内容</Label>
                            <Textarea
                                id="content"
                                value={formData.content}
                                onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                                className="min-h-[200px] font-mono text-sm"
                                placeholder="输入消息内容，支持变量如 {{roll 2d6}}, {{random::A::B}}, {{#注释}}..."
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                                        e.preventDefault();
                                        handleSave();
                                    }
                                }}
                            />
                            <div className="text-xs text-muted-foreground space-y-1">
                                <p>💡 <strong>可用变量：</strong></p>
                                <ul className="list-disc list-inside pl-2 space-y-0.5">
                                    <li><code className="text-xs bg-muted px-1 rounded">{'{{'} roll XdY {'}}'}</code> - 投掷骰子，例如 {'{{'} roll 2d6 {'}}'}</li>
                                    <li><code className="text-xs bg-muted px-1 rounded">{'{{'} random::A::B::C {'}}'}</code> - 随机选择</li>
                                    <li><code className="text-xs bg-muted px-1 rounded">{'{{'} setvar::name::value {'}}'}</code> - 设置变量</li>
                                    <li><code className="text-xs bg-muted px-1 rounded">{'{{'} getvar::name {'}}'}</code> - 获取变量</li>
                                    <li><code className="text-xs bg-muted px-1 rounded">{'{{'} #注释 {'}}'}</code> - 添加注释（将被移除）</li>
                                </ul>
                            </div>
                        </div>
                    )}

                    {/* 非normal类型的提示 */}
                    {formData.type !== 'normal' && (
                        <div className="p-4 bg-muted rounded-lg">
                            <p className="text-sm text-muted-foreground">
                                {formData.type === 'user_input' && '此类型会插入最后一条用户消息，无需填写内容'}
                                {formData.type === 'history' && '此类型会插入历史对话（除最后一条用户消息），无需填写内容'}
                            </p>
                        </div>
                    )}
                </div>

                <DialogFooter className="sm:justify-between">
                    <div className="flex items-center gap-2">
                        <Switch
                            id="item-enabled"
                            checked={formData.enabled !== false}
                            onCheckedChange={(checked) => setFormData({ ...formData, enabled: checked })}
                        />
                        <Label htmlFor="item-enabled" className="cursor-pointer">启用此消息</Label>
                    </div>
                    <div className="flex gap-2">
                        <Button variant="outline" onClick={() => onOpenChange(false)}>
                            取消
                        </Button>
                        <Button onClick={handleSave}>保存</Button>
                    </div>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
