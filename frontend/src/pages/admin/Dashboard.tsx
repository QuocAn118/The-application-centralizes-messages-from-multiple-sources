import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Table, Typography, Spin, message } from 'antd';
import {
    UserOutlined,
    MessageOutlined,
    TeamOutlined,
    FileTextOutlined,
    CheckCircleOutlined,
    ClockCircleOutlined,
} from '@ant-design/icons';
import apiClient from '../../api/client';
import { DashboardStats, User } from '../../types';

const { Title } = Typography;

const AdminDashboard: React.FC = () => {
    const [loading, setLoading] = useState(true);
    const [stats, setStats] = useState<DashboardStats | null>(null);
    const [recentUsers, setRecentUsers] = useState<User[]>([]);

    useEffect(() => {
        fetchDashboardData();
    }, []);

    const fetchDashboardData = async () => {
        try {
            setLoading(true);
            const [statsRes, usersRes] = await Promise.all([
                apiClient.get<DashboardStats>('/api/admin/dashboard'),
                apiClient.get<User[]>('/api/admin/users?limit=5'),
            ]);
            setStats(statsRes.data);
            setRecentUsers(usersRes.data);
        } catch (error: any) {
            message.error('Không thể tải dữ liệu dashboard');
        } finally {
            setLoading(false);
        }
    };

    const userColumns = [
        {
            title: 'Tên',
            dataIndex: 'full_name',
            key: 'full_name',
        },
        {
            title: 'Email',
            dataIndex: 'email',
            key: 'email',
        },
        {
            title: 'Vai trò',
            dataIndex: 'role',
            key: 'role',
            render: (role: string) => {
                const roleMap: Record<string, string> = {
                    admin: 'Quản trị viên',
                    manager: 'Quản lý',
                    staff: 'Nhân viên',
                };
                return roleMap[role] || role;
            },
        },
        {
            title: 'Trạng thái',
            dataIndex: 'is_active',
            key: 'is_active',
            render: (isActive: boolean) => (
                <span style={{ color: isActive ? '#52c41a' : '#ff4d4f' }}>
                    {isActive ? 'Hoạt động' : 'Không hoạt động'}
                </span>
            ),
        },
    ];

    if (loading) {
        return (
            <div className="loading-container">
                <Spin size="large" />
            </div>
        );
    }

    return (
        <div className="page-container">
            <div className="page-header">
                <Title level={2} className="page-title">Dashboard Quản trị viên</Title>
                <p className="page-subtitle">Tổng quan hệ thống OmniChat</p>
            </div>

            <Row gutter={[16, 16]}>
                <Col xs={24} sm={12} lg={6}>
                    <Card className="stat-card">
                        <Statistic
                            title={<span className="stat-label">Tổng tin nhắn</span>}
                            value={stats?.total_messages || 0}
                            prefix={<MessageOutlined />}
                            valueStyle={{ color: 'white' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                    <Card className="stat-card" style={{ background: 'linear-gradient(135deg, #52c41a 0%, #73d13d 100%)' }}>
                        <Statistic
                            title={<span className="stat-label">Đã xử lý</span>}
                            value={stats?.completed_messages || 0}
                            prefix={<CheckCircleOutlined />}
                            valueStyle={{ color: 'white' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                    <Card className="stat-card" style={{ background: 'linear-gradient(135deg, #faad14 0%, #ffc53d 100%)' }}>
                        <Statistic
                            title={<span className="stat-label">Chờ xử lý</span>}
                            value={stats?.pending_messages || 0}
                            prefix={<ClockCircleOutlined />}
                            valueStyle={{ color: 'white' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                    <Card className="stat-card" style={{ background: 'linear-gradient(135deg, #722ed1 0%, #9254de 100%)' }}>
                        <Statistic
                            title={<span className="stat-label">Người dùng</span>}
                            value={stats?.total_users || 0}
                            prefix={<UserOutlined />}
                            valueStyle={{ color: 'white' }}
                        />
                    </Card>
                </Col>
            </Row>

            <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
                <Col xs={24} lg={12}>
                    <Card>
                        <Statistic
                            title="Tổng phòng ban"
                            value={stats?.total_departments || 0}
                            prefix={<TeamOutlined />}
                        />
                    </Card>
                </Col>
                <Col xs={24} lg={12}>
                    <Card>
                        <Statistic
                            title="Yêu cầu chờ duyệt"
                            value={stats?.pending_requests || 0}
                            prefix={<FileTextOutlined />}
                        />
                    </Card>
                </Col>
            </Row>

            <Card style={{ marginTop: 24 }} title="Người dùng mới nhất">
                <Table
                    dataSource={recentUsers}
                    columns={userColumns}
                    rowKey="id"
                    pagination={false}
                />
            </Card>
        </div>
    );
};

export default AdminDashboard;
