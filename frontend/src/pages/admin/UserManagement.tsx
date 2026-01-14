import React, { useEffect, useState } from 'react';
import { Card, Table, Button, Modal, Form, Input, Select, message, Space, Tag } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import apiClient from '../../api/client';
import { User, Department } from '../../types';

const { Option } = Select;

const UserManagement: React.FC = () => {
    const [users, setUsers] = useState<User[]>([]);
    const [departments, setDepartments] = useState<Department[]>([]);
    const [loading, setLoading] = useState(false);
    const [modalVisible, setModalVisible] = useState(false);
    const [editingUser, setEditingUser] = useState<User | null>(null);
    const [form] = Form.useForm();

    useEffect(() => {
        fetchUsers();
        fetchDepartments();
    }, []);

    const fetchUsers = async () => {
        try {
            setLoading(true);
            const response = await apiClient.get<User[]>('/api/admin/users');
            setUsers(response.data);
        } catch (error) {
            message.error('Không thể tải danh sách người dùng');
        } finally {
            setLoading(false);
        }
    };

    const fetchDepartments = async () => {
        try {
            const response = await apiClient.get<Department[]>('/api/admin/departments');
            setDepartments(response.data);
        } catch (error) {
            console.error('Failed to fetch departments');
        }
    };

    const handleCreate = () => {
        setEditingUser(null);
        form.resetFields();
        setModalVisible(true);
    };

    const handleEdit = (user: User) => {
        setEditingUser(user);
        form.setFieldsValue(user);
        setModalVisible(true);
    };

    const handleDelete = async (userId: number) => {
        try {
            await apiClient.delete(`/api/admin/users/${userId}`);
            message.success('Đã xóa người dùng');
            fetchUsers();
        } catch (error) {
            message.error('Không thể xóa người dùng');
        }
    };

    const handleSubmit = async (values: any) => {
        try {
            if (editingUser) {
                await apiClient.put(`/api/admin/users/${editingUser.id}`, values);
                message.success('Đã cập nhật người dùng');
            } else {
                await apiClient.post('/api/admin/users', values);
                message.success('Đã tạo người dùng mới');
            }
            setModalVisible(false);
            fetchUsers();
        } catch (error: any) {
            message.error(error.response?.data?.detail || 'Có lỗi xảy ra');
        }
    };

    const handleChangeRole = async (userId: number, newRole: string) => {
        try {
            await apiClient.put(`/api/admin/users/${userId}/role?new_role=${newRole}`);
            message.success('Đã thay đổi vai trò');
            fetchUsers();
        } catch (error) {
            message.error('Không thể thay đổi vai trò');
        }
    };

    const columns = [
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
            render: (role: string, record: User) => (
                <Select
                    value={role}
                    style={{ width: 120 }}
                    onChange={(value) => handleChangeRole(record.id, value)}
                >
                    <Option value="admin">Admin</Option>
                    <Option value="manager">Manager</Option>
                    <Option value="staff">Staff</Option>
                </Select>
            ),
        },
        {
            title: 'Trạng thái',
            dataIndex: 'is_active',
            key: 'is_active',
            render: (isActive: boolean) => (
                <Tag color={isActive ? 'green' : 'red'}>
                    {isActive ? 'Hoạt động' : 'Không hoạt động'}
                </Tag>
            ),
        },
        {
            title: 'Hành động',
            key: 'actions',
            render: (_: any, record: User) => (
                <Space>
                    <Button
                        type="link"
                        icon={<EditOutlined />}
                        onClick={() => handleEdit(record)}
                    >
                        Sửa
                    </Button>
                    <Button
                        type="link"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={() => handleDelete(record.id)}
                    >
                        Xóa
                    </Button>
                </Space>
            ),
        },
    ];

    return (
        <div className="page-container">
            <Card
                title="Quản lý người dùng"
                extra={
                    <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                        Thêm người dùng
                    </Button>
                }
            >
                <Table
                    dataSource={users}
                    columns={columns}
                    rowKey="id"
                    loading={loading}
                />
            </Card>

            <Modal
                title={editingUser ? 'Sửa người dùng' : 'Thêm người dùng mới'}
                open={modalVisible}
                onCancel={() => setModalVisible(false)}
                onOk={() => form.submit()}
            >
                <Form form={form} layout="vertical" onFinish={handleSubmit}>
                    <Form.Item
                        name="email"
                        label="Email"
                        rules={[
                            { required: true, message: 'Vui lòng nhập email' },
                            { type: 'email', message: 'Email không hợp lệ' },
                        ]}
                    >
                        <Input />
                    </Form.Item>

                    {!editingUser && (
                        <Form.Item
                            name="password"
                            label="Mật khẩu"
                            rules={[{ required: true, message: 'Vui lòng nhập mật khẩu' }]}
                        >
                            <Input.Password />
                        </Form.Item>
                    )}

                    <Form.Item
                        name="full_name"
                        label="Họ tên"
                        rules={[{ required: true, message: 'Vui lòng nhập họ tên' }]}
                    >
                        <Input />
                    </Form.Item>

                    <Form.Item name="phone" label="Số điện thoại">
                        <Input />
                    </Form.Item>

                    <Form.Item
                        name="role"
                        label="Vai trò"
                        rules={[{ required: true, message: 'Vui lòng chọn vai trò' }]}
                    >
                        <Select>
                            <Option value="admin">Admin</Option>
                            <Option value="manager">Manager</Option>
                            <Option value="staff">Staff</Option>
                        </Select>
                    </Form.Item>

                    <Form.Item name="department_id" label="Phòng ban">
                        <Select allowClear>
                            {departments.map((dept) => (
                                <Option key={dept.id} value={dept.id}>
                                    {dept.name}
                                </Option>
                            ))}
                        </Select>
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
};

export default UserManagement;
