import React, { useEffect, useState } from 'react';
import { Card, Button, Table, Modal, Form, Input, Typography, message as antdMessage, Popconfirm, Space, Tag } from 'antd';
import { EditOutlined, DeleteOutlined, TeamOutlined, UserAddOutlined } from '@ant-design/icons';
import apiClient from '../../api/client';
import type { ColumnsType } from 'antd/es/table';

const { Title, Paragraph } = Typography;

interface Staff {
    id: number;
    email: string;
    full_name: string;
    phone?: string;
    role: string;
    department_id?: number;
    is_active: boolean;
    created_at: string;
}

const StaffManagement: React.FC = () => {
    const [staff, setStaff] = useState<Staff[]>([]);
    const [loading, setLoading] = useState(false);
    const [modalVisible, setModalVisible] = useState(false);
    const [editingStaff, setEditingStaff] = useState<Staff | null>(null);
    const [form] = Form.useForm();

    useEffect(() => {
        fetchStaff();
    }, []);

    const fetchStaff = async () => {
        try {
            setLoading(true);
            const response = await apiClient.get<Staff[]>('/api/manager/staff');
            setStaff(response.data);
        } catch (error) {
            antdMessage.error('Không thể tải danh sách nhân viên');
        } finally {
            setLoading(false);
        }
    };

    const handleCreate = () => {
        setEditingStaff(null);
        form.resetFields();
        setModalVisible(true);
    };

    const handleEdit = (record: Staff) => {
        setEditingStaff(record);
        form.setFieldsValue({
            email: record.email,
            full_name: record.full_name,
            phone: record.phone
        });
        setModalVisible(true);
    };

    const handleDelete = async (id: number) => {
        try {
            await apiClient.delete(`/api/manager/staff/${id}`);
            antdMessage.success('Đã xóa nhân viên');
            fetchStaff();
        } catch (error) {
            antdMessage.error('Không thể xóa nhân viên');
        }
    };

    const handleSubmit = async (values: any) => {
        try {
            if (editingStaff) {
                // Update
                await apiClient.put(`/api/manager/staff/${editingStaff.id}`, {
                    email: values.email,
                    full_name: values.full_name,
                    phone: values.phone
                });
                antdMessage.success('Đã cập nhật thông tin nhân viên');
            } else {
                // Create - cần thêm password và department_id
                const profileResponse = await apiClient.get('/api/staff/profile');
                const departmentId = profileResponse.data.department_id;

                await apiClient.post('/api/manager/staff', {
                    email: values.email,
                    full_name: values.full_name,
                    phone: values.phone,
                    password: values.password,
                    role: 'staff',
                    department_id: departmentId
                });
                antdMessage.success('Đã tạo nhân viên mới');
            }
            setModalVisible(false);
            form.resetFields();
            fetchStaff();
        } catch (error: any) {
            antdMessage.error(error.response?.data?.detail || 'Có lỗi xảy ra');
        }
    };

    const columns: ColumnsType<Staff> = [
        {
            title: 'Họ và tên',
            dataIndex: 'full_name',
            key: 'full_name',
            render: (text) => <strong>{text}</strong>,
        },
        {
            title: 'Email',
            dataIndex: 'email',
            key: 'email',
        },
        {
            title: 'Số điện thoại',
            dataIndex: 'phone',
            key: 'phone',
            render: (phone) => phone || '-',
        },
        {
            title: 'Trạng thái',
            dataIndex: 'is_active',
            key: 'is_active',
            width: 120,
            render: (isActive) => (
                <Tag color={isActive ? 'green' : 'default'}>
                    {isActive ? 'Hoạt động' : 'Đã khóa'}
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
                        title="Xóa nhân viên"
                        description="Bạn có chắc muốn xóa nhân viên này?"
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
                            <TeamOutlined /> Quản lý Nhân viên
                        </Title>
                        <Paragraph type="secondary">
                            Quản lý thông tin nhân viên trong phòng ban
                        </Paragraph>
                    </div>
                    <Button
                        type="primary"
                        size="large"
                        icon={<UserAddOutlined />}
                        onClick={handleCreate}
                    >
                        Thêm nhân viên
                    </Button>
                </div>

                <Table
                    columns={columns}
                    dataSource={staff}
                    rowKey="id"
                    loading={loading}
                    pagination={{ pageSize: 10 }}
                />
            </Card>

            <Modal
                title={editingStaff ? 'Cập nhật thông tin nhân viên' : 'Thêm nhân viên mới'}
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
                >
                    <Form.Item
                        name="full_name"
                        label="Họ và tên"
                        rules={[{ required: true, message: 'Vui lòng nhập họ tên' }]}
                    >
                        <Input placeholder="Nguyễn Văn A" />
                    </Form.Item>

                    <Form.Item
                        name="email"
                        label="Email"
                        rules={[
                            { required: true, message: 'Vui lòng nhập email' },
                            { type: 'email', message: 'Email không hợp lệ' }
                        ]}
                    >
                        <Input placeholder="nhanvien@company.com" disabled={!!editingStaff} />
                    </Form.Item>

                    {!editingStaff && (
                        <Form.Item
                            name="password"
                            label="Mật khẩu"
                            rules={[
                                { required: true, message: 'Vui lòng nhập mật khẩu' },
                                { min: 6, message: 'Mật khẩu tối thiểu 6 ký tự' }
                            ]}
                        >
                            <Input.Password placeholder="Nhập mật khẩu" />
                        </Form.Item>
                    )}

                    <Form.Item
                        name="phone"
                        label="Số điện thoại"
                    >
                        <Input placeholder="0901234567" />
                    </Form.Item>

                    <Form.Item style={{ marginBottom: 0, marginTop: 24 }}>
                        <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                            <Button onClick={() => setModalVisible(false)}>
                                Hủy
                            </Button>
                            <Button type="primary" htmlType="submit">
                                {editingStaff ? 'Cập nhật' : 'Tạo mới'}
                            </Button>
                        </Space>
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
};

export default StaffManagement;
