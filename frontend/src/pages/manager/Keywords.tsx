import React, { useEffect, useState } from 'react';
import { Card, Button, Table, Tag, Modal, Form, Input, InputNumber, Switch, Typography, message as antdMessage, Popconfirm, Space } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, KeyOutlined } from '@ant-design/icons';
import apiClient from '../../api/client';
import type { ColumnsType } from 'antd/es/table';

const { Title, Paragraph } = Typography;

interface Keyword {
    id: number;
    keyword: string;
    department_id: number;
    priority: number;
    is_active: boolean;
    created_at: string;
}

const ManagerKeywords: React.FC = () => {
    const [keywords, setKeywords] = useState<Keyword[]>([]);
    const [loading, setLoading] = useState(false);
    const [modalVisible, setModalVisible] = useState(false);
    const [editingKeyword, setEditingKeyword] = useState<Keyword | null>(null);
    const [form] = Form.useForm();

    useEffect(() => {
        fetchKeywords();
    }, []);

    const fetchKeywords = async () => {
        try {
            setLoading(true);
            const response = await apiClient.get<Keyword[]>('/api/manager/keywords');
            setKeywords(response.data);
        } catch (error) {
            antdMessage.error('Không thể tải danh sách từ khóa');
        } finally {
            setLoading(false);
        }
    };

    const handleCreate = () => {
        setEditingKeyword(null);
        form.resetFields();
        setModalVisible(true);
    };

    const handleEdit = (record: Keyword) => {
        setEditingKeyword(record);
        form.setFieldsValue(record);
        setModalVisible(true);
    };

    const handleDelete = async (id: number) => {
        try {
            await apiClient.delete(`/api/manager/keywords/${id}`);
            antdMessage.success('Đã xóa từ khóa');
            fetchKeywords();
        } catch (error) {
            antdMessage.error('Không thể xóa từ khóa');
        }
    };

    const handleSubmit = async (values: any) => {
        try {
            if (editingKeyword) {
                await apiClient.put(`/api/manager/keywords/${editingKeyword.id}`, values);
                antdMessage.success('Đã cập nhật từ khóa');
            } else {
                // Lấy department_id từ user hiện tại
                const profileResponse = await apiClient.get('/api/staff/profile');
                const departmentId = profileResponse.data.department_id;

                await apiClient.post('/api/manager/keywords', {
                    ...values,
                    department_id: departmentId
                });
                antdMessage.success('Đã tạo từ khóa mới');
            }
            setModalVisible(false);
            form.resetFields();
            fetchKeywords();
        } catch (error: any) {
            antdMessage.error(error.response?.data?.detail || 'Có lỗi xảy ra');
        }
    };

    const columns: ColumnsType<Keyword> = [
        {
            title: 'Từ khóa',
            dataIndex: 'keyword',
            key: 'keyword',
            render: (text) => <strong>{text}</strong>,
        },
        {
            title: 'Độ ưu tiên',
            dataIndex: 'priority',
            key: 'priority',
            width: 120,
            render: (priority) => {
                const color = priority === 3 ? 'red' : priority === 2 ? 'orange' : 'blue';
                return <Tag color={color}>Mức {priority}</Tag>;
            },
        },
        {
            title: 'Trạng thái',
            dataIndex: 'is_active',
            key: 'is_active',
            width: 120,
            render: (isActive) => (
                <Tag color={isActive ? 'green' : 'default'}>
                    {isActive ? 'Hoạt động' : 'Tạm dừng'}
                </Tag>
            ),
        },
        {
            title: 'Ngày tạo',
            dataIndex: 'created_at',
            key: 'created_at',
            width: 150,
            render: (date) => new Date(date).toLocaleDateString('vi-VN'),
        },
        {
            title: 'Hành động',
            key: 'actions',
            width: 150,
            render: (_, record) => (
                <Space>
                    <Button
                        type="link"
                        icon={<EditOutlined />}
                        onClick={() => handleEdit(record)}
                    >
                        Sửa
                    </Button>
                    <Popconfirm
                        title="Xóa từ khóa"
                        description="Bạn có chắc muốn xóa từ khóa này?"
                        onConfirm={() => handleDelete(record.id)}
                        okText="Xóa"
                        cancelText="Hủy"
                    >
                        <Button type="link" danger icon={<DeleteOutlined />}>
                            Xóa
                        </Button>
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    return (
        <div className="page-container">
            <Card>
                <div className="content-header" style={{ marginBottom: 24 }}>
                    <div>
                        <Title level={3}>
                            <KeyOutlined /> Quản lý Từ khóa
                        </Title>
                        <Paragraph type="secondary">
                            Quản lý các từ khóa để phân loại và gán tin nhắn tự động cho nhân viên
                        </Paragraph>
                    </div>
                    <Button
                        type="primary"
                        size="large"
                        icon={<PlusOutlined />}
                        onClick={handleCreate}
                    >
                        Thêm từ khóa
                    </Button>
                </div>

                <Table
                    columns={columns}
                    dataSource={keywords}
                    rowKey="id"
                    loading={loading}
                    pagination={{ pageSize: 10 }}
                />
            </Card>

            <Modal
                title={editingKeyword ? 'Cập nhật từ khóa' : 'Thêm từ khóa mới'}
                open={modalVisible}
                onCancel={() => {
                    setModalVisible(false);
                    form.resetFields();
                }}
                footer={null}
                width={500}
            >
                <Form
                    form={form}
                    layout="vertical"
                    onFinish={handleSubmit}
                    initialValues={{ priority: 1, is_active: true }}
                >
                    <Form.Item
                        name="keyword"
                        label="Từ khóa"
                        rules={[{ required: true, message: 'Vui lòng nhập từ khóa' }]}
                    >
                        <Input placeholder="Ví dụ: mua hàng, khiếu nại, hỗ trợ..." />
                    </Form.Item>

                    <Form.Item
                        name="priority"
                        label="Độ ưu tiên"
                        rules={[{ required: true, message: 'Vui lòng chọn độ ưu tiên' }]}
                    >
                        <InputNumber
                            min={1}
                            max={3}
                            style={{ width: '100%' }}
                            placeholder="1 = Thấp, 2 = Trung bình, 3 = Cao"
                        />
                    </Form.Item>

                    <Form.Item
                        name="is_active"
                        label="Trạng thái"
                        valuePropName="checked"
                    >
                        <Switch checkedChildren="Hoạt động" unCheckedChildren="Tạm dừng" />
                    </Form.Item>

                    <Form.Item style={{ marginBottom: 0, marginTop: 24 }}>
                        <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                            <Button onClick={() => setModalVisible(false)}>
                                Hủy
                            </Button>
                            <Button type="primary" htmlType="submit">
                                {editingKeyword ? 'Cập nhật' : 'Tạo mới'}
                            </Button>
                        </Space>
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
};

export default ManagerKeywords;
