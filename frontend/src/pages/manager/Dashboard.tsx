import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Table, Typography, message } from 'antd';
import { MessageOutlined, CheckCircleOutlined, TeamOutlined } from '@ant-design/icons';
import apiClient from '../../api/client';
import { Message } from '../../types';

const { Title } = Typography;

const ManagerDashboard: React.FC = () => {
    const [stats, setStats] = useState({ total: 0, completed: 0, pending: 0, staff: 0 });
    const [recentMessages, setRecentMessages] = useState<Message[]>([]);

    useEffect(() => {
        fetchDashboardData();
    }, []);

    const fetchDashboardData = async () => {
        try {
            // Fetch staff count
            const staffRes = await apiClient.get('/api/manager/staff');
            const staffCount = staffRes.data.length;

            setStats({
                total: 0,
                completed: 0,
                pending: 0,
                staff: staffCount,
            });
        } catch (error) {
            message.error('Không thể tải dữ liệu dashboard');
        }
    };

    return (
        <div className="page-container">
            <div className="page-header">
                <Title level={2} className="page-title">Dashboard Quản lý</Title>
                <p className="page-subtitle">Quản lý phòng ban và nhân viên</p>
            </div>

            <Row gutter={[16, 16]}>
                <Col xs={24} sm={12} lg={8}>
                    <Card className="stat-card">
                        <Statistic
                            title={<span className="stat-label">Tổng nhân viên</span>}
                            value={stats.staff}
                            prefix={<TeamOutlined />}
                            valueStyle={{ color: 'white' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={8}>
                    <Card className="stat-card" style={{ background: 'linear-gradient(135deg, #52c41a 0%, #73d13d 100%)' }}>
                        <Statistic
                            title={<span className="stat-label">Tin nhắn hoàn thành</span>}
                            value={stats.completed}
                            prefix={<CheckCircleOutlined />}
                            valueStyle={{ color: 'white' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={8}>
                    <Card className="stat-card" style={{ background: 'linear-gradient(135deg, #faad14 0%, #ffc53d 100%)' }}>
                        <Statistic
                            title={<span className="stat-label">Tin nhắn chờ xử lý</span>}
                            value={stats.pending}
                            prefix={<MessageOutlined />}
                            valueStyle={{ color: 'white' }}
                        />
                    </Card>
                </Col>
            </Row>

            <Card style={{ marginTop: 24 }} title="Hoạt động gần đây">
                <p style={{ textAlign: 'center', padding: 40, color: '#8c8c8c' }}>
                    Chưa có hoạt động nào
                </p>
            </Card>
        </div>
    );
};

export default ManagerDashboard;
