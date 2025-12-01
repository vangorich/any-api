import { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '@/utils/api';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useToast } from '@/hooks/useToast';

interface CaptchaDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSuccess: (captchaId: string, captchaCode: string) => void;
}

export default function CaptchaDialog({ open, onOpenChange, onSuccess }: CaptchaDialogProps) {
    const [captchaId, setCaptchaId] = useState('');
    const [captchaCode, setCaptchaCode] = useState('');
    const [captchaUrl, setCaptchaUrl] = useState('');
    const [loading, setLoading] = useState(false);
    const { toast } = useToast();

    const fetchCaptcha = async () => {
        try {
            // 后端现在返回json，包含id和base64图片
            const response = await axios.get(`${API_BASE_URL}/captcha/generate`);
            const { captcha_id, image } = response.data;
            setCaptchaId(captcha_id);

            // Revoke old URL to prevent memory leaks
            if (captchaUrl) {
                URL.revokeObjectURL(captchaUrl);
            }
            // 将base64转换为可显示的URL
            setCaptchaUrl(`data:image/png;base64,${image}`);
        } catch (error) {
            console.error("Failed to fetch captcha", error);
            toast({ variant: 'error', title: '无法加载验证码' });
        }
    };

    useEffect(() => {
        if (open) {
            fetchCaptcha();
        }
        // Cleanup when component unmounts or dialog closes
        return () => {
            if (captchaUrl) {
                URL.revokeObjectURL(captchaUrl);
            }
        };
    }, [open]);

    const handleVerify = async () => {
        if (!captchaCode) {
            toast({ variant: 'error', title: '请输入验证码' });
            return;
        }
        setLoading(true);
        try {
            // 前端预验证
            await axios.post(`${API_BASE_URL}/captcha/verify`, {
                captcha_id: captchaId,
                captcha_code: captchaCode,
            });
            toast({ variant: 'success', title: '验证成功' });
            onSuccess(captchaId, captchaCode);
            onOpenChange(false); // 关闭弹窗
        } catch (error: any) {
            toast({
                variant: 'error',
                title: '验证码错误',
                description: error.response?.data?.detail || '请重试',
            });
            fetchCaptcha(); // 刷新验证码
        } finally {
            setLoading(false);
            setCaptchaCode('');
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>安全验证</DialogTitle>
                    <DialogDescription>
                        请输入下图中的字符以继续。
                    </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                    <div className="flex items-center gap-2">
                        <Input
                            id="captcha-code-dialog"
                            placeholder="输入验证码"
                            value={captchaCode}
                            onChange={(e) => setCaptchaCode(e.target.value)}
                            maxLength={4}
                            onKeyDown={(e) => e.key === 'Enter' && handleVerify()}
                            className="flex-1"
                        />
                        {captchaUrl && (
                            <img
                                src={captchaUrl}
                                onClick={fetchCaptcha}
                                className="cursor-pointer rounded-md h-10 w-28"
                                alt="Captcha"
                            />
                        )}
                    </div>
                </div>
                <DialogFooter>
                    <Button type="button" onClick={handleVerify} disabled={loading}>
                        {loading ? '验证中...' : '确认'}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}