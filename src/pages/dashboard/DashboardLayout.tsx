import { useState } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import {
    LayoutDashboard,
    FileJson,
    Regex,
    Key,
    ScrollText,
    Settings,
    Users,
    LogOut,
    Menu,
    X
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/contexts/AuthContext';
import { useSystem } from '@/contexts/SystemContext';

export default function DashboardLayout() {
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    const location = useLocation();
    const navigate = useNavigate();
    const { currentUser, loading, logout } = useAuth();
    const { config: systemConfig } = useSystem();

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    const navItems = [
        { icon: LayoutDashboard, label: '概览', path: '/dashboard' },
        { icon: FileJson, label: '预设', path: '/dashboard/presets' },
        { icon: Regex, label: '正则', path: '/dashboard/regex' },
        { icon: Key, label: '密钥', path: '/dashboard/keys' },
        { icon: Settings, label: '渠道', path: '/dashboard/channels' },
        { icon: ScrollText, label: '日志', path: '/dashboard/logs' },
        { icon: Settings, label: '资料', path: '/dashboard/profile' },
        { icon: Users, label: '用户', path: '/dashboard/users', allowedRoles: ['admin', 'super_admin'] },
        { icon: Settings, label: '系统', path: '/dashboard/system', allowedRoles: ['super_admin'] },
    ];

    const filteredNavItems = navItems.filter(item => {
        if (!item.allowedRoles) {
            return true; // 没有权限要求的菜单项，所有人都可见
        }
        if (!currentUser) {
            return false; // 用户未登录，不可见
        }
        return item.allowedRoles.includes(currentUser.role);
    });

    if (loading) {
        return <div>加载中...</div>; // 或者一个更复杂的加载动画
    }

    return (
        <div className="flex h-full bg-background overflow-hidden">
            {/* Sidebar */}
            <aside
                className={cn(
                    "fixed inset-y-0 left-0 z-50 w-64 bg-card border-r transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-0",
                    !isSidebarOpen && "-translate-x-full"
                )}
            >
                <div className="h-full flex flex-col">
                    <Link to="/" className="h-16 flex items-center px-4 border-b gap-2">
                        <img src="/vite.svg" alt="Logo" className="w-8 h-8" />
                        <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-purple-600 dark:to-purple-400">
                            {systemConfig?.site_name || <>&nbsp;</>}
                        </span>
                    </Link>

                    <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
                        {filteredNavItems.map((item) => (
                            <Link
                                key={item.path}
                                to={item.path}
                                className={cn(
                                    "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                                    location.pathname === item.path
                                        ? "bg-primary text-primary-foreground"
                                        : "hover:bg-accent hover:text-accent-foreground"
                                )}
                            >
                                <item.icon className="w-4 h-4" />
                                {item.label}
                            </Link>
                        ))}
                    </nav>

                    <div className="p-4 border-t">
                        <button
                            onClick={handleLogout}
                            className="flex items-center gap-3 px-3 py-2 w-full rounded-md text-sm font-medium text-destructive hover:bg-destructive/10 transition-colors"
                        >
                            <LogOut className="w-4 h-4" />
                            退出登录
                        </button>
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
                <header className="h-16 flex items-center px-4 border-b bg-card lg:hidden">
                    <button
                        onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                        className="p-2 rounded-md hover:bg-accent"
                    >
                        {isSidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
                    </button>
                </header>

                <main className="flex-1 overflow-y-auto p-4 lg:p-8 main-scroll-container">
                    <Outlet />
                </main>
            </div>
        </div>
    );
}
