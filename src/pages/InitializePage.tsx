import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useSystem } from '@/contexts/SystemContext';
import { API_BASE_URL } from '@/utils/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/useToast';
import { User, Lock, Database, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

type SetupStep = 'database' | 'admin' | 'initializing' | 'complete';

export default function InitializePage() {
    const [currentStep, setCurrentStep] = useState<SetupStep>('database');
    const [databaseType, setDatabaseType] = useState<string>('');
    const [username, setUsername] = useState('admin');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [passwordMatch, setPasswordMatch] = useState(true);
    const navigate = useNavigate();
    const { toast } = useToast();
    const { config: systemConfig } = useSystem();

    // 检查初始化状态
    useEffect(() => {
        const checkStatus = async () => {
            try {
                const response = await axios.get(`${API_BASE_URL}/setup/status`);
                const { needs_setup, database_type } = response.data;

                setDatabaseType(database_type);

                // 如果不需要初始化,重定向到登录页
                if (!needs_setup) {
                    navigate('/login');
                    return;
                }

                // 如果不是 SQLite,跳过数据库确认步骤
                if (database_type !== 'sqlite') {
                    setCurrentStep('admin');
                }
            } catch (error) {
                console.error('Failed to check setup status:', error);
            }
        };

        checkStatus();
    }, [navigate]);

    // 检查密码匹配
    useEffect(() => {
        if (confirmPassword) {
            setPasswordMatch(password === confirmPassword);
        } else {
            setPasswordMatch(true);
        }
    }, [password, confirmPassword]);

    // 处理数据库确认
    const handleDatabaseConfirm = () => {
        setCurrentStep('admin');
    };

    // 处理初始化
    const handleInitialize = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!passwordMatch) {
            toast({
                variant: 'error',
                title: '密码不匹配',
                description: '请确保两次输入的密码一致',
            });
            return;
        }

        if (password.length < 6) {
            toast({
                variant: 'error',
                title: '密码太短',
                description: '密码长度至少为 6 位',
            });
            return;
        }

        setLoading(true);
        setCurrentStep('initializing');

        try {
            const response = await axios.post(`${API_BASE_URL}/setup/initialize`, {
                username,
                password,
                confirm_password: confirmPassword,
                database_confirmed: true,
            });

            if (response.data.status === 'success') {
                setCurrentStep('complete');
                toast({
                    variant: 'success',
                    title: '初始化成功',
                    description: '系统已完成初始化,请使用管理员账户登录',
                });
            }
        } catch (error: any) {
            setCurrentStep('admin');
            toast({
                variant: 'error',
                title: '初始化失败',
                description: error.response?.data?.detail || '系统初始化失败,请重试',
            });
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary/10 via-background to-secondary/10 p-4">
            <div className="bg-card border rounded-xl shadow-2xl w-full max-w-2xl overflow-hidden">
                {/* 标题区域 */}
                <div className="bg-gradient-to-r from-primary to-primary/80 text-primary-foreground p-8 text-center">
                    <h1 className="text-3xl font-bold mb-2">{systemConfig?.site_name || 'Any API'} 系统初始化</h1>
                    <p className="text-sm opacity-90">
                        欢迎使用 {systemConfig?.site_name || 'Any API'}, 请完成初始化设置
                    </p>
                </div>

                {/* 内容区域 */}
                <div className="p-8">
                    {/* 步骤 1: 数据库确认 */}
                    {currentStep === 'database' && (
                        <div className="space-y-6">
                            <div className="flex items-center gap-3 mb-4">
                                <div className="w-12 h-12 rounded-full bg-blue-500/10 flex items-center justify-center">
                                    <Database className="w-6 h-6 text-blue-500" />
                                </div>
                                <div>
                                    <h2 className="text-xl font-semibold">数据库配置确认</h2>
                                    <p className="text-sm text-muted-foreground">步骤 1/2</p>
                                </div>
                            </div>

                            <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4">
                                <div className="flex gap-3">
                                    <AlertCircle className="w-5 h-5 text-yellow-500 shrink-0 mt-0.5" />
                                    <div className="space-y-2">
                                        <p className="font-medium text-yellow-700 dark:text-yellow-500">
                                            检测到 SQLite 数据库
                                        </p>
                                        <p className="text-sm text-muted-foreground">
                                            您当前使用的是 <span className="font-mono font-semibold">{databaseType}</span> 数据库。
                                            SQLite 适合小规模部署和测试环境,但不推荐用于生产环境。
                                        </p>
                                        <p className="text-sm text-muted-foreground">
                                            如需在生产环境中使用,建议配置 PostgreSQL 或 MySQL 数据库。
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <div className="flex gap-3 justify-end">
                                <Button
                                    onClick={handleDatabaseConfirm}
                                    className="w-full sm:w-auto"
                                >
                                    我了解,继续使用
                                </Button>
                            </div>
                        </div>
                    )}

                    {/* 步骤 2: 管理员账户创建 */}
                    {currentStep === 'admin' && (
                        <div className="space-y-6">
                            <div className="flex items-center gap-3 mb-4">
                                <div className="w-12 h-12 rounded-full bg-green-500/10 flex items-center justify-center">
                                    <User className="w-6 h-6 text-green-500" />
                                </div>
                                <div>
                                    <h2 className="text-xl font-semibold">创建管理员账户</h2>
                                    <p className="text-sm text-muted-foreground">
                                        {databaseType === 'sqlite' ? '步骤 2/2' : '步骤 1/1'}
                                    </p>
                                </div>
                            </div>

                            <form onSubmit={handleInitialize} className="space-y-4">
                                <div className="space-y-2">
                                    <Label htmlFor="username">用户名</Label>
                                    <div className="relative">
                                        <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                                        <Input
                                            id="username"
                                            type="text"
                                            placeholder="输入管理员用户名"
                                            value={username}
                                            onChange={(e) => setUsername(e.target.value)}
                                            className="pl-10"
                                            required
                                            minLength={4}
                                            pattern="^[a-zA-Z0-9]+$"
                                            onInvalid={(e) => {
                                                const target = e.target as HTMLInputElement;
                                                if (target.value.length < 4) {
                                                    target.setCustomValidity('用户名长度不能少于4位');
                                                } else {
                                                    target.setCustomValidity('用户名只能包含字母和数字');
                                                }
                                            }}
                                            onInput={(e) => (e.target as HTMLInputElement).setCustomValidity('')}
                                        />
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="password">密码</Label>
                                    <div className="relative">
                                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                                        <Input
                                            id="password"
                                            type="password"
                                            placeholder="输入密码(至少 6 位)"
                                            value={password}
                                            onChange={(e) => setPassword(e.target.value)}
                                            className="pl-10"
                                            required
                                            minLength={6}
                                        />
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="confirm-password">确认密码</Label>
                                    <div className="relative">
                                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                                        <Input
                                            id="confirm-password"
                                            type="password"
                                            placeholder="再次输入密码"
                                            value={confirmPassword}
                                            onChange={(e) => setConfirmPassword(e.target.value)}
                                            className={`pl-10 ${!passwordMatch ? 'border-red-500' : ''}`}
                                            required
                                        />
                                    </div>
                                    {!passwordMatch && confirmPassword && (
                                        <p className="text-sm text-red-500">密码不匹配</p>
                                    )}
                                </div>

                                <Button type="submit" className="w-full" disabled={loading || !passwordMatch}>
                                    {loading ? '创建中...' : '创建管理员账户'}
                                </Button>
                            </form>
                        </div>
                    )}

                    {/* 步骤 3: 初始化进行中 */}
                    {currentStep === 'initializing' && (
                        <div className="space-y-6 text-center py-8">
                            <div className="flex justify-center">
                                <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
                                    <Loader2 className="w-8 h-8 text-primary animate-spin" />
                                </div>
                            </div>
                            <div>
                                <h2 className="text-xl font-semibold mb-2">正在初始化系统</h2>
                                <p className="text-sm text-muted-foreground">
                                    请稍候,系统正在初始化数据库和配置...
                                </p>
                            </div>
                        </div>
                    )}

                    {/* 步骤 4: 完成 */}
                    {currentStep === 'complete' && (
                        <div className="space-y-6 text-center py-8">
                            <div className="flex justify-center">
                                <div className="w-16 h-16 rounded-full bg-green-500/10 flex items-center justify-center">
                                    <CheckCircle className="w-8 h-8 text-green-500" />
                                </div>
                            </div>
                            <div>
                                <h2 className="text-xl font-semibold mb-2">初始化完成!</h2>
                                <p className="text-sm text-muted-foreground mb-1">
                                    系统已成功初始化,管理员账户已创建。
                                </p>
                                <p className="text-sm text-muted-foreground">
                                    请使用您创建的账户登录系统。
                                </p>
                            </div>
                            <Button onClick={() => navigate('/login')} className="w-full sm:w-auto">
                                前往登录
                            </Button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
