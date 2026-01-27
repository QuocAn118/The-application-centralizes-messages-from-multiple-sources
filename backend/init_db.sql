-- Active: 1769480225896@@127.0.0.1@5432@omnichat_db
-- OmniChat Database Schema
-- PostgreSQL Database Initialization Script

-- Drop existing tables if they exist
DROP TABLE IF EXISTS notifications CASCADE;

DROP TABLE IF EXISTS message_assignments CASCADE;

DROP TABLE IF EXISTS messages CASCADE;

DROP TABLE IF EXISTS requests CASCADE;

DROP TABLE IF EXISTS user_shifts CASCADE;

DROP TABLE IF EXISTS shifts CASCADE;

DROP TABLE IF EXISTS kpis CASCADE;

DROP TABLE IF EXISTS keywords CASCADE;

DROP TABLE IF EXISTS customers CASCADE;

DROP TABLE IF EXISTS users CASCADE;

DROP TABLE IF EXISTS departments CASCADE;

-- Create departments table
CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(5555) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    role VARCHAR(20) NOT NULL CHECK (
        role IN ('admin', 'manager', 'staff')
    ),
    department_id INTEGER REFERENCES departments (id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create customers table
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    phone VARCHAR(20),
    email VARCHAR(255),
    zalo_id VARCHAR(255),
    meta_id VARCHAR(255),
    platform VARCHAR(50),
    city VARCHAR(100),
    total_orders INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create keywords table
CREATE TABLE keywords (
    id SERIAL PRIMARY KEY,
    keyword VARCHAR(255) NOT NULL,
    department_id INTEGER REFERENCES departments (id) ON DELETE CASCADE,
    priority INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create kpis table
CREATE TABLE kpis (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users (id) ON DELETE CASCADE,
    metric_name VARCHAR(255) NOT NULL,
    target_value DECIMAL(10, 2),
    current_value DECIMAL(10, 2) DEFAULT 0,
    period_start DATE,
    period_end DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create shifts table
CREATE TABLE shifts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    department_id INTEGER REFERENCES departments (id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create user_shifts table (shift assignments)
CREATE TABLE user_shifts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users (id) ON DELETE CASCADE,
    shift_id INTEGER REFERENCES shifts (id) ON DELETE CASCADE,
    date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'scheduled' CHECK (
        status IN (
            'scheduled',
            'completed',
            'cancelled'
        )
    ),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, shift_id, date)
);

-- Create messages table
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers (id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    platform VARCHAR(50) NOT NULL,
    external_id VARCHAR(255),
    direction VARCHAR(20) DEFAULT 'incoming' CHECK (
        direction IN ('incoming', 'outgoing')
    ),
    status VARCHAR(20) DEFAULT 'pending' CHECK (
        status IN (
            'pending',
            'assigned',
            'in_progress',
            'completed'
        )
    ),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create message_assignments table
CREATE TABLE message_assignments (
    id SERIAL PRIMARY KEY,
    message_id INTEGER REFERENCES messages (id) ON DELETE CASCADE,
    assigned_to INTEGER REFERENCES users (id) ON DELETE SET NULL,
    assigned_by INTEGER REFERENCES users (id) ON DELETE SET NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    notes TEXT,
    match_score DECIMAL(5, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create requests table (internal staff requests)
CREATE TABLE requests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users (id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL CHECK (
        type IN (
            'leave',
            'salary_increase',
            'transfer',
            'other'
        )
    ),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'pending' CHECK (
        status IN (
            'pending',
            'approved',
            'rejected'
        )
    ),
    reviewed_by INTEGER REFERENCES users (id) ON DELETE SET NULL,
    reviewed_at TIMESTAMP,
    review_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create notifications table
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users (id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(50) DEFAULT 'info',
    is_read BOOLEAN DEFAULT FALSE,
    link VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_users_email ON users (email);

CREATE INDEX idx_users_department ON users (department_id);

CREATE INDEX idx_users_role ON users (role);

CREATE INDEX idx_messages_customer ON messages (customer_id);

CREATE INDEX idx_messages_status ON messages (status);

CREATE INDEX idx_messages_created ON messages (created_at);

CREATE INDEX idx_message_assignments_assigned_to ON message_assignments (assigned_to);

CREATE INDEX idx_requests_user ON requests (user_id);

CREATE INDEX idx_requests_status ON requests (status);

CREATE INDEX idx_notifications_user ON notifications (user_id);

CREATE INDEX idx_notifications_read ON notifications (is_read);

CREATE INDEX idx_keywords_department ON keywords (department_id);

-- Insert sample data for testing

-- Insert departments
INSERT INTO
    departments (name, description)
VALUES (
        'Kinh doanh',
        'Phòng kinh doanh và bán hàng'
    ),
    (
        'Kỹ thuật',
        'Phòng hỗ trợ kỹ thuật'
    ),
    (
        'Chăm sóc khách hàng',
        'Phòng chăm sóc khách hàng'
    );

-- Insert admin user (password: admin123)
INSERT INTO
    users (
        email,
        password_hash,
        full_name,
        phone,
        role
    )
VALUES (
        'admin@omnichat.com',
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqVr/4Kfuy',
        'Quản trị viên',
        '0901234567',
        'admin'
    );

-- Insert manager users (password: manager123)
INSERT INTO
    users (
        email,
        password_hash,
        full_name,
        phone,
        role,
        department_id
    )
VALUES (
        'manager.sales@omnichat.com',
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqVr/4Kfuy',
        'Nguyễn Văn A',
        '0902234567',
        'manager',
        1
    ),
    (
        'manager.tech@omnichat.com',
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqVr/4Kfuy',
        'Trần Thị B',
        '0903234567',
        'manager',
        2
    ),
    (
        'manager.cs@omnichat.com',
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqVr/4Kfuy',
        'Lê Văn C',
        '0904234567',
        'manager',
        3
    );

-- Insert staff users (password: staff123)
INSERT INTO
    users (
        email,
        password_hash,
        full_name,
        phone,
        role,
        department_id
    )
VALUES (
        'staff1@omnichat.com',
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqVr/4Kfuy',
        'Phạm Thị D',
        '0905234567',
        'staff',
        1
    ),
    (
        'staff2@omnichat.com',
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqVr/4Kfuy',
        'Hoàng Văn E',
        '0906234567',
        'staff',
        2
    ),
    (
        'staff3@omnichat.com',
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqVr/4Kfuy',
        'Vũ Thị F',
        '0907234567',
        'staff',
        3
    );

-- Insert keywords
INSERT INTO
    keywords (
        keyword,
        department_id,
        priority
    )
VALUES ('mua hàng', 1, 3),
    ('giá cả', 1, 3),
    ('khuyến mãi', 1, 2),
    ('lỗi', 2, 3),
    ('không hoạt động', 2, 3),
    ('cài đặt', 2, 2),
    ('hỗ trợ', 3, 2),
    ('khiếu nại', 3, 3),
    ('đổi trả', 3, 2);

-- Insert sample customers
INSERT INTO
    customers (
        name,
        phone,
        email,
        platform,
        city,
        total_orders
    )
VALUES (
        'Nguyễn Văn A',
        '0911111111',
        'customer1@example.com',
        'facebook',
        'Hà Nội',
        5
    ),
    (
        'Lê Thị B',
        '0922222222',
        'customer2@example.com',
        'zalo',
        'Hồ Chí Minh',
        3
    ),
    (
        'Trần Văn C',
        '0933333333',
        'customer3@example.com',
        'email',
        'Đà Nẵng',
        8
    );

-- Insert sample KPIs
INSERT INTO
    kpis (
        user_id,
        metric_name,
        target_value,
        current_value,
        period_start,
        period_end
    )
VALUES (
        5,
        'Số tin nhắn xử lý',
        100,
        45,
        '2026-01-01',
        '2026-01-31'
    ),
    (
        6,
        'Số tin nhắn xử lý',
        100,
        52,
        '2026-01-01',
        '2026-01-31'
    ),
    (
        7,
        'Số tin nhắn xử lý',
        100,
        38,
        '2026-01-01',
        '2026-01-31'
    );

-- Insert sample shifts
INSERT INTO
    shifts (
        name,
        start_time,
        end_time,
        department_id
    )
VALUES (
        'Ca sáng',
        '08:00:00',
        '12:00:00',
        1
    ),
    (
        'Ca chiều',
        '13:00:00',
        '17:00:00',
        1
    ),
    (
        'Ca tối',
        '18:00:00',
        '22:00:00',
        1
    );

-- Insert sample messages
INSERT INTO
    messages (
        customer_id,
        content,
        platform,
        status
    )
VALUES (
        1,
        'Tôi muốn mua sản phẩm X, giá bao nhiêu?',
        'zalo',
        'pending'
    ),
    (
        2,
        'Sản phẩm của tôi bị lỗi, không hoạt động được',
        'zalo',
        'pending'
    ),
    (
        3,
        'Tôi muốn được hỗ trợ về dịch vụ',
        'facebook',
        'pending'
    );

COMMENT ON TABLE departments IS 'Bảng quản lý phòng ban';

COMMENT ON TABLE users IS 'Bảng quản lý người dùng (admin, manager, staff)';

COMMENT ON TABLE customers IS 'Bảng quản lý thông tin khách hàng';

COMMENT ON TABLE keywords IS 'Bảng quản lý từ khóa cho phân loại tin nhắn';

COMMENT ON TABLE kpis IS 'Bảng quản lý KPI của nhân viên';

COMMENT ON TABLE shifts IS 'Bảng quản lý ca làm việc';

COMMENT ON TABLE user_shifts IS 'Bảng phân công ca làm việc cho nhân viên';

COMMENT ON TABLE messages IS 'Bảng lưu trữ tin nhắn từ khách hàng';

COMMENT ON TABLE message_assignments IS 'Bảng phân công xử lý tin nhắn';

COMMENT ON TABLE requests IS 'Bảng quản lý yêu cầu nội bộ của nhân viên';

COMMENT ON TABLE notifications IS 'Bảng quản lý thông báo hệ thống';


-- Insert additional sample customers with detailed information
INSERT INTO
    customers (
        name,
        phone,
        email,
        platform,
        city,
        total_orders
    )
VALUES (
        'Nguyen Thi Huong',
        '0987654321',
        'huong.nguyen@gmail.com',
        'zalo',
        'Ha Noi',
        12
    ),
    (
        'Tran Van Minh',
        '0912345678',
        'minh.tran@yahoo.com',
        'facebook',
        'Ho Chi Minh',
        5
    ),
    (
        'Le Thi Mai',
        '0909876543',
        'mai.le@outlook.com',
        'zalo',
        'Da Nang',
        8
    ),
    (
        'Pham Quoc Anh',
        '0938765432',
        'anh.pham@gmail.com',
        'facebook',
        'Hai Phong',
        3
    );

-- Insert detailed sample messages from customers
INSERT INTO
    messages (
        customer_id,
        content,
        platform,
        direction,
        status
    )
VALUES (
        (SELECT id FROM customers WHERE phone = '0987654321'),
        'Chào shop, em muốn hỏi về sản phẩm iPhone 15 Pro Max hiện tại còn hàng không ?? Giá bao nhiêu và có khuyến mãi gì không?',
        'zalo',
        'incoming',
        'assigned'
    ),
    (
        (SELECT id FROM customers WHERE phone = '0912345678'),
        'Sản phẩm em mua hôm qua bị lỗi không hoạt động được. Màn hình có nhấp nháy rồi tắt nguồn. Em cần được hỗ trợ cài đặt lại.',
        'facebook',
        'incoming',
        'assigned'
    ),
    (
        (SELECT id FROM customers WHERE phone = '0909876543'),
        'Em muốn được hỗ trợ về chính sách đổi trả hàng. Em mua sản phẩm được 3 ngày nhưng không vừa ý, có thể đổi sang sản phẩm khác được không ??',
        'zalo',
        'incoming',
        'assigned'
    ),
    (
        (SELECT id FROM customers WHERE phone = '0938765432'),
        'Shop cho em hỏi giá cả của laptop Dell Inspiron 15 bao nhiêu? Hiện tại có chương trình khuyến mãi nào không?',
        'facebook',
        'incoming',
        'assigned'
    );

-- Assign messages to appropriate staff members
INSERT INTO
    message_assignments (
        message_id,
        assigned_to,
        assigned_by,
        match_score,
        notes
    )
SELECT
    m.id,
    (SELECT id FROM users WHERE email = 'staff1@omnichat.com'),
    (SELECT id FROM users WHERE email = 'manager.sales@omnichat.com'),
    95.5,
    'Tự động gán dựa trên từ khóa: mua hàng, giá, khuyến mãi'
FROM messages m
JOIN customers c ON m.customer_id = c.id
WHERE c.phone = '0987654321'
AND m.content LIKE '%iPhone%';

INSERT INTO
    message_assignments (
        message_id,
        assigned_to,
        assigned_by,
        match_score,
        notes
    )
SELECT
    m.id,
    (SELECT id FROM users WHERE email = 'staff2@omnichat.com'),
    (SELECT id FROM users WHERE email = 'manager.tech@omnichat.com'),
    98.0,
    'Tự động gán dựa trên từ khóa: lỗi, không hoạt động, cài đặt'
FROM messages m
JOIN customers c ON m.customer_id = c.id
WHERE c.phone = '0912345678'
AND m.content LIKE '%lỗi%';
INSERT INTO
    message_assignments (
        message_id,
        assigned_to,
        assigned_by,
        match_score,
        notes
    )
SELECT
    m.id,
    (SELECT id FROM users WHERE email = 'staff3@omnichat.com'),
    (SELECT id FROM users WHERE email = 'manager.cs@omnichat.com'),
    92.0,
    'Tự động gán dựa trên từ khóa: hỗ trợ, đổi trả'
FROM messages m
JOIN customers c ON m.customer_id = c.id
WHERE c.phone = '0909876543'
AND m.content LIKE '%hỗ trợ%';
INSERT INTO
    message_assignments (
        message_id,
        assigned_to,
        assigned_by,
        match_score,
        notes
    )
SELECT
    m.id,
    (SELECT id FROM users WHERE email = 'staff1@omnichat.com'),
    (SELECT id FROM users WHERE email = 'manager.sales@omnichat.com'),
    90.0,
    'Tự động gán dựa trên từ khóa: giá cả, khuyến mãi'
FROM messages m
JOIN customers c ON m.customer_id = c.id
WHERE c.phone = '0938765432'
AND m.content LIKE '%laptop%';

ALTER TABLE customers ADD COLUMN telegram_id VARCHAR(255);