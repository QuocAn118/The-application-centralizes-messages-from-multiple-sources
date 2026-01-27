import React, { useEffect, useState } from 'react';
import {
    Card, Button, Table, Modal, Form, Input, TimePicker, Typography,
    message as antdMessage, Popconfirm, Space, Row, Col, Tag, DatePicker, Select
} from 'antd';
import {
    PlusOutlined, EditOutlined, DeleteOutlined, ClockCircleOutlined,
    CalendarOutlined, UserAddOutlined
} from '@ant-design/icons';
import dayjs from 'dayjs';
import apiClient from '../../api/client';
import type { ColumnsType } from 'antd/es/table';
import { Shift, UserShift } from '../../types';

const { Title, Paragraph } = Typography;

interface StaffMember {
    id: number;
    full_name: string;
    email: string;
}

interface ShiftAssignment extends UserShift {
    user_name?: string;
    shift_name?: string;
}

const ShiftsManagement: React.FC = () => {
    const [shifts, setShifts] = useState<Shift[]>([]);
    const [assignments, setAssignments] = useState<ShiftAssignment[]>([]);
    const [staff, setStaff] = useState<StaffMember[]>([]);
    const [loading, setLoading] = useState(false);
    const [modalVisible, setModalVisible] = useState(false);
    const [assignModalVisible, setAssignModalVisible] = useState(false);
    const [editingShift, setEditingShift] = useState<Shift | null>(null);
    const [form] = Form.useForm();
    const [assignForm] = Form.useForm();
    const [activeTab, setActiveTab] = useState<'shifts' | 'assignments'>('shifts');

    useEffect(() => {
        fetchShifts();
        fetchStaff();
        fetchAssignments();
    }, []);

    const fetchShifts = async () => {
        try {
            setLoading(true);
            const response = await apiClient.get<Shift[]>('/api/manager/shifts');
            setShifts(response.data);
        } catch (error) {
            antdMessage.error('Không thể tải danh sách ca làm việc');
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

    const fetchAssignments = async () => {
        try {
            const response = await apiClient.get<UserShift[]>('/api/manager/shift-assignments');
            
            // Enrich data with user and shift names
            const enrichedAssignments = response.data.map(assignment => {
                const user = staff.find(s => s.id === assignment.user_id);
                const shift = shifts.find(s => s.id === assignment.shift_id);
                return {
                    ...assignment,
                    user_name: user?.full_name || 'N/A',
                    shift_name: shift?.name || 'N/A'
                };
            });
            
            setAssignments(enrichedAssignments);
        } catch (error) {
            // Silent fail for assignments
        }
    };

    useEffect(() => {
        if (staff.length > 0 && shifts.length > 0) {
            fetchAssignments();
        }
    }, [staff, shifts]);

    const handleCreateShift = () => {
        setEditingShift(null);
        form.resetFields();
        setModalVisible(true);
    };

    const handleEditShift = (record: Shift) => {
        setEditingShift(record);
        form.setFieldsValue({
            ...record,
            start_time: dayjs(record.start_time, 'HH:mm:ss'),
            end_time: dayjs(record.end_time, 'HH:mm:ss'),
        });
        setModalVisible(true);
    };

    const handleDeleteShift = async (id: number) => {
        try {
            await apiClient.delete(`/api/manager/shifts/${id}`);
            antdMessage.success('Đã xóa ca làm việc');
            fetchShifts();
        } catch (error) {
            antdMessage.error('Không thể xóa ca làm việc');
        }
    };

    const handleSubmitShift = async (values: any) => {
        try {
            // Lấy department_id từ profile
            const profileResponse = await apiClient.get('/api/staff/profile');
            const departmentId = profileResponse.data.department_id;

            const payload = {
                name: values.name,
                start_time: values.start_time.format('HH:mm:ss'),
                end_time: values.end_time.format('HH:mm:ss'),
                department_id: departmentId
            };

            if (editingShift) {
                await apiClient.put(`/api/manager/shifts/${editingShift.id}`, payload);
                antdMessage.success('Đã cập nhật ca làm việc');
            } else {
                await apiClient.post('/api/manager/shifts', payload);
                antdMessage.success('Đã tạo ca làm việc mới');
            }
            setModalVisible(false);
            form.resetFields();
            fetchShifts();
        } catch (error: any) {
            antdMessage.error(error.response?.data?.detail || 'Có lỗi xảy ra');
        }
    };

    const handleAssignShift = () => {
        assignForm.resetFields();
        setAssignModalVisible(true);
    };

    const handleSubmitAssignment = async (values: any) => {
        try {
            const payload = {
                user_id: values.user_id,
                shift_id: values.shift_id,
                date: values.date.format('YYYY-MM-DD'),
                status: 'scheduled'
            };

            await apiClient.post('/api/manager/shift-assignments', payload);
            antdMessage.success('Đã phân công ca làm việc');
            setAssignModalVisible(false);
            assignForm.resetFields();
            fetchAssignments();
        } catch (error: any) {
            antdMessage.error(error.response?.data?.detail || 'Có lỗi xảy ra');
        }
    };

    const shiftColumns: ColumnsType<Shift> = [
        {
            title: 'Tên ca',
            dataIndex: 'name',
            key: 'name',
            render: (text) => <strong>{text}</strong>,
        },
        {
            title: 'Giờ bắt đầu',
            dataIndex: 'start_time',
            key: 'start_time',
            width: 120,
            render: (time) => (
                <Tag color="blue">
                    <ClockCircleOutlined /> {time?.substring(0, 5)}
                </Tag>
            ),
        },
        {
            title: 'Giờ kết thúc',
            dataIndex: 'end_time',
            key: 'end_time',
            width: 120,
            render: (time) => (
                <Tag color="green">
                    <ClockCircleOutlined /> {time?.substring(0, 5)}
                </Tag>
            ),
        },
        {
            title: 'Thời lượng',
            key: 'duration',
            width: 100,
            render: (_, record) => {
                if (!record.start_time || !record.end_time) return '-';
                const start = dayjs(record.start_time, 'HH:mm:ss');
                const end = dayjs(record.end_time, 'HH:mm:ss');
                let diff = end.diff(start, 'hour', true);
                if (diff < 0) diff += 24; // Handle overnight shifts
                return `${diff.toFixed(1)} giờ`;
            },
        },
        {
            title: 'Ngày tạo',
            dataIndex: 'created_at',
            key: 'created_at',
            width: 120,
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
                        onClick={() => handleEditShift(record)}
                    >
                        Sửa
                    </Button>
                    <Popconfirm
                        title="Xóa ca làm việc"
                        description="Bạn có chắc muốn xóa ca này?"
                        onConfirm={() => handleDeleteShift(record.id)}
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

    const assignmentColumns: ColumnsType<ShiftAssignment> = [
        {
            title: 'Nhân viên',
            dataIndex: 'user_name',
            key: 'user_name',
            render: (text) => <strong>{text}</strong>,
        },
        {
            title: 'Ca làm việc',
            dataIndex: 'shift_name',
            key: 'shift_name',
        },
        {
            title: 'Ngày',
            dataIndex: 'date',
            key: 'date',
            width: 120,
            render: (date) => new Date(date).toLocaleDateString('vi-VN'),
        },
        {
            title: 'Trạng thái',
            dataIndex: 'status',
            key: 'status',
            width: 120,
            render: (status) => {
                const config: Record<string, { color: string; text: string }> = {
                    scheduled: { color: 'blue', text: 'Đã lên lịch' },
                    completed: { color: 'green', text: 'Hoàn thành' },
                    cancelled: { color: 'red', text: 'Đã hủy' },
                };
                const { color, text } = config[status] || { color: 'default', text: status };
                return <Tag color={color}>{text}</Tag>;
            },
        },
    ];

    return (
        <div className="page-container">
            <div className="page-header" style={{ marginBottom: 24 }}>
                <Title level={2}>
                    <ClockCircleOutlined /> Quản lý Ca làm việc
                </Title>
                <Paragraph type="secondary">
                    Tạo và quản lý các ca làm việc, phân công nhân viên vào từng ca
                </Paragraph>
            </div>

            {/* Tab buttons */}
            <Card style={{ marginBottom: 24 }}>
                <Space size="middle">
                    <Button
                        type={activeTab === 'shifts' ? 'primary' : 'default'}
                        icon={<ClockCircleOutlined />}
                        onClick={() => setActiveTab('shifts')}
                    >
                        Danh sách ca làm việc
                    </Button>
                    <Button
                        type={activeTab === 'assignments' ? 'primary' : 'default'}
                        icon={<CalendarOutlined />}
                        onClick={() => setActiveTab('assignments')}
                    >
                        Phân công ca
                    </Button>
                </Space>
            </Card>

            {/* Shifts table */}
            {activeTab === 'shifts' && (
                <Card>
                    <div className="content-header" style={{ marginBottom: 24, display: 'flex', justifyContent: 'flex-end' }}>
                        <Button
                            type="primary"
                            size="large"
                            icon={<PlusOutlined />}
                            onClick={handleCreateShift}
                        >
                            Thêm ca làm việc
                        </Button>
                    </div>

                    <Table
                        columns={shiftColumns}
                        dataSource={shifts}
                        rowKey="id"
                        loading={loading}
                        pagination={{ pageSize: 10 }}
                    />
                </Card>
            )}

            {/* Assignments table */}
            {activeTab === 'assignments' && (
                <Card>
                    <div className="content-header" style={{ marginBottom: 24, display: 'flex', justifyContent: 'flex-end' }}>
                        <Button
                            type="primary"
                            size="large"
                            icon={<UserAddOutlined />}
                            onClick={handleAssignShift}
                        >
                            Phân công ca
                        </Button>
                    </div>

                    <Table
                        columns={assignmentColumns}
                        dataSource={assignments}
                        rowKey="id"
                        loading={loading}
                        pagination={{ pageSize: 10 }}
                    />
                </Card>
            )}

            {/* Modal tạo/sửa ca làm việc */}
            <Modal
                title={editingShift ? 'Cập nhật ca làm việc' : 'Thêm ca làm việc mới'}
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
                    onFinish={handleSubmitShift}
                >
                    <Form.Item
                        name="name"
                        label="Tên ca làm việc"
                        rules={[{ required: true, message: 'Vui lòng nhập tên ca' }]}
                    >
                        <Input placeholder="Ví dụ: Ca sáng, Ca chiều, Ca tối..." />
                    </Form.Item>

                    <Row gutter={16}>
                        <Col span={12}>
                            <Form.Item
                                name="start_time"
                                label="Giờ bắt đầu"
                                rules={[{ required: true, message: 'Vui lòng chọn giờ bắt đầu' }]}
                            >
                                <TimePicker
                                    format="HH:mm"
                                    style={{ width: '100%' }}
                                    placeholder="Chọn giờ"
                                />
                            </Form.Item>
                        </Col>
                        <Col span={12}>
                            <Form.Item
                                name="end_time"
                                label="Giờ kết thúc"
                                rules={[{ required: true, message: 'Vui lòng chọn giờ kết thúc' }]}
                            >
                                <TimePicker
                                    format="HH:mm"
                                    style={{ width: '100%' }}
                                    placeholder="Chọn giờ"
                                />
                            </Form.Item>
                        </Col>
                    </Row>

                    <Form.Item style={{ marginBottom: 0, marginTop: 24 }}>
                        <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                            <Button onClick={() => setModalVisible(false)}>
                                Hủy
                            </Button>
                            <Button type="primary" htmlType="submit">
                                {editingShift ? 'Cập nhật' : 'Tạo mới'}
                            </Button>
                        </Space>
                    </Form.Item>
                </Form>
            </Modal>

            {/* Modal phân công ca */}
            <Modal
                title="Phân công ca làm việc"
                open={assignModalVisible}
                onCancel={() => {
                    setAssignModalVisible(false);
                    assignForm.resetFields();
                }}
                footer={null}
                width={500}
            >
                <Form
                    form={assignForm}
                    layout="vertical"
                    onFinish={handleSubmitAssignment}
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
                        name="shift_id"
                        label="Ca làm việc"
                        rules={[{ required: true, message: 'Vui lòng chọn ca làm việc' }]}
                    >
                        <Select
                            placeholder="Chọn ca"
                            options={shifts.map(s => ({
                                label: `${s.name} (${s.start_time?.substring(0, 5)} - ${s.end_time?.substring(0, 5)})`,
                                value: s.id
                            }))}
                        />
                    </Form.Item>

                    <Form.Item
                        name="date"
                        label="Ngày"
                        rules={[{ required: true, message: 'Vui lòng chọn ngày' }]}
                    >
                        <DatePicker
                            format="DD/MM/YYYY"
                            style={{ width: '100%' }}
                            placeholder="Chọn ngày"
                        />
                    </Form.Item>

                    <Form.Item style={{ marginBottom: 0, marginTop: 24 }}>
                        <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                            <Button onClick={() => setAssignModalVisible(false)}>
                                Hủy
                            </Button>
                            <Button type="primary" htmlType="submit">
                                Phân công
                            </Button>
                        </Space>
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
};

export default ShiftsManagement;
