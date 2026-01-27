import React, { useEffect, useState } from 'react';
import {
    Card, Row, Col, Typography, Spin, DatePicker, Select, Tabs, Table, Tag, Statistic, Space
} from 'antd';
import {
    BarChartOutlined, PieChartOutlined, LineChartOutlined, TeamOutlined,
    UserOutlined, FileTextOutlined, ClockCircleOutlined, RiseOutlined, FallOutlined
} from '@ant-design/icons';
import {
    Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale,
    BarElement, Title as ChartTitle, PointElement, LineElement, Filler
} from 'chart.js';
import { Bar, Pie, Line, Doughnut } from 'react-chartjs-2';
import dayjs from 'dayjs';
import apiClient from '../../api/client';

ChartJS.register(
    ArcElement, Tooltip, Legend, CategoryScale, LinearScale,
    BarElement, ChartTitle, PointElement, LineElement, Filler
);

const { Title, Paragraph, Text } = Typography;
const { RangePicker } = DatePicker;
const { TabPane } = Tabs;

interface StatsByDepartment {
    department_id: number;
    department_name: string;
    total_messages: number;
    completed_messages: number;
    pending_messages: number;
    total_staff: number;
}

interface StatsByUser {
    user_id: number;
    user_name: string;
    role: string;
    department_name: string;
    total_messages: number;
    completed_messages: number;
    avg_completion_time: number | null;
}

interface StatsByRequestType {
    request_type: string;
    total_requests: number;
    approved_requests: number;
    rejected_requests: number;
    pending_requests: number;
}

interface Department {
    id: number;
    name: string;
}

const AdminStatistics: React.FC = () => {
    const [loading, setLoading] = useState(true);
    const [departments, setDepartments] = useState<Department[]>([]);
    const [statsByDepartment, setStatsByDepartment] = useState<StatsByDepartment[]>([]);
    const [statsByUser, setStatsByUser] = useState<StatsByUser[]>([]);
    const [statsByRequestType, setStatsByRequestType] = useState<StatsByRequestType[]>([]);
    const [selectedDepartment, setSelectedDepartment] = useState<number | null>(null);
    const [selectedRole, setSelectedRole] = useState<string | null>(null);
    const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);

    useEffect(() => {
        fetchAllData();
    }, [dateRange]);

    const fetchAllData = async () => {
        try {
            setLoading(true);
            const params: any = {};
            if (dateRange) {
                params.start_date = dateRange[0].format('YYYY-MM-DD');
                params.end_date = dateRange[1].format('YYYY-MM-DD');
            }

            const [deptRes, deptStatsRes, userStatsRes, reqStatsRes] = await Promise.all([
                apiClient.get<Department[]>('/api/admin/departments'),
                apiClient.get<StatsByDepartment[]>('/api/admin/statistics/by-department', { params }),
                apiClient.get<StatsByUser[]>('/api/admin/statistics/by-user', { params }),
                apiClient.get<StatsByRequestType[]>('/api/admin/statistics/by-request-type', { params })
            ]);

            setDepartments(deptRes.data);
            setStatsByDepartment(deptStatsRes.data);
            setStatsByUser(userStatsRes.data);
            setStatsByRequestType(reqStatsRes.data);
        } catch (error) {
            console.error('Error fetching statistics:', error);
        } finally {
            setLoading(false);
        }
    };

    // Màu sắc cho biểu đồ
    const chartColors = [
        'rgba(24, 144, 255, 0.8)',
        'rgba(82, 196, 26, 0.8)',
        'rgba(250, 173, 20, 0.8)',
        'rgba(114, 46, 209, 0.8)',
        'rgba(245, 34, 45, 0.8)',
        'rgba(19, 194, 194, 0.8)',
        'rgba(235, 47, 150, 0.8)',
        'rgba(47, 84, 235, 0.8)',
    ];

    // ===== BIỂU ĐỒ THEO PHÒNG BAN =====
    const getDepartmentBarData = () => ({
        labels: statsByDepartment.map(d => d.department_name),
        datasets: [
            {
                label: 'Hoàn thành',
                data: statsByDepartment.map(d => d.completed_messages),
                backgroundColor: 'rgba(82, 196, 26, 0.8)',
                borderRadius: 4,
            },
            {
                label: 'Chờ xử lý',
                data: statsByDepartment.map(d => d.pending_messages),
                backgroundColor: 'rgba(250, 173, 20, 0.8)',
                borderRadius: 4,
            }
        ]
    });

    const getDepartmentPieData = () => ({
        labels: statsByDepartment.map(d => d.department_name),
        datasets: [{
            data: statsByDepartment.map(d => d.total_messages),
            backgroundColor: chartColors.slice(0, statsByDepartment.length),
            borderWidth: 2,
            borderColor: '#fff',
        }]
    });

    const getDepartmentStaffData = () => ({
        labels: statsByDepartment.map(d => d.department_name),
        datasets: [{
            label: 'Số nhân viên',
            data: statsByDepartment.map(d => d.total_staff),
            backgroundColor: chartColors.slice(0, statsByDepartment.length),
            borderRadius: 4,
        }]
    });

    // ===== BIỂU ĐỒ THEO NHÂN VIÊN =====
    const getFilteredUserStats = () => {
        let filtered = statsByUser;
        if (selectedDepartment) {
            filtered = filtered.filter(u => 
                departments.find(d => d.id === selectedDepartment)?.name === u.department_name
            );
        }
        if (selectedRole) {
            filtered = filtered.filter(u => u.role === selectedRole);
        }
        return filtered.slice(0, 15); // Giới hạn 15 người để hiển thị rõ
    };

    const getUserBarData = () => {
        const filtered = getFilteredUserStats();
        return {
            labels: filtered.map(u => u.user_name),
            datasets: [
                {
                    label: 'Tin nhắn xử lý',
                    data: filtered.map(u => u.total_messages),
                    backgroundColor: 'rgba(24, 144, 255, 0.8)',
                    borderRadius: 4,
                },
                {
                    label: 'Hoàn thành',
                    data: filtered.map(u => u.completed_messages),
                    backgroundColor: 'rgba(82, 196, 26, 0.8)',
                    borderRadius: 4,
                }
            ]
        };
    };

    const getUserPerformanceData = () => {
        const filtered = getFilteredUserStats().filter(u => u.total_messages > 0);
        return {
            labels: filtered.map(u => u.user_name),
            datasets: [{
                label: 'Tỷ lệ hoàn thành (%)',
                data: filtered.map(u => Math.round((u.completed_messages / u.total_messages) * 100)),
                backgroundColor: filtered.map(u => {
                    const rate = (u.completed_messages / u.total_messages) * 100;
                    if (rate >= 80) return 'rgba(82, 196, 26, 0.8)';
                    if (rate >= 50) return 'rgba(250, 173, 20, 0.8)';
                    return 'rgba(245, 34, 45, 0.8)';
                }),
                borderRadius: 4,
            }]
        };
    };

    // ===== BIỂU ĐỒ THEO LOẠI YÊU CẦU =====
    const requestTypeLabels: Record<string, string> = {
        leave: 'Nghỉ phép',
        salary_increase: 'Tăng lương',
        transfer: 'Chuyển phòng',
        other: 'Khác'
    };

    const getRequestTypeBarData = () => ({
        labels: statsByRequestType.map(r => requestTypeLabels[r.request_type] || r.request_type),
        datasets: [
            {
                label: 'Đã duyệt',
                data: statsByRequestType.map(r => r.approved_requests),
                backgroundColor: 'rgba(82, 196, 26, 0.8)',
                borderRadius: 4,
            },
            {
                label: 'Từ chối',
                data: statsByRequestType.map(r => r.rejected_requests),
                backgroundColor: 'rgba(245, 34, 45, 0.8)',
                borderRadius: 4,
            },
            {
                label: 'Chờ duyệt',
                data: statsByRequestType.map(r => r.pending_requests),
                backgroundColor: 'rgba(250, 173, 20, 0.8)',
                borderRadius: 4,
            }
        ]
    });

    const getRequestTypeDoughnutData = () => ({
        labels: statsByRequestType.map(r => requestTypeLabels[r.request_type] || r.request_type),
        datasets: [{
            data: statsByRequestType.map(r => r.total_requests),
            backgroundColor: chartColors.slice(0, statsByRequestType.length),
            borderWidth: 2,
            borderColor: '#fff',
        }]
    });

    // ===== BẢNG DỮ LIỆU =====
    const departmentColumns = [
        { title: 'Phòng ban', dataIndex: 'department_name', key: 'department_name' },
        { title: 'Tổng tin nhắn', dataIndex: 'total_messages', key: 'total_messages', sorter: (a: StatsByDepartment, b: StatsByDepartment) => a.total_messages - b.total_messages },
        { title: 'Hoàn thành', dataIndex: 'completed_messages', key: 'completed_messages', render: (v: number) => <Tag color="success">{v}</Tag> },
        { title: 'Chờ xử lý', dataIndex: 'pending_messages', key: 'pending_messages', render: (v: number) => <Tag color="warning">{v}</Tag> },
        { title: 'Nhân viên', dataIndex: 'total_staff', key: 'total_staff' },
        {
            title: 'Tỷ lệ hoàn thành',
            key: 'rate',
            render: (_: any, record: StatsByDepartment) => {
                const rate = record.total_messages > 0 ? Math.round((record.completed_messages / record.total_messages) * 100) : 0;
                const color = rate >= 80 ? 'green' : rate >= 50 ? 'orange' : 'red';
                return <Tag color={color}>{rate}%</Tag>;
            }
        }
    ];

    const userColumns = [
        { title: 'Nhân viên', dataIndex: 'user_name', key: 'user_name' },
        {
            title: 'Vai trò', dataIndex: 'role', key: 'role',
            render: (role: string) => (
                <Tag color={role === 'manager' ? 'purple' : 'blue'}>
                    {role === 'manager' ? 'Quản lý' : 'Nhân viên'}
                </Tag>
            )
        },
        { title: 'Phòng ban', dataIndex: 'department_name', key: 'department_name' },
        { title: 'Tổng tin nhắn', dataIndex: 'total_messages', key: 'total_messages', sorter: (a: StatsByUser, b: StatsByUser) => a.total_messages - b.total_messages },
        { title: 'Hoàn thành', dataIndex: 'completed_messages', key: 'completed_messages', render: (v: number) => <Tag color="success">{v}</Tag> },
        {
            title: 'Tỷ lệ',
            key: 'rate',
            render: (_: any, record: StatsByUser) => {
                const rate = record.total_messages > 0 ? Math.round((record.completed_messages / record.total_messages) * 100) : 0;
                const color = rate >= 80 ? 'green' : rate >= 50 ? 'orange' : 'red';
                return <Tag color={color}>{rate}%</Tag>;
            }
        },
        {
            title: 'Thời gian TB',
            dataIndex: 'avg_completion_time',
            key: 'avg_completion_time',
            render: (v: number | null) => {
                if (!v) return '-';
                const minutes = Math.round(v / 60);
                return `${minutes} phút`;
            }
        }
    ];

    // Tính tổng thống kê
    const totalStats = {
        totalMessages: statsByDepartment.reduce((acc, d) => acc + d.total_messages, 0),
        completedMessages: statsByDepartment.reduce((acc, d) => acc + d.completed_messages, 0),
        pendingMessages: statsByDepartment.reduce((acc, d) => acc + d.pending_messages, 0),
        totalStaff: statsByDepartment.reduce((acc, d) => acc + d.total_staff, 0),
        totalRequests: statsByRequestType.reduce((acc, r) => acc + r.total_requests, 0),
        pendingRequests: statsByRequestType.reduce((acc, r) => acc + r.pending_requests, 0),
    };

    if (loading) {
        return (
            <div className="loading-container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
                <Spin size="large" />
            </div>
        );
    }

    return (
        <div className="page-container">
            <div className="page-header" style={{ marginBottom: 24 }}>
                <Title level={2}>
                    <BarChartOutlined /> Thống kê hệ thống
                </Title>
                <Paragraph type="secondary">
                    Thống kê chi tiết theo phòng ban, nhân viên, loại yêu cầu và khoảng thời gian
                </Paragraph>
            </div>

            {/* Bộ lọc thời gian */}
            <Card style={{ marginBottom: 24 }}>
                <Space size="large" wrap>
                    <div>
                        <Text strong>Lọc theo thời gian:</Text>
                        <RangePicker
                            style={{ marginLeft: 12 }}
                            format="DD/MM/YYYY"
                            onChange={(dates) => setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs] | null)}
                            placeholder={['Từ ngày', 'Đến ngày']}
                        />
                    </div>
                </Space>
            </Card>

            {/* Thống kê tổng quan */}
            <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
                <Col xs={24} sm={12} lg={4}>
                    <Card className="stat-card">
                        <Statistic
                            title={<span style={{ color: 'white' }}>Tổng tin nhắn</span>}
                            value={totalStats.totalMessages}
                            prefix={<BarChartOutlined />}
                            valueStyle={{ color: 'white' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={4}>
                    <Card className="stat-card" style={{ background: 'linear-gradient(135deg, #52c41a 0%, #73d13d 100%)' }}>
                        <Statistic
                            title={<span style={{ color: 'white' }}>Đã xử lý</span>}
                            value={totalStats.completedMessages}
                            prefix={<RiseOutlined />}
                            valueStyle={{ color: 'white' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={4}>
                    <Card className="stat-card" style={{ background: 'linear-gradient(135deg, #faad14 0%, #ffc53d 100%)' }}>
                        <Statistic
                            title={<span style={{ color: 'white' }}>Chờ xử lý</span>}
                            value={totalStats.pendingMessages}
                            prefix={<ClockCircleOutlined />}
                            valueStyle={{ color: 'white' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={4}>
                    <Card className="stat-card" style={{ background: 'linear-gradient(135deg, #722ed1 0%, #9254de 100%)' }}>
                        <Statistic
                            title={<span style={{ color: 'white' }}>Nhân viên</span>}
                            value={totalStats.totalStaff}
                            prefix={<UserOutlined />}
                            valueStyle={{ color: 'white' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={4}>
                    <Card className="stat-card" style={{ background: 'linear-gradient(135deg, #13c2c2 0%, #36cfc9 100%)' }}>
                        <Statistic
                            title={<span style={{ color: 'white' }}>Tổng yêu cầu</span>}
                            value={totalStats.totalRequests}
                            prefix={<FileTextOutlined />}
                            valueStyle={{ color: 'white' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={4}>
                    <Card className="stat-card" style={{ background: 'linear-gradient(135deg, #eb2f96 0%, #f759ab 100%)' }}>
                        <Statistic
                            title={<span style={{ color: 'white' }}>Yêu cầu chờ</span>}
                            value={totalStats.pendingRequests}
                            prefix={<FallOutlined />}
                            valueStyle={{ color: 'white' }}
                        />
                    </Card>
                </Col>
            </Row>

            {/* Tabs thống kê */}
            <Tabs defaultActiveKey="department" size="large">
                {/* Tab Theo phòng ban */}
                <TabPane
                    tab={<span><TeamOutlined /> Theo phòng ban</span>}
                    key="department"
                >
                    <Row gutter={[16, 16]}>
                        <Col xs={24} lg={12}>
                            <Card title="Tin nhắn theo phòng ban">
                                <div style={{ height: 350 }}>
                                    <Bar
                                        data={getDepartmentBarData()}
                                        options={{
                                            responsive: true,
                                            maintainAspectRatio: false,
                                            plugins: { legend: { position: 'top' } },
                                            scales: { y: { beginAtZero: true } }
                                        }}
                                    />
                                </div>
                            </Card>
                        </Col>
                        <Col xs={24} lg={12}>
                            <Card title="Phân bố tin nhắn theo phòng ban">
                                <div style={{ height: 350, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                                    <Pie
                                        data={getDepartmentPieData()}
                                        options={{
                                            responsive: true,
                                            maintainAspectRatio: false,
                                            plugins: { legend: { position: 'right' } }
                                        }}
                                    />
                                </div>
                            </Card>
                        </Col>
                        <Col xs={24} lg={12}>
                            <Card title="Số nhân viên theo phòng ban">
                                <div style={{ height: 300 }}>
                                    <Bar
                                        data={getDepartmentStaffData()}
                                        options={{
                                            responsive: true,
                                            maintainAspectRatio: false,
                                            plugins: { legend: { display: false } },
                                            scales: { y: { beginAtZero: true } }
                                        }}
                                    />
                                </div>
                            </Card>
                        </Col>
                        <Col xs={24} lg={12}>
                            <Card title="Chi tiết theo phòng ban">
                                <Table
                                    dataSource={statsByDepartment}
                                    columns={departmentColumns}
                                    rowKey="department_id"
                                    pagination={false}
                                    size="small"
                                />
                            </Card>
                        </Col>
                    </Row>
                </TabPane>

                {/* Tab Theo nhân viên */}
                <TabPane
                    tab={<span><UserOutlined /> Theo nhân viên</span>}
                    key="user"
                >
                    <Card style={{ marginBottom: 16 }}>
                        <Space size="large" wrap>
                            <div>
                                <Text strong>Lọc theo phòng ban:</Text>
                                <Select
                                    allowClear
                                    style={{ width: 200, marginLeft: 12 }}
                                    placeholder="Tất cả phòng ban"
                                    onChange={(value) => setSelectedDepartment(value)}
                                    options={departments.map(d => ({ label: d.name, value: d.id }))}
                                />
                            </div>
                            <div>
                                <Text strong>Lọc theo vai trò:</Text>
                                <Select
                                    allowClear
                                    style={{ width: 150, marginLeft: 12 }}
                                    placeholder="Tất cả"
                                    onChange={(value) => setSelectedRole(value)}
                                    options={[
                                        { label: 'Nhân viên', value: 'staff' },
                                        { label: 'Quản lý', value: 'manager' }
                                    ]}
                                />
                            </div>
                        </Space>
                    </Card>

                    <Row gutter={[16, 16]}>
                        <Col xs={24} lg={12}>
                            <Card title="Số tin nhắn theo nhân viên">
                                <div style={{ height: 400 }}>
                                    <Bar
                                        data={getUserBarData()}
                                        options={{
                                            responsive: true,
                                            maintainAspectRatio: false,
                                            indexAxis: 'y' as const,
                                            plugins: { legend: { position: 'top' } },
                                            scales: { x: { beginAtZero: true } }
                                        }}
                                    />
                                </div>
                            </Card>
                        </Col>
                        <Col xs={24} lg={12}>
                            <Card title="Tỷ lệ hoàn thành theo nhân viên">
                                <div style={{ height: 400 }}>
                                    <Bar
                                        data={getUserPerformanceData()}
                                        options={{
                                            responsive: true,
                                            maintainAspectRatio: false,
                                            indexAxis: 'y' as const,
                                            plugins: { legend: { display: false } },
                                            scales: { x: { beginAtZero: true, max: 100 } }
                                        }}
                                    />
                                </div>
                            </Card>
                        </Col>
                        <Col xs={24}>
                            <Card title="Bảng chi tiết nhân viên">
                                <Table
                                    dataSource={getFilteredUserStats()}
                                    columns={userColumns}
                                    rowKey="user_id"
                                    pagination={{ pageSize: 10 }}
                                    size="small"
                                />
                            </Card>
                        </Col>
                    </Row>
                </TabPane>

                {/* Tab Theo loại yêu cầu */}
                <TabPane
                    tab={<span><FileTextOutlined /> Theo loại yêu cầu</span>}
                    key="request"
                >
                    <Row gutter={[16, 16]}>
                        <Col xs={24} lg={14}>
                            <Card title="Thống kê yêu cầu theo loại">
                                <div style={{ height: 400 }}>
                                    <Bar
                                        data={getRequestTypeBarData()}
                                        options={{
                                            responsive: true,
                                            maintainAspectRatio: false,
                                            plugins: { legend: { position: 'top' } },
                                            scales: { y: { beginAtZero: true } }
                                        }}
                                    />
                                </div>
                            </Card>
                        </Col>
                        <Col xs={24} lg={10}>
                            <Card title="Phân bố yêu cầu">
                                <div style={{ height: 400, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                                    <Doughnut
                                        data={getRequestTypeDoughnutData()}
                                        options={{
                                            responsive: true,
                                            maintainAspectRatio: false,
                                            plugins: { legend: { position: 'bottom' } }
                                        }}
                                    />
                                </div>
                            </Card>
                        </Col>
                        <Col xs={24}>
                            <Card title="Chi tiết yêu cầu theo loại">
                                <Table
                                    dataSource={statsByRequestType}
                                    columns={[
                                        {
                                            title: 'Loại yêu cầu',
                                            dataIndex: 'request_type',
                                            key: 'request_type',
                                            render: (type) => requestTypeLabels[type] || type
                                        },
                                        { title: 'Tổng số', dataIndex: 'total_requests', key: 'total_requests' },
                                        {
                                            title: 'Đã duyệt',
                                            dataIndex: 'approved_requests',
                                            key: 'approved_requests',
                                            render: (v) => <Tag color="success">{v}</Tag>
                                        },
                                        {
                                            title: 'Từ chối',
                                            dataIndex: 'rejected_requests',
                                            key: 'rejected_requests',
                                            render: (v) => <Tag color="error">{v}</Tag>
                                        },
                                        {
                                            title: 'Chờ duyệt',
                                            dataIndex: 'pending_requests',
                                            key: 'pending_requests',
                                            render: (v) => <Tag color="warning">{v}</Tag>
                                        },
                                        {
                                            title: 'Tỷ lệ duyệt',
                                            key: 'approval_rate',
                                            render: (_: any, record: StatsByRequestType) => {
                                                const rate = record.total_requests > 0
                                                    ? Math.round((record.approved_requests / record.total_requests) * 100)
                                                    : 0;
                                                return <Tag color="blue">{rate}%</Tag>;
                                            }
                                        }
                                    ]}
                                    rowKey="request_type"
                                    pagination={false}
                                    size="small"
                                />
                            </Card>
                        </Col>
                    </Row>
                </TabPane>
            </Tabs>
        </div>
    );
};

export default AdminStatistics;
