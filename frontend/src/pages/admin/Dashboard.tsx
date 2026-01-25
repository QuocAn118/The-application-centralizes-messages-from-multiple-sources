import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Typography, Tabs, DatePicker } from 'antd';
import { UserOutlined, TeamOutlined, BarChartOutlined } from '@ant-design/icons';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
    PieChart, Pie, Cell
} from 'recharts';
import apiClient from '../../api/client';

const { Title } = Typography;
const { RangePicker } = DatePicker;

// Mock data cho biểu đồ (Trong thực tế nên lấy từ API stats)
const deptData = [
    { name: 'Kinh doanh', tin_nhan: 400, yeu_cau: 240 },
    { name: 'Kỹ thuật', tin_nhan: 300, yeu_cau: 139 },
    { name: 'CSKH', tin_nhan: 200, yeu_cau: 980 },
    { name: 'Marketing', tin_nhan: 278, yeu_cau: 390 },
];

const requestTypeData = [
    { name: 'Nghỉ phép', value: 400 },
    { name: 'Tăng lương', value: 300 },
    { name: 'Thiết bị', value: 300 },
    { name: 'Khác', value: 200 },
];

const staffPerformanceData = [
    { name: 'Nguyễn Văn A', mess: 120, req: 10 },
    { name: 'Trần Thị B', mess: 98, req: 5 },
    { name: 'Lê Văn C', mess: 86, req: 8 },
    { name: 'Phạm Thị D', mess: 99, req: 12 },
    { name: 'Hoàng Văn E', mess: 85, req: 6 },
];

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

const AdminDashboard: React.FC = () => {
    const [stats, setStats] = useState({ users: 0, keywords: 0, customers: 0 });

    useEffect(() => {
        fetchDashboardData();
    }, []);

    const fetchDashboardData = async () => {
        try {
            // Lấy số liệu tổng quan thực tế
            const [usersRes, keywordsRes] = await Promise.all([
                apiClient.get('/api/admin/users'),
                apiClient.get('/api/admin/keywords'),
            ]);
            
            setStats({
                users: usersRes.data.length,
                keywords: keywordsRes.data.length,
                customers: 125, // Mock number or fetch from real API if available
            });
        } catch (error) {
            console.error('Error fetching dashboard data', error);
        }
    };

    return (
        <div className="page-container">
            <div className="page-header">
                <Title level={2} className="page-title">Dashboard Quản trị</Title>
                <div style={{ float: 'right' }}>
                     <RangePicker />
                </div>
            </div>

            <Row gutter={[16, 16]}>
                <Col xs={24} sm={8}>
                    <Card>
                        <Statistic
                            title="Tổng người dùng"
                            value={stats.users}
                            prefix={<UserOutlined />}
                            valueStyle={{ color: '#3f8600' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={8}>
                    <Card>
                        <Statistic
                            title="Tổng từ khóa"
                            value={stats.keywords}
                            prefix={<BarChartOutlined />}
                            valueStyle={{ color: '#cf1322' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={8}>
                    <Card>
                        <Statistic
                            title="Tổng khách hàng"
                            value={stats.customers}
                            prefix={<TeamOutlined />}
                            valueStyle={{ color: '#1890ff' }}
                        />
                    </Card>
                </Col>
            </Row>

            <Tabs defaultActiveKey="1" style={{ marginTop: 24, background: '#fff', padding: 24, borderRadius: 8 }}>
                <Tabs.TabPane tab="Thống kê theo Phòng ban" key="1">
                    <div style={{ height: 400 }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart
                                data={deptData}
                                margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                            >
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="name" />
                                <YAxis />
                                <Tooltip />
                                <Legend />
                                <Bar dataKey="tin_nhan" name="Tin nhắn xử lý" fill="#8884d8" />
                                <Bar dataKey="yeu_cau" name="Yêu cầu nội bộ" fill="#82ca9d" />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </Tabs.TabPane>
                
                <Tabs.TabPane tab="Theo Loại Yêu cầu" key="2">
                    <Row>
                        <Col span={12}>
                            <div style={{ height: 400 }}>
                                <ResponsiveContainer width="100%" height="100%">
                                    <PieChart>
                                        <Pie
                                            data={requestTypeData}
                                            cx="50%"
                                            cy="50%"
                                            labelLine={false}
                                            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                                            outerRadius={150}
                                            fill="#8884d8"
                                            dataKey="value"
                                        >
                                            {requestTypeData.map((entry, index) => (
                                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                            ))}
                                        </Pie>
                                        <Tooltip />
                                    </PieChart>
                                </ResponsiveContainer>
                            </div>
                        </Col>
                        <Col span={12}>
                             {/* Thêm biểu đồ phụ hoặc thông tin chi tiết */}
                             <Card title="Ghi chú" bordered={false}>
                                 <p>Biểu đồ thể hiện tỷ lệ các loại yêu cầu được gửi lên trong tháng.</p>
                                 <p>Nghỉ phép chiếm tỷ trọng cao nhất.</p>
                             </Card>
                        </Col>
                    </Row>
                </Tabs.TabPane>

                <Tabs.TabPane tab="Hiệu suất Nhân viên" key="3">
                    <div style={{ height: 400 }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart
                                layout="vertical"
                                data={staffPerformanceData}
                                margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                            >
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis type="number" />
                                <YAxis dataKey="name" type="category" width={150} />
                                <Tooltip />
                                <Legend />
                                <Bar dataKey="mess" name="Tin nhắn" fill="#1890ff" />
                                <Bar dataKey="req" name="Yêu cầu" fill="#ffc658" />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </Tabs.TabPane>
            </Tabs>
        </div>
    );
};

export default AdminDashboard;
