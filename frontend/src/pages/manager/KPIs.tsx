import React, { useEffect, useState } from 'react';
import { Table, Card, Button, Modal, Form, Input, InputNumber, Select, DatePicker, message, Progress, Space, Tag, Popconfirm } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import apiClient from '../../api/client';
import { Staff } from '../../types';

interface KPI {
    id: number;
    user_id: number;
    metric_name: string;
    target_value: number;
    current_value: number;
    unit: string;
    period_start: string;
    period_end: string;
    user?: {
        full_name: string;
    };
}

const ManagerKPIs: React.FC = () => {
    const [kpis, setKPIs] = useState<KPI[]>([]);
    const [staffList, setStaffList] = useState<Staff[]>([]);
    const [loading, setLoading] = useState(false);
    const [isModalVisible, setIsModalVisible] = useState(false);
    const [editingKPI, setEditingKPI] = useState<KPI | null>(null);
    const [form] = Form.useForm();

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [kpiRes, staffRes] = await Promise.all([
                apiClient.get('/api/manager/kpis'),
                apiClient.get('/api/manager/staff')
            ]);
            setKPIs(kpiRes.data);
            setStaffList(staffRes.data);
        } catch (error) {
            message.error('Không thể tải dữ liệu');
        } finally {
            setLoading(false);
        }
    };

    const handleAdd = () => {
        setEditingKPI(null);
        form.resetFields();
        setIsModalVisible(true);
    };

    const handleEdit = (record: KPI) => {
        setEditingKPI(record);
        form.setFieldsValue({
            ...record,
            period: [dayjs(record.period_start), dayjs(record.period_end)],
        });
        setIsModalVisible(true);
    };

    const handleDelete = async (id: number) => {
        try {
            await apiClient.delete(`/api/manager/kpis/${id}`);
            message.success('Xóa KPI thành công');
            fetchData();
        } catch (error) {
            message.error('Xóa thất bại');
        }
    };

    const handleModalOk = async () => {
        try {
            const values = await form.validateFields();
            const payload = {
                user_id: values.user_id,
                metric_name: values.metric_name,
                target_value: values.target_value,
                current_value: values.current_value || 0,
                unit: values.unit,
                period_start: values.period[0].format('YYYY-MM-DD'),
                period_end: values.period[1].format('YYYY-MM-DD'),
            };

            if (editingKPI) {
                await apiClient.put(`/api/manager/kpis/${editingKPI.id}`, payload);
                message.success('Cập nhật KPI thành công');
            } else {
                await apiClient.post('/api/manager/kpis', payload);
                message.success('Tạo KPI mới thành công');
            }
            setIsModalVisible(false);
            fetchData();
        } catch (error) {
            message.error('Có lỗi xảy ra');
        }
    };

    const columns = [
        {
            title: 'Nhân viên',
            dataIndex: ['user', 'full_name'],
            key: 'user_name',
            render: (text: string) => <span style={{ fontWeight: 500 }}>{text || 'Unknown'}</span>,
        },
        {
            title: 'Chỉ số',
            dataIndex: 'metric_name',
            key: 'metric_name',
        },
        {
            title: 'Mục tiêu',
            key: 'target',
            render: (_: any, record: KPI) => (
                <span>{record.current_value} / {record.target_value} {record.unit}</span>
            ),
        },
        {
            title: 'Tiến độ',
            key: 'progress',
            render: (_: any, record: KPI) => {
                const percent = Math.min(Math.round((record.current_value / record.target_value) * 100), 100);
                return <Progress percent={percent} size="small" status={percent >= 100 ? 'success' : 'active'} />;
            },
        },
        {
            title: 'Thời gian',
            key: 'period',
            render: (_: any, record: KPI) => (
                <Space direction="vertical" size={0}>
                    <Tag color="blue">Start: {dayjs(record.period_start).format('DD/MM/YYYY')}</Tag>
                    <Tag color="orange">End: {dayjs(record.period_end).format('DD/MM/YYYY')}</Tag>
                </Space>
            ),
        },
        {
            title: 'Hành động',
            key: 'action',
            render: (_: any, record: KPI) => (
                <Space>
                    <Button icon={<EditOutlined />} size="small" onClick={() => handleEdit(record)} />
                    <Popconfirm title="Bạn có chắc chắn muốn xóa?" onConfirm={() => handleDelete(record.id)}>
                        <Button icon={<DeleteOutlined />} size="small" danger />
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    return (
        <div className="page-container">
            <div className="page-header">
                <h1 className="page-title">Quản lý KPI</h1>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
                    Thêm KPI Mới
                </Button>
            </div>

            <Card>
                <Table
                    columns={columns}
                    dataSource={kpis}
                    rowKey="id"
                    loading={loading}
                    pagination={{ pageSize: 10 }}
                />
            </Card>

            <Modal
                title={editingKPI ? "Cập nhật KPI" : "Tạo KPI Mới"}
                open={isModalVisible}
                onOk={handleModalOk}
                onCancel={() => setIsModalVisible(false)}
            >
                <Form form={form} layout="vertical">
                    <Form.Item name="user_id" label="Nhân viên" rules={[{ required: true, message: 'Vui lòng chọn nhân viên' }]}>
                        <Select placeholder="Chọn nhân viên">
                            {staffList.map(staff => (
                                <Select.Option key={staff.id} value={staff.id}>{staff.full_name}</Select.Option>
                            ))}
                        </Select>
                    </Form.Item>
                    <Form.Item name="metric_name" label="Tên chỉ số" rules={[{ required: true, message: 'Nhập tên chỉ số (VD: Doanh số)' }]}>
                        <Input placeholder="VD: Doanh số bán hàng" />
                    </Form.Item>
                    <Space style={{ display: 'flex', marginBottom: 8 }} align="baseline">
                        <Form.Item name="target_value" label="Mục tiêu" rules={[{ required: true }]}>
                            <InputNumber min={0} style={{ width: '100%' }} />
                        </Form.Item>
                        <Form.Item name="current_value" label="Hiện tại">
                            <InputNumber min={0} style={{ width: '100%' }} />
                        </Form.Item>
                        <Form.Item name="unit" label="Đơn vị" rules={[{ required: true }]}>
                            <Input placeholder="VD: VND, HĐ" />
                        </Form.Item>
                    </Space>
                    <Form.Item name="period" label="Thời gian áp dụng" rules={[{ required: true }]}>
                        <DatePicker.RangePicker style={{ width: '100%' }} />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
};

export default ManagerKPIs;
