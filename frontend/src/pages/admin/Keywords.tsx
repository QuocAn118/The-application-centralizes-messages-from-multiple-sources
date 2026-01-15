import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Typography } from 'antd';
import { KeyOutlined } from '@ant-design/icons';
import apiClient from '../../api/client';
import type { ColumnsType } from 'antd/es/table';

const { Title, Paragraph } = Typography;

interface Keyword {
    id: number;
    keyword: string;
    department_id: number;
    department_name: string;
    priority: number;
    is_active: boolean;
    created_at: string;
}

const AdminKeywords: React.FC = () => {
    const [keywords, setKeywords] = useState<Keyword[]>([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        fetchKeywords();
    }, []);

    const fetchKeywords = async () => {
        try {
            setLoading(true);
            const response = await apiClient.get<Keyword[]>('/api/admin/keywords');
            setKeywords(response.data);
        } catch (error) {
            console.error('Không thể tải danh sách từ khóa:', error);
        } finally {
            setLoading(false);
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
            title: 'Phòng ban',
            dataIndex: 'department_name',
            key: 'department_name',
            render: (text) => text || '-',
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
    ];

    return (
        <div className="page-container">
            <Card>
                <div className="content-header" style={{ marginBottom: 24 }}>
                    <div>
                        <Title level={3}>
                            <KeyOutlined /> Danh sách Từ khóa
                        </Title>
                        <Paragraph type="secondary">
                            Xem tất cả từ khóa được tạo bởi các Quản lý phòng ban trong hệ thống
                        </Paragraph>
                    </div>
                </div>

                <Table
                    columns={columns}
                    dataSource={keywords}
                    rowKey="id"
                    loading={loading}
                    pagination={{ pageSize: 10 }}
                />
            </Card>
        </div>
    );
};

export default AdminKeywords;
