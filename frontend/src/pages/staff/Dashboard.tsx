import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Table, Button, Tag, Typography, message } from 'antd';
import { MessageOutlined, CheckCircleOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import apiClient from '../../api/client';
import { Message } from '../../types';

const { Title } = Typography;

const StaffDashboard: React.FC = () => {
    const navigate = useNavigate();
    const [messages, setMessages] = useState<Message[]>([]);
    const [stats, setStats] = useState({ total: 0, completed: 0, pending: 0 });
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        fetchMessages();
    }, []);

    const fetchMessages = async () => {
        try {
            setLoading(true);
            const response = await apiClient.get<Message[]>('/api/staff/messages?limit=10');
            setMessages(response.data);

            // Calculate stats
            const total = response.data.length;
            const completed = response.data.filter(m => m.status === 'completed').length;
            const pending = response.data.filter(m => m.status !== 'completed').length;
            setStats({ total, completed, pending });
        } catch (error) {
            message.error('Không thể tải danh sách tin nhắn');
        } finally {
            setLoading(false);
        }
    };

    const handleMarkComplete = async (messageId: number) => {
        try {
            await apiClient.put(`/api/staff/messages/${messageId}/complete`);
            message.success('Đã đánh dấu hoàn thành');
            fetchMessages();
        } catch (error) {
            message.error('Không thể cập nhật trạng thái');
        }
    };

    const columns = [
        {
            title: 'Khách hàng',
            dataIndex: 'customer_name',
            key: 'customer_name',
            render: (name: string) => name || 'Không rõ',
        },
        {
            title: 'Nội dung',
            dataIndex: 'content',
            key: 'content',
            render: (text: string) => text.substring(0, 50) + (text.length > 50 ? '...' : ''),
        },
        {
            title: 'Nền tảng',
            dataIndex: 'platform',
            key: 'platform',
            render: (platform: string) => (
                <Tag color="blue">{platform.toUpperCase()}</Tag>
            ),
        },
        {
            title: 'Trạng thái',
            dataIndex: 'status',
            key: 'status',
            render: (status: string) => {
                const statusMap: Record<string, { text: string; color: string }> = {
                    pending: { text: 'Chờ xử lý', color: 'orange' },
                    assigned: { text: 'Đã giao', color: 'blue' },
                    in_progress: { text: 'Đang xử lý', color: 'cyan' },
                    completed: { text: 'Hoàn thành', color: 'green' },
                };
                const { text, color } = statusMap[status] || { text: status, color: 'default' };
                return <Tag color={color}>{text}</Tag>;
            },
        },
        {
            title: 'Hành động',
            key: 'actions',
            render: (_: any, record: Message) => (
                record.status !== 'completed' ? (
                    <Button
                        type="primary"
                        size="small"
                        onClick={() => handleMarkComplete(record.id)}
                    >
                        Hoàn thành
                    </Button>
                ) : null
            ),
        },
    ];

    return (
        <div className="page-container">
            <div className="page-header">
                <Title level={2} className="page-title">Dashboard Nhân viên</Title>
                <p className="page-subtitle">Quản lý tin nhắn được giao</p>
            </div>

            <Row gutter={[16, 16]}>
                <Col xs={24} sm={8}>
                    <Card className="stat-card">
                        <Statistic
                            title={<span className="stat-label">Tổng tin nhắn</span>}
                            value={stats.total}
                            prefix={<MessageOutlined />}
                            valueStyle={{ color: 'white' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={8}>
                    <Card className="stat-card" style={{ background: 'linear-gradient(135deg, #52c41a 0%, #73d13d 100%)' }}>
                        <Statistic
                            title={<span className="stat-label">Đã hoàn thành</span>}
                            value={stats.completed}
                            prefix={<CheckCircleOutlined />}
                            valueStyle={{ color: 'white' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={8}>
                    <Card className="stat-card" style={{ background: 'linear-gradient(135deg, #faad14 0%, #ffc53d 100%)' }}>
                        <Statistic
                            title={<span className="stat-label">Chờ xử lý</span>}
                            value={stats.pending}
                            prefix={<ClockCircleOutlined />}
                            valueStyle={{ color: 'white' }}
                        />
                    </Card>
                </Col>
            </Row>

            <Card
                style={{ marginTop: 24 }}
                title="Tin nhắn gần đây"
                extra={
                    <Button type="primary" onClick={() => navigate('/staff/messages')}>
                        Xem tất cả
                    </Button>
                }
            >
                <Table
                    dataSource={messages}
                    columns={columns}
                    rowKey="id"
                    loading={loading}
                    pagination={{ pageSize: 10 }}
                />
            </Card>
        </div>
    );
};

export default StaffDashboard;
