import React, { useState } from 'react';
import { Form, Input, Button, Card, message, Typography } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { LoginRequest } from '../types';

const { Title, Text } = Typography;

const Login: React.FC = () => {
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();
    const login = useAuthStore((state) => state.login);
    const user = useAuthStore((state) => state.user);

    const onFinish = async (values: LoginRequest) => {
        setLoading(true);
        try {
            await login(values);
            message.success('Đăng nhập thành công!');

            // Redirect based on role
            const currentUser = useAuthStore.getState().user;
            if (currentUser) {
                switch (currentUser.role) {
                    case 'admin':
                        navigate('/admin/dashboard');
                        break;
                    case 'manager':
                        navigate('/manager/dashboard');
                        break;
                    case 'staff':
                        navigate('/staff/dashboard');
                        break;
                    default:
                        navigate('/');
                }
            }
        } catch (error: any) {
            message.error(error.response?.data?.detail || 'Đăng nhập thất bại');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'linear-gradient(135deg, #1890ff 0%, #40a9ff 100%)',
            padding: '20px'
        }}>
            <Card
                style={{
                    width: '100%',
                    maxWidth: 400,
                    boxShadow: '0 8px 24px rgba(0, 0, 0, 0.15)',
                    borderRadius: 12
                }}
            >
                <div style={{ textAlign: 'center', marginBottom: 32 }}>
                    <Title level={2} style={{ color: '#1890ff', marginBottom: 8 }}>
                        OmniChat
                    </Title>
                    <Text type="secondary">Hệ thống Quản lý Đa kênh</Text>
                </div>

                <Form
                    name="login"
                    onFinish={onFinish}
                    autoComplete="off"
                    size="large"
                >
                    <Form.Item
                        name="email"
                        rules={[
                            { required: true, message: 'Vui lòng nhập email!' },
                            { type: 'email', message: 'Email không hợp lệ!' }
                        ]}
                    >
                        <Input
                            prefix={<UserOutlined />}
                            placeholder="Email"
                        />
                    </Form.Item>

                    <Form.Item
                        name="password"
                        rules={[{ required: true, message: 'Vui lòng nhập mật khẩu!' }]}
                    >
                        <Input.Password
                            prefix={<LockOutlined />}
                            placeholder="Mật khẩu"
                        />
                    </Form.Item>

                    <Form.Item>
                        <Button
                            type="primary"
                            htmlType="submit"
                            loading={loading}
                            block
                            style={{ height: 45 }}
                        >
                            Đăng nhập
                        </Button>
                    </Form.Item>
                </Form>

                <div style={{ marginTop: 24, padding: 16, background: '#f0f5ff', borderRadius: 8 }}>
                    <Text strong style={{ display: 'block', marginBottom: 8 }}>Tài khoản demo:</Text>
                    <Text style={{ display: 'block', fontSize: 12 }}>
                        Admin: admin@omnichat.com / admin123
                    </Text>
                    <Text style={{ display: 'block', fontSize: 12 }}>
                        Manager: manager.sales@omnichat.com / manager123
                    </Text>
                    <Text style={{ display: 'block', fontSize: 12 }}>
                        Staff: staff1@omnichat.com / staff123
                    </Text>
                </div>
            </Card>
        </div>
    );
};

export default Login;
