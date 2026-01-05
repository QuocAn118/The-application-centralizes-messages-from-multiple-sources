-- Active: 1767346754964@@127.0.0.1@5432@omnichat
-- Initialize database schema for OmniChat (Postgres)

CREATE TABLE IF NOT EXISTS departments (
  id SERIAL PRIMARY KEY,
  name TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  username TEXT UNIQUE,
  full_name TEXT,
  hashed_password TEXT,
  role TEXT,
  department_id INTEGER REFERENCES departments(id),
  kpi_score FLOAT DEFAULT 0.0,
  status TEXT DEFAULT 'available'
);

CREATE TABLE IF NOT EXISTS keywords (
  id SERIAL PRIMARY KEY,
  word TEXT UNIQUE,
  department_id INTEGER REFERENCES departments(id)
);

CREATE TABLE IF NOT EXISTS messages (
  id SERIAL PRIMARY KEY,
  platform TEXT,
  sender TEXT,
  content TEXT,
  received_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  keywords TEXT,
  assigned_to INTEGER REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS assignments (
  id SERIAL PRIMARY KEY,
  message_id INTEGER REFERENCES messages(id),
  user_id INTEGER REFERENCES users(id),
  assigned_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  status TEXT DEFAULT 'open'
);

CREATE TABLE IF NOT EXISTS requests (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  request_type TEXT,
  description TEXT,
  status TEXT DEFAULT 'pending',
  submitted_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  reviewed_at TIMESTAMP WITH TIME ZONE,
  reviewed_by INTEGER REFERENCES users(id),
  notes TEXT
);

CREATE TABLE IF NOT EXISTS shifts (
  id SERIAL PRIMARY KEY,
  department_id INTEGER REFERENCES departments(id),
  shift_name TEXT,
  start_time TEXT,
  end_time TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE IF NOT EXISTS shift_assignments (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  shift_id INTEGER REFERENCES shifts(id),
  assigned_date TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE IF NOT EXISTS time_tracking (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  check_in_time TIMESTAMP WITH TIME ZONE,
  check_out_time TIMESTAMP WITH TIME ZONE,
  date TEXT
);

CREATE TABLE IF NOT EXISTS kpi_metrics (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  metric_name TEXT,
  metric_value FLOAT,
  period TEXT,
  recorded_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
