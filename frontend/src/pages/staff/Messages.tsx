import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Input, List, Avatar, Tag, Button, Typography, message as antdMessage, Spin } from 'antd';
import { SearchOutlined, FacebookOutlined, MessageOutlined, CheckCircleOutlined, MailOutlined, PhoneOutlined, EnvironmentOutlined, CalendarOutlined, ShoppingOutlined } from '@ant-design/icons';
import apiClient from '../../api/client';

const { Title, Text } = Typography;
const { TextArea } = Input;

interface Customer {
    id: number;
    name: string;
    platform: string;
    latest_message: string;
    latest_message_time: string;
    status: string;
}

interface Message {
    id: number;
    content: string;
    direction: 'incoming' | 'outgoing';
    created_at: string;
}

interface CustomerDetail {
    id: number;
    name: string;
    email: string;
    phone: string;
    platform: string;
    city: string;
    total_orders: number;
    created_at: string;
}

const StaffMessages: React.FC = () => {
    const [customers, setCustomers] = useState<Customer[]>([]);
    const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const [customerDetail, setCustomerDetail] = useState<CustomerDetail | null>(null);
    const [newMessage, setNewMessage] = useState('');
    const [searchText, setSearchText] = useState('');
    const [loading, setLoading] = useState(false);
    const [sendingMessage, setSendingMessage] = useState(false);

    useEffect(() => {
        fetchCustomers();
    }, []);

    const fetchCustomers = async () => {
        try {
            setLoading(true);
            const response = await apiClient.get<Customer[]>('/api/staff/customers');
            setCustomers(response.data);
        } catch (error) {
            antdMessage.error('Không thể tải danh sách khách hàng');
        } finally {
            setLoading(false);
        }
    };

    const handleSelectCustomer = async (customer: Customer) => {
        setSelectedCustomer(customer);
        try {
            // Lấy lịch sử chat
            const messagesResponse = await apiClient.get<Message[]>(`/api/staff/customers/${customer.id}/messages`);
            setMessages(messagesResponse.data);

            // Lấy thông tin chi tiết khách hàng
            const detailResponse = await apiClient.get<CustomerDetail>(`/api/staff/customers/${customer.id}`);
            setCustomerDetail(detailResponse.data);
        } catch (error) {
            antdMessage.error('Không thể tải thông tin khách hàng');
        }
    };

    const handleSendMessage = async () => {
        if (!newMessage.trim() || !selectedCustomer) return;

        try {
            setSendingMessage(true);
            const response = await apiClient.post(`/api/staff/customers/${selectedCustomer.id}/messages`, null, {
                params: { content: newMessage }
            });

            setMessages([...messages, response.data]);
            setNewMessage('');
            antdMessage.success('Đã gửi tin nhắn');
        } catch (error) {
            antdMessage.error('Không thể gửi tin nhắn');
        } finally {
            setSendingMessage(false);
        }
    };

    const handleMarkComplete = async () => {
        if (!selectedCustomer) return;

        try {
            // Tìm message_id từ customer
            const lastMessage = messages.find(m => m.direction === 'incoming');
            if (!lastMessage) {
                antdMessage.warning('Không tìm thấy tin nhắn để đánh dấu');
                return;
            }

            await apiClient.put(`/api/staff/messages/${lastMessage.id}/complete`);
            antdMessage.success('Đã đánh dấu hoàn thành');

            // Cập nhật trạng thái trong danh sách
            setCustomers(customers.map(c =>
                c.id === selectedCustomer.id ? { ...c, status: 'completed' } : c
            ));
            setSelectedCustomer({ ...selectedCustomer, status: 'completed' });
        } catch (error) {
            antdMessage.error('Không thể đánh dấu hoàn thành');
        }
    };

    const filteredCustomers = customers.filter(c =>
        c.name.toLowerCase().includes(searchText.toLowerCase())
    );

    const getPlatformIcon = (platform: string) => {
        switch (platform?.toLowerCase()) {
            case 'facebook':
                return <FacebookOutlined style={{ color: '#1877f2' }} />;
            case 'zalo':
                return <MessageOutlined style={{ color: '#0068ff' }} />;
            case 'email':
                return <MailOutlined style={{ color: '#ea4335' }} />;
            default:
                return <MessageOutlined />;
        }
    };

    return (
        <div className="messages-page">
            <Row gutter={16} style={{ height: 'calc(100vh - 100px)' }}>
                {/* Danh sách khách hàng - Cột trái */}
                <Col span={6}>
                    <Card
                        className="customer-list-card"
                        title="Danh sách khách hàng"
                        style={{ height: '100%', overflow: 'hidden' }}
                    >
                        <Input
                            placeholder="Tìm kiếm khách hàng..."
                            prefix={<SearchOutlined />}
                            value={searchText}
                            onChange={(e) => setSearchText(e.target.value)}
                            style={{ marginBottom: 16 }}
                        />
                        <div style={{ height: 'calc(100% - 80px)', overflowY: 'auto' }}>
                            {loading ? (
                                <div style={{ textAlign: 'center', padding: 40 }}>
                                    <Spin />
                                </div>
                            ) : (
                                <List
                                    dataSource={filteredCustomers}
                                    renderItem={(customer) => (
                                        <List.Item
                                            className={`customer-item ${selectedCustomer?.id === customer.id ? 'selected' : ''}`}
                                            onClick={() => handleSelectCustomer(customer)}
                                            style={{ cursor: 'pointer', padding: '12px 8px' }}
                                        >
                                            <List.Item.Meta
                                                avatar={
                                                    <Avatar style={{ backgroundColor: '#1890ff' }}>
                                                        {getPlatformIcon(customer.platform)}
                                                    </Avatar>
                                                }
                                                title={
                                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                        <Text strong>{customer.name}</Text>
                                                        <Tag color={customer.status === 'completed' ? 'green' : 'orange'} style={{ fontSize: 10 }}>
                                                            {customer.status === 'completed' ? 'Hoàn thành' : 'Đang xử lý'}
                                                        </Tag>
                                                    </div>
                                                }
                                                description={
                                                    <div>
                                                        <Text ellipsis style={{ fontSize: 12, color: '#888' }}>
                                                            {customer.latest_message || 'Chưa có tin nhắn'}
                                                        </Text>
                                                        <div style={{ fontSize: 11, color: '#aaa', marginTop: 4 }}>
                                                            Từ {customer.platform}
                                                        </div>
                                                    </div>
                                                }
                                            />
                                        </List.Item>
                                    )}
                                />
                            )}
                        </div>
                    </Card>
                </Col>

                {/* Cửa sổ chat - Cột giữa */}
                <Col span={12}>
                    <Card
                        className="chat-window-card"
                        style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
                        title={
                            selectedCustomer ? (
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <div>
                                        <Text strong>{selectedCustomer.name}</Text>
                                        <div style={{ fontSize: 12, color: '#888' }}>
                                            Kênh: {selectedCustomer.platform}
                                        </div>
                                    </div>
                                    {selectedCustomer.status !== 'completed' && (
                                        <Button
                                            type="primary"
                                            icon={<CheckCircleOutlined />}
                                            onClick={handleMarkComplete}
                                            style={{ background: '#52c41a', borderColor: '#52c41a' }}
                                        >
                                            Đánh dấu Hoàn thành
                                        </Button>
                                    )}
                                </div>
                            ) : 'Chọn khách hàng để bắt đầu chat'
                        }
                    >
                        {selectedCustomer ? (
                            <>
                                <div className="messages-container" style={{ flex: 1, overflowY: 'auto', padding: '16px 0', marginBottom: 16 }}>
                                    {messages.map((msg) => (
                                        <div
                                            key={msg.id}
                                            className={`message-bubble ${msg.direction}`}
                                            style={{
                                                marginBottom: 12,
                                                display: 'flex',
                                                justifyContent: msg.direction === 'outgoing' ? 'flex-end' : 'flex-start'
                                            }}
                                        >
                                            <div
                                                style={{
                                                    maxWidth: '70%',
                                                    padding: '10px 14px',
                                                    borderRadius: 12,
                                                    backgroundColor: msg.direction === 'outgoing' ? '#1890ff' : '#f0f0f0',
                                                    color: msg.direction === 'outgoing' ? 'white' : 'black'
                                                }}
                                            >
                                                <div>{msg.content}</div>
                                                <div style={{
                                                    fontSize: 10,
                                                    marginTop: 4,
                                                    opacity: 0.7,
                                                    textAlign: 'right'
                                                }}>
                                                    {new Date(msg.created_at).toLocaleTimeString('vi-VN', {
                                                        hour: '2-digit',
                                                        minute: '2-digit'
                                                    })}
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                                <div className="message-input-container">
                                    <TextArea
                                        placeholder="Nhập tin nhắn..."
                                        value={newMessage}
                                        onChange={(e) => setNewMessage(e.target.value)}
                                        onPressEnter={(e) => {
                                            if (!e.shiftKey) {
                                                e.preventDefault();
                                                handleSendMessage();
                                            }
                                        }}
                                        autoSize={{ minRows: 2, maxRows: 4 }}
                                        style={{ marginBottom: 8 }}
                                    />
                                    <Button
                                        type="primary"
                                        icon={<MessageOutlined />}
                                        onClick={handleSendMessage}
                                        loading={sendingMessage}
                                        block
                                    >
                                        Gửi tin nhắn
                                    </Button>
                                </div>
                            </>
                        ) : (
                            <div style={{ textAlign: 'center', padding: 60, color: '#999' }}>
                                <MessageOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                                <div>Chọn một khách hàng để xem tin nhắn</div>
                            </div>
                        )}
                    </Card>
                </Col>

                {/* Thông tin khách hàng - Cột phải */}
                <Col span={6}>
                    <Card
                        className="customer-info-card"
                        title="Thông tin Khách hàng"
                        style={{ height: '100%' }}
                    >
                        {customerDetail ? (
                            <div className="customer-detail">
                                <div style={{ textAlign: 'center', marginBottom: 24 }}>
                                    <Avatar size={80} style={{ backgroundColor: '#1890ff', fontSize: 32 }}>
                                        {customerDetail.name?.charAt(0) || 'K'}
                                    </Avatar>
                                    <Title level={4} style={{ marginTop: 12, marginBottom: 4 }}>
                                        {customerDetail.name || 'Không rõ'}
                                    </Title>
                                    <Text type="secondary">Từ kênh: {customerDetail.platform}</Text>
                                </div>

                                <div className="info-section">
                                    <div className="info-item">
                                        <MailOutlined style={{ color: '#1890ff', marginRight: 8 }} />
                                        <div>
                                            <Text type="secondary" style={{ fontSize: 12 }}>Email</Text>
                                            <div><Text>{customerDetail.email || 'Chưa có'}</Text></div>
                                        </div>
                                    </div>

                                    <div className="info-item">
                                        <PhoneOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                                        <div>
                                            <Text type="secondary" style={{ fontSize: 12 }}>Số điện thoại</Text>
                                            <div><Text>{customerDetail.phone || 'Chưa có'}</Text></div>
                                        </div>
                                    </div>

                                    <div className="info-divider" />

                                    <Title level={5} style={{ marginTop: 16, marginBottom: 12 }}>CHI TIẾT KHÁC</Title>

                                    <div className="info-item">
                                        <CalendarOutlined style={{ color: '#faad14', marginRight: 8 }} />
                                        <div>
                                            <Text type="secondary" style={{ fontSize: 12 }}>Ngày tham gia</Text>
                                            <div><Text>{new Date(customerDetail.created_at).toLocaleDateString('vi-VN')}</Text></div>
                                        </div>
                                    </div>

                                    <div className="info-item">
                                        <ShoppingOutlined style={{ color: '#722ed1', marginRight: 8 }} />
                                        <div>
                                            <Text type="secondary" style={{ fontSize: 12 }}>Tổng đơn hàng</Text>
                                            <div><Text strong>{customerDetail.total_orders || 0}</Text></div>
                                        </div>
                                    </div>

                                    <div className="info-item">
                                        <EnvironmentOutlined style={{ color: '#eb2f96', marginRight: 8 }} />
                                        <div>
                                            <Text type="secondary" style={{ fontSize: 12 }}>Thành phố</Text>
                                            <div><Text>{customerDetail.city || 'Chưa có'}</Text></div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div style={{ textAlign: 'center', padding: 60, color: '#999' }}>
                                Chọn khách hàng để xem thông tin
                            </div>
                        )}
                    </Card>
                </Col>
            </Row>
        </div>
    );
};

export default StaffMessages;
