import React, { useEffect, useState } from 'react';
import { Card, Button, List, Tag, Modal, Form, Input, Typography, message as antdMessage, Spin, Space, Tabs } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined, FileTextOutlined } from '@ant-design/icons';
import apiClient from '../../api/client';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

interface Request {
    id: number;
    user_id: number;
    type: string;
    title: string;
    description: string;
    status: 'pending' | 'approved' | 'rejected';
    reviewed_by?: number;
    reviewed_at?: string;
    review_notes?: string;
    created_at: string;
    user_name: string;
    reviewer_name?: string;
}

const REQUEST_TYPES: Record<string, { label: string; icon: string }> = {
    leave: { label: 'Đơn xin nghỉ phép', icon: '🏖️' },
    salary_increase: { label: 'Yêu cầu tăng lương', icon: '💰' },
    transfer: { label: 'Đề xuất dự án', icon: '📋' },
    other: { label: 'Khác', icon: '📝' }
};

const ManagerRequests: React.FC = () => {
    const [requests, setRequests] = useState<Request[]>([]);
    const [loading, setLoading] = useState(false);
    const [modalVisible, setModalVisible] = useState(false);
    const [selectedRequest, setSelectedRequest] = useState<Request | null>(null);
    const [actionType, setActionType] = useState<'approve' | 'reject'>('approve');
    const [form] = Form.useForm();
    const [activeTab, setActiveTab] = useState('pending');

    useEffect(() => {
        fetchRequests();
    }, [activeTab]);

    const fetchRequests = async () => {
        try {
            setLoading(true);
            const statusFilter = activeTab === 'all' ? undefined : activeTab;
            const response = await apiClient.get<Request[]>('/api/manager/requests', {
                params: { status_filter: statusFilter }
            });
            setRequests(response.data);
        } catch (error) {
            antdMessage.error('Không thể tải danh sách yêu cầu');
        } finally {
            setLoading(false);
        }
    };

    const handleApprove = (request: Request) => {
        setSelectedRequest(request);
        setActionType('approve');
        form.resetFields();
        setModalVisible(true);
    };

    const handleReject = (request: Request) => {
        setSelectedRequest(request);
        setActionType('reject');
        form.resetFields();
        setModalVisible(true);
    };

    const handleSubmit = async (values: any) => {
        if (!selectedRequest) return;

        try {
            const endpoint = actionType === 'approve'
                ? `/api/manager/requests/${selectedRequest.id}/approve`
                : `/api/manager/requests/${selectedRequest.id}/reject`;

            await apiClient.put(endpoint, null, {
                params: { review_notes: values.review_notes }
            });

            antdMessage.success(
                actionType === 'approve'
                    ? 'Đã phê duyệt yêu cầu'
                    : 'Đã từ chối yêu cầu'
            );
            setModalVisible(false);
            fetchRequests();
        } catch (error: any) {
            antdMessage.error(error.response?.data?.detail || 'Có lỗi xảy ra');
        }
    };

    const getStatusTag = (status: string) => {
        const statusMap: Record<string, { text: string; color: string; icon: React.ReactNode }> = {
            pending: { text: 'Chờ duyệt', color: 'orange', icon: <ClockCircleOutlined /> },
            approved: { text: 'Đã phê duyệt', color: 'green', icon: <CheckCircleOutlined /> },
            rejected: { text: 'Đã từ chối', color: 'red', icon: <CloseCircleOutlined /> }
        };
        const { text, color, icon } = statusMap[status] || statusMap.pending;
        return <Tag color={color} icon={icon}>{text}</Tag>;
    };

    const getRequestTypeLabel = (type: string) => {
        const requestType = REQUEST_TYPES[type];
        return requestType ? `${requestType.icon} ${requestType.label}` : type;
    };

    const filteredRequests = requests;

    return (
        <div className="page-container">
            <Card>
                <div className="content-header" style={{ marginBottom: 24 }}>
                    <div>
                        <Title level={3}>
                            <FileTextOutlined /> Phê duyệt Yêu cầu
                        </Title>
                        <Paragraph type="secondary">
                            Xem xét và phê duyệt các yêu cầu từ nhân viên trong phòng ban
                        </Paragraph>
                    </div>
                </div>

                <Tabs
                    activeKey={activeTab}
                    onChange={setActiveTab}
                    items={[
                        { key: 'pending', label: `Chờ duyệt (${requests.filter(r => r.status === 'pending').length})` },
                        { key: 'approved', label: 'Đã phê duyệt' },
                        { key: 'rejected', label: 'Đã từ chối' },
                        { key: 'all', label: 'Tất cả' }
                    ]}
                    style={{ marginBottom: 16 }}
                />

                {loading ? (
                    <div style={{ textAlign: 'center', padding: 60 }}>
                        <Spin size="large" />
                    </div>
                ) : filteredRequests.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: 60, color: '#999' }}>
                        <FileTextOutlined style={{ fontSize: 64, marginBottom: 16, color: '#d9d9d9' }} />
                        <div style={{ fontSize: 16 }}>Chưa có yêu cầu nào</div>
                    </div>
                ) : (
                    <List
                        dataSource={filteredRequests}
                        renderItem={(request) => (
                            <List.Item style={{ padding: '16px 0' }}>
                                <Card style={{ width: '100%' }} hoverable>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                        <div style={{ flex: 1 }}>
                                            <div style={{ marginBottom: 8 }}>
                                                <Title level={5} style={{ marginBottom: 4, display: 'inline-block' }}>
                                                    {getRequestTypeLabel(request.type)}
                                                </Title>
                                                {getStatusTag(request.status)}
                                            </div>
                                            <Text strong style={{ fontSize: 16, display: 'block', marginBottom: 8 }}>
                                                {request.title}
                                            </Text>
                                            <Paragraph type="secondary" ellipsis={{ rows: 2 }}>
                                                {request.description}
                                            </Paragraph>
                                            <div style={{ marginTop: 12 }}>
                                                <Text type="secondary" style={{ fontSize: 12 }}>
                                                    Gửi bởi: <Text strong>{request.user_name}</Text> • {new Date(request.created_at).toLocaleDateString('vi-VN')}
                                                </Text>
                                            </div>
                                            {request.review_notes && (
                                                <div style={{ marginTop: 12, padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
                                                    <Text type="secondary" style={{ fontSize: 12 }}>Ghi chú:</Text>
                                                    <Paragraph style={{ marginTop: 4, marginBottom: 0 }}>{request.review_notes}</Paragraph>
                                                </div>
                                            )}
                                        </div>
                                        {request.status === 'pending' && (
                                            <Space style={{ marginLeft: 16 }}>
                                                <Button
                                                    type="primary"
                                                    icon={<CheckCircleOutlined />}
                                                    onClick={() => handleApprove(request)}
                                                    style={{ background: '#52c41a', borderColor: '#52c41a' }}
                                                >
                                                    Phê duyệt
                                                </Button>
                                                <Button
                                                    danger
                                                    icon={<CloseCircleOutlined />}
                                                    onClick={() => handleReject(request)}
                                                >
                                                    Từ chối
                                                </Button>
                                            </Space>
                                        )}
                                    </div>
                                </Card>
                            </List.Item>
                        )}
                    />
                )}
            </Card>

            <Modal
                title={actionType === 'approve' ? 'Phê duyệt yêu cầu' : 'Từ chối yêu cầu'}
                open={modalVisible}
                onCancel={() => setModalVisible(false)}
                footer={null}
                width={500}
            >
                {selectedRequest && (
                    <>
                        <div style={{ marginBottom: 16, padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
                            <Text strong>{selectedRequest.title}</Text>
                            <br />
                            <Text type="secondary" style={{ fontSize: 12 }}>
                                Từ: {selectedRequest.user_name}
                            </Text>
                        </div>

                        <Form form={form} layout="vertical" onFinish={handleSubmit}>
                            <Form.Item
                                name="review_notes"
                                label="Ghi chú (tùy chọn)"
                            >
                                <TextArea
                                    rows={4}
                                    placeholder="Nhập ghi chú cho nhân viên..."
                                />
                            </Form.Item>

                            <Form.Item style={{ marginBottom: 0 }}>
                                <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                                    <Button onClick={() => setModalVisible(false)}>
                                        Hủy
                                    </Button>
                                    <Button
                                        type="primary"
                                        htmlType="submit"
                                        danger={actionType === 'reject'}
                                        style={actionType === 'approve' ? { background: '#52c41a', borderColor: '#52c41a' } : undefined}
                                    >
                                        {actionType === 'approve' ? 'Phê duyệt' : 'Từ chối'}
                                    </Button>
                                </Space>
                            </Form.Item>
                        </Form>
                    </>
                )}
            </Modal>
        </div>
    );
};

export default ManagerRequests;
