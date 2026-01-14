import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import viVN from 'antd/locale/vi_VN';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { useAuthStore } from './store/authStore';
import Login from './pages/Login';
import Layout from './components/Layout';

// Admin pages
import AdminDashboard from './pages/admin/Dashboard';
import UserManagement from './pages/admin/UserManagement';

// Manager pages
import ManagerDashboard from './pages/manager/Dashboard';

// Staff pages
import StaffDashboard from './pages/staff/Dashboard';

import './index.css';

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            refetchOnWindowFocus: false,
            retry: 1,
        },
    },
});

interface ProtectedRouteProps {
    children: React.ReactNode;
    allowedRoles?: string[];
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles }) => {
    const { isAuthenticated, user } = useAuthStore();

    if (!isAuthenticated) {
        return <Navigate to="/login" replace />;
    }

    if (allowedRoles && user && !allowedRoles.includes(user.role)) {
        return <Navigate to="/" replace />;
    }

    return <>{children}</>;
};

const App: React.FC = () => {
    const { isAuthenticated, user } = useAuthStore();

    return (
        <ConfigProvider
            locale={viVN}
            theme={{
                token: {
                    colorPrimary: '#1890ff',
                    borderRadius: 8,
                    fontFamily: 'Inter, sans-serif',
                },
            }}
        >
            <QueryClientProvider client={queryClient}>
                <BrowserRouter>
                    <Routes>
                        <Route path="/login" element={<Login />} />

                        <Route
                            path="/"
                            element={
                                isAuthenticated ? (
                                    user?.role === 'admin' ? (
                                        <Navigate to="/admin/dashboard" replace />
                                    ) : user?.role === 'manager' ? (
                                        <Navigate to="/manager/dashboard" replace />
                                    ) : (
                                        <Navigate to="/staff/dashboard" replace />
                                    )
                                ) : (
                                    <Navigate to="/login" replace />
                                )
                            }
                        />

                        {/* Admin Routes */}
                        <Route
                            path="/admin/dashboard"
                            element={
                                <ProtectedRoute allowedRoles={['admin']}>
                                    <Layout>
                                        <AdminDashboard />
                                    </Layout>
                                </ProtectedRoute>
                            }
                        />
                        <Route
                            path="/admin/users"
                            element={
                                <ProtectedRoute allowedRoles={['admin']}>
                                    <Layout>
                                        <UserManagement />
                                    </Layout>
                                </ProtectedRoute>
                            }
                        />

                        {/* Manager Routes */}
                        <Route
                            path="/manager/dashboard"
                            element={
                                <ProtectedRoute allowedRoles={['manager']}>
                                    <Layout>
                                        <ManagerDashboard />
                                    </Layout>
                                </ProtectedRoute>
                            }
                        />

                        {/* Staff Routes */}
                        <Route
                            path="/staff/dashboard"
                            element={
                                <ProtectedRoute allowedRoles={['staff']}>
                                    <Layout>
                                        <StaffDashboard />
                                    </Layout>
                                </ProtectedRoute>
                            }
                        />

                        <Route path="*" element={<Navigate to="/" replace />} />
                    </Routes>
                </BrowserRouter>
            </QueryClientProvider>
        </ConfigProvider>
    );
};

export default App;
