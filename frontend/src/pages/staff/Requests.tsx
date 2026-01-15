import React, { useEffect, useState } from 'react';
import { Card, Button, List, Tag, Modal, Form, Input, Select, Typography, message as antdMessage, Spin } from 'antd';
import { PlusOutlined, FormOutlined, CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined } from '@ant-design/icons';
import apiClient from '../../api/client';
import './Requests.css';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

interface Request {
    id: number;
    type: string;
    title: string;
    description: string;
    status: 'pending' | 'approved' | 'rejected';
    created_at: string;
    review_notes?: string;
}

const REQUEST_TYPES = [
    { value: 'leave', label: 'Đơn xin nghỉ phép', icon: '🏖️' },
    { value: 'salary_increase', label: 'Yêu cầu tăng lương', icon: '💰' },
    { value: 'transfer', label: 'Đề xuất dự án', icon: '📋' },
    { value: 'other', label: 'Khác', icon: '📝' }
];

const StaffRequests: React.FC = () => {
    const [requests, setRequests] = useState<Request[]>([]);
    const [loading, setLoading] = useState(false);
    const [modalVisible, setModalVisible] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [form] = Form.useForm();

    useEffect(() => {
        fetchRequests();
    }, []);

    const fetchRequests = async () => {
        try {
            setLoading(true);
            const response = await apiClient.get<Request[]>('/api/staff/requests');
            setRequests(response.data);
        } catch (error) {
            antdMessage.error('Không thể tải danh sách yêu cầu');
        } finally {
            setLoading(false);
        }
    };

    const handleCreateRequest = async (values: any) => {
        try {
            setSubmitting(true);
            await apiClient.post('/api/staff/requests', values);
            antdMessage.success('Đã tạo yêu cầu thành công');
            setModalVisible(false);
            form.resetFields();
            fetchRequests();
        } catch (error) {
            antdMessage.error('Không thể tạo yêu cầu');
        } finally {
            setSubmitting(false);
        }
    };

    const getStatusTag = (status: string) => {
        const statusMap: Record<string, { text: string; color: string; icon: React.ReactNode }> = {
            pending: { text: 'Đang chờ duyệt', color: 'orange', icon: <ClockCircleOutlined /> },
            approved: { text: 'Đã phê duyệt', color: 'green', icon: <CheckCircleOutlined /> },
            rejected: { text: 'Đã từ chối', color: 'red', icon: <CloseCircleOutlined /> }
        };
        const { text, color, icon } = statusMap[status] || statusMap.pending;
        return <Tag color={color} icon={icon}>{text}</Tag>;
    };

    const getRequestTypeLabel = (type: string) => {
        const requestType = REQUEST_TYPES.find(t => t.value === type);
        return requestType ? `${requestType.icon} ${requestType.label}` : type;
    };

    return (
        <div className="requests-page">
            {/* Main Content - Full Width */}
            <Card className="main-content-card">
                <div className="content-header">
                    <div>
                        <Title level={3}>Biểu mẫu cá nhân</Title>
                        <Paragraph type="secondary">
                            Đây là nơi bạn có thể gửi và theo dõi các yêu cầu nghiệp vụ cá nhân (xin nghỉ phép, tăng lương,...).
                        </Paragraph>
                    </div>
                    <Button
                        type="primary"
                        size="large"
                        icon={<PlusOutlined />}
                        onClick={() => setModalVisible(true)}
                    >
                        Tạo yêu cầu mới
                    </Button>
                </div>

                {loading ? (
                    <div style={{ textAlign: 'center', padding: 60 }}>
                        <Spin size="large" />
                    </div>
                ) : requests.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: 60, color: '#999' }}>
                        <FormOutlined style={{ fontSize: 64, marginBottom: 16, color: '#d9d9d9' }} />
                        <div style={{ fontSize: 16 }}>Chưa có yêu cầu nào</div>
                        <div style={{ marginTop: 8 }}>Nhấn "Tạo yêu cầu mới" để bắt đầu</div>
                    </div>
                ) : (
                    <List
                        className="requests-list"
                        dataSource={requests}
                        renderItem={(request) => (
                            <List.Item className="request-item">
                                <Card className="request-card">
                                    <div className="request-header">
                                        <div>
                                            <Title level={5} style={{ marginBottom: 4 }}>
                                                {getRequestTypeLabel(request.type)}
                                            </Title>
                                            <Text strong style={{ fontSize: 16 }}>{request.title}</Text>
                                        </div>
                                        {getStatusTag(request.status)}
                                    </div>
                                    <Paragraph
                                        style={{ marginTop: 12, marginBottom: 8, color: '#666' }}
                                        ellipsis={{ rows: 2 }}
                                    >
                                        Gửi bởi: <Text strong>Bạn</Text>
                                    </Paragraph>
                                    {request.description && (
                                        <Paragraph
                                            type="secondary"
                                            ellipsis={{ rows: 2 }}
                                            style={{ marginTop: 8 }}
                                        >
                                            {request.description}
                                        </Paragraph>
                                    )}
                                    {request.review_notes && (
                                        <div className="review-notes">
                                            <Text type="secondary">Ghi chú từ quản lý:</Text>
                                            <Paragraph style={{ marginTop: 4 }}>{request.review_notes}</Paragraph>
                                        </div>
                                    )}
                                    <div className="request-footer">
                                        <Text type="secondary" style={{ fontSize: 12 }}>
                                            Ngày tạo: {new Date(request.created_at).toLocaleDateString('vi-VN')}
                                        </Text>
                                    </div>
                                </Card>
                            </List.Item>
                        )}
                    />
                )}
            </Card>

            {/* Modal tạo yêu cầu */}
            <Modal
                title="Tạo yêu cầu mới"
                open={modalVisible}
                onCancel={() => {
                    setModalVisible(false);
                    form.resetFields();
                }}
                footer={null}
                width={600}
            >
                <Form
                    form={form}
                    layout="vertical"
                    onFinish={handleCreateRequest}
                >
                    <Form.Item
                        name="type"
                        label="Loại yêu cầu"
                        rules={[{ required: true, message: 'Vui lòng chọn loại yêu cầu' }]}
                    >
                        <Select size="large" placeholder="Chọn loại yêu cầu">
                            {REQUEST_TYPES.map(type => (
                                <Select.Option key={type.value} value={type.value}>
                                    {type.icon} {type.label}
                                </Select.Option>
                            ))}
                        </Select>
                    </Form.Item>

                    <Form.Item
                        name="title"
                        label="Tiêu đề"
                        rules={[{ required: true, message: 'Vui lòng nhập tiêu đề' }]}
                    >
                        <Input size="large" placeholder="Nhập tiêu đề yêu cầu" />
                    </Form.Item>

                    <Form.Item
                        name="description"
                        label="Mô tả chi tiết"
                        rules={[{ required: true, message: 'Vui lòng nhập mô tả' }]}
                    >
                        <TextArea
                            rows={4}
                            placeholder="Nhập mô tả chi tiết về yêu cầu của bạn..."
                        />
                    </Form.Item>

                    <Form.Item style={{ marginBottom: 0, marginTop: 24 }}>
                        <Button
                            type="primary"
                            htmlType="submit"
                            size="large"
                            loading={submitting}
                            block
                        >
                            Gửi yêu cầu
                        </Button>
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
};

export default StaffRequests;
