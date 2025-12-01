import { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '@/utils/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';

export default function ProfilePage() {
    const [user, setUser] = useState<any>(null);
    const [oldPassword, setOldPassword] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [email, setEmail] = useState('');
    const [message, setMessage] = useState('');

    useEffect(() => {
        const fetchUser = async () => {
            const token = localStorage.getItem('token');
            try {
                const response = await axios.get(`${API_BASE_URL}/users/me`, {
                    headers: { Authorization: `Bearer ${token}` }
                });
                setUser(response.data);
                setEmail(response.data.email);
            } catch (error) {
                console.error('Failed to fetch user', error);
            }
        };
        fetchUser();
    }, []);

    const handleUpdate = async (e: React.FormEvent) => {
        e.preventDefault();
        setMessage('');
        const token = localStorage.getItem('token');

        const updatePayload: { old_password?: string; password?: string; } = {};

        // Only proceed if any password field is touched
        if (password || oldPassword || confirmPassword) {
            if (!oldPassword) {
                setMessage('请输入旧密码');
                return;
            }
            if (password !== confirmPassword) {
                setMessage('新密码和确认密码不匹配');
                return;
            }
            if (!password) {
                setMessage('请输入新密码');
                return;
            }
            updatePayload.old_password = oldPassword;
            updatePayload.password = password;
        } else {
            setMessage('没有需要更新的资料');
            return;
        }

        try {
            await axios.put(`${API_BASE_URL}/users/me`,
                updatePayload,
                { headers: { Authorization: `Bearer ${token}` } }
            );
            setMessage('资料已成功更新');
            setOldPassword('');
            setPassword('');
            setConfirmPassword('');
        } catch (error: any) {
            const errorMessage = error.response?.data?.detail || '更新资料失败';
            setMessage(errorMessage);
        }
    };

    const getRoleDisplayName = (role: string) => {
        const roleMap: Record<string, string> = {
            'user': '用户',
            'admin': '管理员',
            'super_admin': '超级管理员'
        };
        return roleMap[role] || role;
    };

    if (!user) return <div>加载中...</div>;

    return (
        <div className="max-w-2xl space-y-8">
            <div className="bg-card border rounded-lg p-6 space-y-6">
                <h2 className="text-xl font-semibold">资料设置</h2>

                {message && (
                    <div className={cn("p-3 rounded text-sm", message.includes('成功') ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800")}>
                        {message}
                    </div>
                )}

                <div className="space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="username">用户名</Label>
                        <Input id="username" value={user.username} disabled className="bg-muted" />
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="user-id">用户ID</Label>
                        <Input id="user-id" value={user.id} disabled className="bg-muted" />
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="user-role">用户权限</Label>
                        <Input id="user-role" value={getRoleDisplayName(user.role)} disabled className="bg-muted" />
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="email">邮箱</Label>
                        <Input
                            id="email"
                            type="email"
                            value={email}
                            disabled
                            className="bg-muted"
                        />
                    </div>
                </div>
            </div>

            <div className="bg-card border rounded-lg p-6 space-y-6">
                <h2 className="text-xl font-semibold">修改密码</h2>
                <form onSubmit={handleUpdate} className="space-y-4">
                    <div className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="old-password">旧密码</Label>
                            <Input
                                id="old-password"
                                type="password"
                                value={oldPassword}
                                onChange={(e) => setOldPassword(e.target.value)}
                                placeholder="修改密码时需要输入旧密码"
                                required={!!(password || confirmPassword)}
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="password">新密码</Label>
                            <Input
                                id="password"
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="输入新密码（至少6位）"
                                minLength={6}
                                pattern="^(?!\d+$).{6,}$"
                                onInvalid={(e) => {
                                    const target = e.target as HTMLInputElement;
                                    if (target.value.length > 0 && target.value.length < 6) {
                                        target.setCustomValidity('密码长度不能少于6位');
                                    } else if (target.value.match(/^\d+$/)) {
                                        target.setCustomValidity('密码不能为纯数字');
                                    } else {
                                        target.setCustomValidity('');
                                    }
                                }}
                                onInput={(e) => (e.target as HTMLInputElement).setCustomValidity('')}
                                required={!!(oldPassword || confirmPassword)}
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="confirm-password">确认新密码</Label>
                            <Input
                                id="confirm-password"
                                type="password"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                placeholder="再次输入新密码"
                                minLength={6}
                                required={!!(oldPassword || password)}
                            />
                        </div>
                    </div>

                    <Button type="submit">更新资料</Button>
                </form>
            </div>
        </div>
    );
}