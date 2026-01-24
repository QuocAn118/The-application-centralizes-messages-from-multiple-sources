import React, { ReactNode } from 'react';
import { Layout as AntLayout, Menu, Avatar, Dropdown, Badge, Typography } from 'antd';
import {
    DashboardOutlined,
    UserOutlined,
    TeamOutlined,
    MessageOutlined,
    SettingOutlined,
    LogoutOutlined,
    BellOutlined,
    KeyOutlined,
    BarChartOutlined,
    ClockCircleOutlined,
    FileTextOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

const { Header, Sider, Content } = AntLayout;
const { Text } = Typography;

interface LayoutProps {
    children: ReactNode;
}

const AppLayout: React.FC<LayoutProps> = ({ children }) => {
    const navigate = useNavigate();
    const location = useLocation();
    const { user, logout } = useAuthStore();

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    const userMenuItems = [
        {
            key: 'profile',
            icon: <UserOutlined />,
            label: 'Thông tin cá nhân',
        },
        {
            key: 'settings',
            icon: <SettingOutlined />,
            label: 'Cài đặt',
        },
        {
            type: 'divider' as const,
        },
        {
            key: 'logout',
            icon: <LogoutOutlined />,
            label: 'Đăng xuất',
            onClick: handleLogout,
        },
    ];

    const getMenuItems = () => {
        if (!user) return [];

        const baseItems = [];

        if (user.role === 'staff' || user.role === 'admin') {
            baseItems.push({
                key: `/${user.role}/dashboard`,
                icon: <DashboardOutlined />,
                label: 'Dashboard',
            });
        }

        if (user.role === 'admin') {
            return [
                ...baseItems,
                {
                    key: '/admin/users',
                    icon: <TeamOutlined />,
                    label: 'Quản lý người dùng',
                },
                {
                    key: '/admin/statistics',
                    icon: <BarChartOutlined />,
                    label: 'Thống kê',
                },
                {
                    key: '/admin/keywords',
                    icon: <KeyOutlined />,
                    label: 'Từ khóa',
                },
            ];
        }

        if (user.role === 'manager') {
            return [
                ...baseItems,
                {
                    key: '/manager/staff',
                    icon: <TeamOutlined />,
                    label: 'Quản lý nhân viên',
                },
                {
                    key: '/manager/kpis',
                    icon: <BarChartOutlined />,
                    label: 'Quản lý KPI',
                },
                {
                    key: '/manager/keywords',
                    icon: <KeyOutlined />,
                    label: 'Từ khóa',
                },
                {
                    key: '/manager/shifts',
                    icon: <ClockCircleOutlined />,
                    label: 'Ca làm việc',
                },
                {
                    key: '/manager/requests',
                    icon: <FileTextOutlined />,
                    label: 'Phê duyệt yêu cầu',
                },
            ];
        }

        if (user.role === 'staff') {
            return [
                ...baseItems,
                {
                    key: '/staff/messages',
                    icon: <MessageOutlined />,
                    label: 'Tin nhắn',
                },
                {
                    key: '/staff/requests',
                    icon: <FileTextOutlined />,
                    label: 'Yêu cầu của tôi',
                },
            ];
        }

        return baseItems;
    };

    return (
        <AntLayout style={{ minHeight: '100vh' }}>
            <Sider
                width={250}
                style={{
                    overflow: 'auto',
                    height: '100vh',
                    position: 'fixed',
                    left: 0,
                    top: 0,
                    bottom: 0,
                }}
            >
                <div style={{
                    height: 64,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    borderBottom: '1px solid #f0f0f0',
                    padding: '0 16px'
                }}>
                    <img src="/logo.png" alt="OmniChat" style={{ height: 40, marginRight: 8 }} />
                    <img src="/logo.png" alt="OmniChat" style={{ height: 40, marginRight: 8 }} />
                </div>
                <Menu
                    mode="inline"
                    selectedKeys={[location.pathname]}
                    items={getMenuItems()}
                    onClick={({ key }) => navigate(key)}
                    style={{ borderRight: 0 }}
                />
            </Sider>

            <AntLayout style={{ marginLeft: 250 }}>
                <Header style={{
                    background: '#fff',
                    padding: '0 24px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
                    position: 'sticky',
                    top: 0,
                    zIndex: 1,
                }}>
                    <div />
                    <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
                        <Badge count={0}>
                            <BellOutlined style={{ fontSize: 20, cursor: 'pointer' }} />
                        </Badge>
                        <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                                <Avatar icon={<UserOutlined />} style={{ backgroundColor: '#1890ff' }} />
                                <div>
                                    <Text strong style={{ display: 'block' }}>{user?.full_name}</Text>
                                    <Text type="secondary" style={{ fontSize: 12 }}>
                                        {user?.role === 'admin' ? 'Quản trị viên' :
                                            user?.role === 'manager' ? 'Quản lý' : 'Nhân viên'}
                                    </Text>
                                </div>
                            </div>
                        </Dropdown>
                    </div>
                </Header>

                <Content style={{ margin: 0, overflow: 'initial' }}>
                    {children}
                </Content>
            </AntLayout>
        </AntLayout>
    );
};

export default AppLayout;
