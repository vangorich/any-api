import { create } from 'zustand';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { useEffect, useState } from 'react';

interface ConfirmDialogState {
    isOpen: boolean;
    title: string;
    description: React.ReactNode;
    confirmText: string;
    cancelText: string;
    onConfirm: () => void;
    onCancel: () => void;
    
    // Actions
    ask: (props: {
        title: string;
        description: React.ReactNode;
        confirmText?: string;
        cancelText?: string;
        onConfirm?: () => void;
        onCancel?: () => void;
    }) => Promise<boolean>;
    close: () => void;
}

const useConfirmStore = create<ConfirmDialogState>((set) => ({
    isOpen: false,
    title: '',
    description: '',
    confirmText: '确定',
    cancelText: '取消',
    onConfirm: () => {},
    onCancel: () => {},

    ask: ({ title, description, confirmText = '确定', cancelText = '取消', onConfirm, onCancel }) => {
        return new Promise<boolean>((resolve) => {
            set({
                isOpen: true,
                title,
                description,
                confirmText,
                cancelText,
                onConfirm: () => {
                    set({ isOpen: false });
                    if (onConfirm) onConfirm();
                    resolve(true);
                },
                onCancel: () => {
                    set({ isOpen: false });
                    if (onCancel) onCancel();
                    resolve(false);
                },
            });
        });
    },
    close: () => set({ isOpen: false }),
}));

export const confirm = (props: {
    title: string;
    description: React.ReactNode;
    confirmText?: string;
    cancelText?: string;
}) => useConfirmStore.getState().ask(props);

export function ConfirmDialog() {
    // 解决 hydration 问题，确保组件只在客户端挂载后渲染
    const [isMounted, setIsMounted] = useState(false);
    
    useEffect(() => {
        setIsMounted(true);
    }, []);

    const { isOpen, title, description, confirmText, cancelText, onConfirm, onCancel, close } = useConfirmStore();

    if (!isMounted) return null;

    return (
        <Dialog open={isOpen} onOpenChange={(open) => !open && onCancel()}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>{title}</DialogTitle>
                    <DialogDescription>
                        {description}
                    </DialogDescription>
                </DialogHeader>
                <DialogFooter>
                    <Button variant="outline" onClick={onCancel}>
                        {cancelText}
                    </Button>
                    <Button onClick={onConfirm}>
                        {confirmText}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}