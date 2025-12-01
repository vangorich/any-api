import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useEffect } from 'react';
import { SystemProvider, useSystem } from './contexts/SystemContext';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import InitializePage from './pages/InitializePage';
import DashboardLayout from './pages/dashboard/DashboardLayout';
import DashboardHome from './pages/dashboard/DashboardHome';
import PresetsPage from './pages/dashboard/PresetsPage';
import RegexPage from './pages/dashboard/RegexPage';
import KeysPage from './pages/dashboard/KeysPage';
import ChannelsPage from './pages/dashboard/ChannelsPage';
import LogsPage from './pages/dashboard/LogsPage';
import ProfilePage from './pages/dashboard/ProfilePage';
import AdminUsersPage from './pages/dashboard/AdminUsersPage';
import SystemPage from './pages/dashboard/SystemPage';
import { Toaster } from './components/ui/toaster';
import { ConfirmDialog } from './components/ui/ConfirmDialog';
import PrivateRoute from './components/PrivateRoute';

// 一个专门用于更新网站标题的组件
const SiteTitleUpdater = () => {
    const { config } = useSystem();

    useEffect(() => {
        if (config && config.site_name) {
            document.title = config.site_name;
        }
    }, [config]);

    return null; // 这个组件不渲染任何UI
};


function App() {
    return (
        <SystemProvider>
            <BrowserRouter>
                <SiteTitleUpdater />
                <Routes>
                    <Route path="/" element={<HomePage />} />
                    <Route path="/login" element={<LoginPage />} />
                    <Route path="/initialize" element={<InitializePage />} />

                    <Route path="/dashboard" element={<DashboardLayout />}>
                        {/* 普通用户及以上 */}
                        <Route element={<PrivateRoute allowedRoles={['user', 'admin', 'super_admin']} />}>
                            <Route index element={<DashboardHome />} />
                            <Route path="presets" element={<PresetsPage />} />
                            <Route path="regex" element={<RegexPage />} />
                            <Route path="keys" element={<KeysPage />} />
                            <Route path="channels" element={<ChannelsPage />} />
                            <Route path="logs" element={<LogsPage />} />
                            <Route path="profile" element={<ProfilePage />} />
                        </Route>
                        {/* 管理员及以上 */}
                        <Route element={<PrivateRoute allowedRoles={['admin', 'super_admin']} />}>
                            <Route path="users" element={<AdminUsersPage />} />
                        </Route>
                        {/* 仅超级管理员 */}
                        <Route element={<PrivateRoute allowedRoles={['super_admin']} />}>
                            <Route path="system" element={<SystemPage />} />
                        </Route>
                    </Route>

                    <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
                <Toaster />
                <ConfirmDialog />
            </BrowserRouter>
        </SystemProvider>
    );
}

export default App;
