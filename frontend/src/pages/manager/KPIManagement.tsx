import React, { useEffect, useState } from 'react';
import {
    Card, Button, Table, Modal, Form, Input, InputNumber, DatePicker, Typography,
    message as antdMessage, Popconfirm, Space, Row, Col, Statistic, Progress, Tag, Select
} from 'antd';
import {
    PlusOutlined, EditOutlined, DeleteOutlined, BarChartOutlined,
    TrophyOutlined, RiseOutlined, AimOutlined
} from '@ant-design/icons';
import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, Title as ChartTitle } from 'chart.js';
import { Bar, Doughnut } from 'react-chartjs-2';
import dayjs from 'dayjs';
import apiClient from '../../api/client';
import type { ColumnsType } from 'antd/es/table';
import { KPI, User } from '../../types';

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, ChartTitle);

const { Title, Paragraph } = Typography;
const { RangePicker } = DatePicker;

interface KPIWithUser extends KPI {
    user_name?: string;
}

interface StaffMember {
    id: number;
    full_name: string;
    email: string;
}

const KPIManagement: React.FC = () => {
    const [kpis, setKpis] = useState<KPIWithUser[]>([]);
    const [staff, setStaff] = useState<StaffMember[]>([]);
    const [loading, setLoading] = useState(false);
    const [modalVisible, setModalVisible] = useState(false);
    const [editingKPI, setEditingKPI] = useState<KPIWithUser | null>(null);
    const [form] = Form.useForm();
    const [selectedStaff, setSelectedStaff] = useState<number | null>(null);

    useEffect(() => {
        fetchKPIs();
        fetchStaff();
    }, []);

    const fetchKPIs = async () => {
        try {
            setLoading(true);
            const response = await apiClient.get<KPI[]>('/api/manager/kpis');
            
            // Fetch user names for each KPI
            const kpisWithUsers = await Promise.all(
                response.data.map(async (kpi) => {
                    try {
                        const staffRes = await apiClient.get<StaffMember[]>('/api/manager/staff');
                        const user = staffRes.data.find(s => s.id === kpi.user_id);
                        return { ...kpi, user_name: user?.full_name || 'N/A' };
                    } catch {
                        return { ...kpi, user_name: 'N/A' };
                    }
                })
            );
            
            setKpis(kpisWithUsers);
        } catch (error) {
            antdMessage.error('Không thể tải danh sách KPI');
        } finally {
            setLoading(false);
        }
    };

    const fetchStaff = async () => {
        try {
            const response = await apiClient.get<StaffMember[]>('/api/manager/staff');
            setStaff(response.data);
        } catch (error) {
            antdMessage.error('Không thể tải danh sách nhân viên');
        }
    };

    const handleCreate = () => {
        setEditingKPI(null);
        form.resetFields();
        setModalVisible(true);
    };

    const handleEdit = (record: KPIWithUser) => {
        setEditingKPI(record);
        form.setFieldsValue({
            ...record,
            period: record.period_start && record.period_end
                ? [dayjs(record.period_start), dayjs(record.period_end)]
                : undefined
        });
        setModalVisible(true);
    };

    const handleDelete = async (id: number) => {
        try {
            await apiClient.delete(`/api/manager/kpis/${id}`);
            antdMessage.success('Đã xóa KPI');
            fetchKPIs();
        } catch (error) {
            antdMessage.error('Không thể xóa KPI');
        }
    };

    const handleSubmit = async (values: any) => {
        try {
            const payload = {
                user_id: values.user_id,
                metric_name: values.metric_name,
                target_value: values.target_value,
                current_value: values.current_value || 0,
                period_start: values.period?.[0]?.format('YYYY-MM-DD'),
                period_end: values.period?.[1]?.format('YYYY-MM-DD'),
            };

            if (editingKPI) {
                await apiClient.put(`/api/manager/kpis/${editingKPI.id}`, payload);
                antdMessage.success('Đã cập nhật KPI');
            } else {
                await apiClient.post('/api/manager/kpis', payload);
                antdMessage.success('Đã tạo KPI mới');
            }
            setModalVisible(false);
            form.resetFields();
            fetchKPIs();
        } catch (error: any) {
            antdMessage.error(error.response?.data?.detail || 'Có lỗi xảy ra');
        }
    };

    // Tính toán thống kê
    const calculateStats = () => {
        const filteredKPIs = selectedStaff
            ? kpis.filter(k => k.user_id === selectedStaff)
            : kpis;

        const totalKPIs = filteredKPIs.length;
        const completedKPIs = filteredKPIs.filter(k =>
            k.target_value && k.current_value >= k.target_value
        ).length;
        const avgProgress = filteredKPIs.length > 0
            ? filteredKPIs.reduce((acc, k) => {
                if (k.target_value && k.target_value > 0) {
                    return acc + (k.current_value / k.target_value) * 100;
                }
                return acc;
            }, 0) / filteredKPIs.filter(k => k.target_value && k.target_value > 0).length || 0
            : 0;

        return { totalKPIs, completedKPIs, avgProgress };
    };

    const stats = calculateStats();

    // Dữ liệu biểu đồ theo nhân viên
    const getChartDataByStaff = () => {
        const staffKPIs = staff.map(s => {
            const userKPIs = kpis.filter(k => k.user_id === s.id);
            const completed = userKPIs.filter(k => k.target_value && k.current_value >= k.target_value).length;
            const inProgress = userKPIs.length - completed;
            return {
                name: s.full_name,
                completed,
                inProgress,
                total: userKPIs.length
            };
        }).filter(s => s.total > 0);

        return {
            labels: staffKPIs.map(s => s.name),
            datasets: [
                {
                    label: 'Hoàn thành',
                    data: staffKPIs.map(s => s.completed),
                    backgroundColor: 'rgba(82, 196, 26, 0.8)',
                },
                {
                    label: 'Đang thực hiện',
                    data: staffKPIs.map(s => s.inProgress),
                    backgroundColor: 'rgba(24, 144, 255, 0.8)',
                }
            ]
        };
    };

    // Dữ liệu biểu đồ tròn
    const getDoughnutData = () => {
        const completed = kpis.filter(k => k.target_value && k.current_value >= k.target_value).length;
        const inProgress = kpis.filter(k => k.target_value && k.current_value < k.target_value && k.current_value > 0).length;
        const notStarted = kpis.filter(k => k.current_value === 0).length;

        return {
            labels: ['Hoàn thành', 'Đang thực hiện', 'Chưa bắt đầu'],
            datasets: [{
                data: [completed, inProgress, notStarted],
                backgroundColor: [
                    'rgba(82, 196, 26, 0.8)',
                    'rgba(24, 144, 255, 0.8)',
                    'rgba(140, 140, 140, 0.8)'
                ],
                borderWidth: 1
            }]
        };
    };

    const columns: ColumnsType<KPIWithUser> = [
        {
            title: 'Nhân viên',
            dataIndex: 'user_name',
            key: 'user_name',
            render: (text) => <strong>{text}</strong>,
        },
        {
            title: 'Chỉ số KPI',
            dataIndex: 'metric_name',
            key: 'metric_name',
        },
        {
            title: 'Mục tiêu',
            dataIndex: 'target_value',
            key: 'target_value',
            width: 100,
            render: (value) => value || '-',
        },
        {
            title: 'Hiện tại',
            dataIndex: 'current_value',
            key: 'current_value',
            width: 100,
        },
        {
            title: 'Tiến độ',
            key: 'progress',
            width: 150,
            render: (_, record) => {
                if (!record.target_value || record.target_value === 0) {
                    return <Tag color="default">Không có mục tiêu</Tag>;
                }
                const percent = Math.min((record.current_value / record.target_value) * 100, 100);
                const status = percent >= 100 ? 'success' : percent >= 50 ? 'active' : 'exception';
                return <Progress percent={Math.round(percent)} size="small" status={status} />;
            },
        },
        {
            title: 'Thời gian',
            key: 'period',
            width: 180,
            render: (_, record) => {
                if (!record.period_start || !record.period_end) return '-';
                return `${dayjs(record.period_start).format('DD/MM/YYYY')} - ${dayjs(record.period_end).format('DD/MM/YYYY')}`;
            },
        },
        {
            title: 'Trạng thái',
            key: 'status',
            width: 120,
            render: (_, record) => {
                if (!record.target_value) return <Tag color="default">N/A</Tag>;
                if (record.current_value >= record.target_value) {
                    return <Tag color="success">Hoàn thành</Tag>;
                }
                if (record.current_value > 0) {
                    return <Tag color="processing">Đang thực hiện</Tag>;
                }
                return <Tag color="warning">Chưa bắt đầu</Tag>;
            },
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
                        title="Xóa KPI"
                        description="Bạn có chắc muốn xóa KPI này?"
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
            <div className="page-header" style={{ marginBottom: 24 }}>
                <Title level={2}>
                    <BarChartOutlined /> Quản lý KPI
                </Title>
                <Paragraph type="secondary">
                    Tạo, cập nhật và giám sát số liệu thống kê KPI của từng nhân viên trong phòng ban
                </Paragraph>
            </div>

            {/* Thống kê tổng quan */}
            <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
                <Col xs={24} sm={8}>
                    <Card className="stat-card">
                        <Statistic
                            title={<span style={{ color: 'white' }}>Tổng số KPI</span>}
                            value={stats.totalKPIs}
                            prefix={<AimOutlined />}
                            valueStyle={{ color: 'white' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={8}>
                    <Card className="stat-card" style={{ background: 'linear-gradient(135deg, #52c41a 0%, #73d13d 100%)' }}>
                        <Statistic
                            title={<span style={{ color: 'white' }}>KPI hoàn thành</span>}
                            value={stats.completedKPIs}
                            prefix={<TrophyOutlined />}
                            valueStyle={{ color: 'white' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={8}>
                    <Card className="stat-card" style={{ background: 'linear-gradient(135deg, #faad14 0%, #ffc53d 100%)' }}>
                        <Statistic
                            title={<span style={{ color: 'white' }}>Tiến độ trung bình</span>}
                            value={Math.round(stats.avgProgress)}
                            suffix="%"
                            prefix={<RiseOutlined />}
                            valueStyle={{ color: 'white' }}
                        />
                    </Card>
                </Col>
            </Row>

            {/* Biểu đồ */}
            <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
                <Col xs={24} lg={14}>
                    <Card title="Thống kê KPI theo nhân viên">
                        <div style={{ height: 300 }}>
                            <Bar
                                data={getChartDataByStaff()}
                                options={{
                                    responsive: true,
                                    maintainAspectRatio: false,
                                    plugins: {
                                        legend: { position: 'top' as const }
                                    },
                                    scales: {
                                        y: { beginAtZero: true }
                                    }
                                }}
                            />
                        </div>
                    </Card>
                </Col>
                <Col xs={24} lg={10}>
                    <Card title="Tỷ lệ hoàn thành KPI">
                        <div style={{ height: 300, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                            <Doughnut
                                data={getDoughnutData()}
                                options={{
                                    responsive: true,
                                    maintainAspectRatio: false,
                                    plugins: {
                                        legend: { position: 'bottom' as const }
                                    }
                                }}
                            />
                        </div>
                    </Card>
                </Col>
            </Row>

            {/* Bảng danh sách KPI */}
            <Card>
                <div className="content-header" style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
                    <Select
                        placeholder="Lọc theo nhân viên"
                        allowClear
                        style={{ width: 200 }}
                        onChange={(value) => setSelectedStaff(value)}
                        options={staff.map(s => ({ label: s.full_name, value: s.id }))}
                    />
                    <Button
                        type="primary"
                        size="large"
                        icon={<PlusOutlined />}
                        onClick={handleCreate}
                    >
                        Thêm KPI
                    </Button>
                </div>

                <Table
                    columns={columns}
                    dataSource={selectedStaff ? kpis.filter(k => k.user_id === selectedStaff) : kpis}
                    rowKey="id"
                    loading={loading}
                    pagination={{ pageSize: 10 }}
                />
            </Card>

            {/* Modal tạo/sửa KPI */}
            <Modal
                title={editingKPI ? 'Cập nhật KPI' : 'Thêm KPI mới'}
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
                    onFinish={handleSubmit}
                    initialValues={{ current_value: 0 }}
                >
                    <Form.Item
                        name="user_id"
                        label="Nhân viên"
                        rules={[{ required: true, message: 'Vui lòng chọn nhân viên' }]}
                    >
                        <Select
                            placeholder="Chọn nhân viên"
                            options={staff.map(s => ({ label: s.full_name, value: s.id }))}
                        />
                    </Form.Item>

                    <Form.Item
                        name="metric_name"
                        label="Tên chỉ số KPI"
                        rules={[{ required: true, message: 'Vui lòng nhập tên chỉ số' }]}
                    >
                        <Input placeholder="Ví dụ: Số tin nhắn xử lý, Tỷ lệ hoàn thành..." />
                    </Form.Item>

                    <Row gutter={16}>
                        <Col span={12}>
                            <Form.Item
                                name="target_value"
                                label="Mục tiêu"
                            >
                                <InputNumber
                                    style={{ width: '100%' }}
                                    min={0}
                                    placeholder="Giá trị mục tiêu"
                                />
                            </Form.Item>
                        </Col>
                        <Col span={12}>
                            <Form.Item
                                name="current_value"
                                label="Giá trị hiện tại"
                                rules={[{ required: true, message: 'Vui lòng nhập giá trị' }]}
                            >
                                <InputNumber
                                    style={{ width: '100%' }}
                                    min={0}
                                    placeholder="Giá trị hiện tại"
                                />
                            </Form.Item>
                        </Col>
                    </Row>

                    <Form.Item
                        name="period"
                        label="Thời gian áp dụng"
                    >
                        <RangePicker
                            style={{ width: '100%' }}
                            format="DD/MM/YYYY"
                            placeholder={['Ngày bắt đầu', 'Ngày kết thúc']}
                        />
                    </Form.Item>

                    <Form.Item style={{ marginBottom: 0, marginTop: 24 }}>
                        <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                            <Button onClick={() => setModalVisible(false)}>
                                Hủy
                            </Button>
                            <Button type="primary" htmlType="submit">
                                {editingKPI ? 'Cập nhật' : 'Tạo mới'}
                            </Button>
                        </Space>
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
};

export default KPIManagement;
