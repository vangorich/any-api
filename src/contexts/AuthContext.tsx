import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '@/utils/api';

// 定义用户对象接口
export interface User {
    id: number;
    email: string;
    username: string;
    is_active: boolean;
    role: 'user' | 'admin' | 'super_admin';
}

// 定义Context的数据结构
interface AuthContextType {
    currentUser: User | null;
    loading: boolean;
    login: (token: string) => Promise<void>;
    logout: () => void;
}

// 创建Context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// 自定义Hook，方便使用Context
export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth 必须在 AuthProvider 中使用');
    }
    return context;
};

// AuthProvider组件
export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [currentUser, setCurrentUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);

    const fetchUser = useCallback(async () => {
        const token = localStorage.getItem('token');
        if (token) {
            try {
                api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
                const response = await api.get<User>('/users/me');
                setCurrentUser(response.data);
            } catch (error) {
                console.error('获取用户信息失败', error);
                localStorage.removeItem('token');
                delete api.defaults.headers.common['Authorization'];
            }
        }
        setLoading(false);
    }, []);

    useEffect(() => {
        fetchUser();
    }, [fetchUser]);

    const login = async (token: string) => {
        localStorage.setItem('token', token);
        api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        setLoading(true);
        await fetchUser();
    };

    const logout = () => {
        localStorage.removeItem('token');
        delete api.defaults.headers.common['Authorization'];
        setCurrentUser(null);
    };

    const value = {
        currentUser,
        loading,
        login,
        logout,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};