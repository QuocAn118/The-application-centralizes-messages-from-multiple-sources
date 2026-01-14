export interface User {
    id: number;
    email: string;
    full_name: string;
    phone?: string;
    role: 'admin' | 'manager' | 'staff';
    department_id?: number;
    is_active: boolean;
    created_at: string;
}

export interface Department {
    id: number;
    name: string;
    description?: string;
}

export interface Customer {
    id: number;
    name?: string;
    phone?: string;
    email?: string;
    platform?: string;
    zalo_id?: string;
    meta_id?: string;
}

export interface Message {
    id: number;
    customer_id: number;
    content: string;
    platform: string;
    direction: 'incoming' | 'outgoing';
    status: 'pending' | 'assigned' | 'in_progress' | 'completed';
    external_id?: string;
    created_at: string;
    customer_name?: string;
    customer_phone?: string;
}

export interface Keyword {
    id: number;
    keyword: string;
    department_id: number;
    priority: number;
    is_active: boolean;
    created_at: string;
    department_name?: string;
}

export interface KPI {
    id: number;
    user_id: number;
    metric_name: string;
    target_value?: number;
    current_value: number;
    period_start?: string;
    period_end?: string;
    created_at: string;
}

export interface Shift {
    id: number;
    name: string;
    start_time: string;
    end_time: string;
    department_id: number;
    created_at: string;
}

export interface UserShift {
    id: number;
    user_id: number;
    shift_id: number;
    date: string;
    status: 'scheduled' | 'completed' | 'cancelled';
}

export interface Request {
    id: number;
    user_id: number;
    type: 'leave' | 'salary_increase' | 'transfer' | 'other';
    title: string;
    description?: string;
    status: 'pending' | 'approved' | 'rejected';
    reviewed_by?: number;
    reviewed_at?: string;
    review_notes?: string;
    created_at: string;
    user_name?: string;
    reviewer_name?: string;
}

export interface Notification {
    id: number;
    user_id: number;
    title: string;
    message: string;
    type: string;
    is_read: boolean;
    link?: string;
    created_at: string;
}

export interface DashboardStats {
    total_messages: number;
    pending_messages: number;
    completed_messages: number;
    total_users: number;
    total_departments: number;
    total_requests: number;
    pending_requests: number;
}

export interface LoginRequest {
    email: string;
    password: string;
}

export interface LoginResponse {
    access_token: string;
    token_type: string;
}
