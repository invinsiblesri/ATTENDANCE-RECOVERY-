-- ====================================================================
-- AI Attendance Recovery Agent - Database Schema (SQLite)
-- Prototype Schema for College Hackathon Project
-- ====================================================================

PRAGMA foreign_keys = ON;

-- 1. Students Table (20 Students: S001 to S020)
CREATE TABLE IF NOT EXISTS students (
    student_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    year INTEGER NOT NULL,
    semester INTEGER NOT NULL
);

-- 2. Subjects Table (8 Equal Subjects, No Priority/Weighting)
CREATE TABLE IF NOT EXISTS subjects (
    subject_id TEXT PRIMARY KEY,
    subject_code TEXT UNIQUE NOT NULL,
    subject_name TEXT NOT NULL
);

-- 3. Timetable Table (Monday to Friday, 8 Periods/Day = 40 Slots)
CREATE TABLE IF NOT EXISTS timetable (
    timetable_id INTEGER PRIMARY KEY AUTOINCREMENT,
    day_of_week TEXT NOT NULL CHECK(day_of_week IN ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday')),
    period_number INTEGER NOT NULL CHECK(period_number BETWEEN 1 AND 8),
    subject_id TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE RESTRICT,
    CONSTRAINT unique_timetable_slot UNIQUE (day_of_week, period_number)
);

-- 4. Attendance Records Table (Period-Wise / Class-Wise Truth)
CREATE TABLE IF NOT EXISTS attendance_records (
    attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    date TEXT NOT NULL, -- Format: YYYY-MM-DD
    period_number INTEGER NOT NULL CHECK(period_number BETWEEN 1 AND 8),
    status TEXT NOT NULL CHECK(status IN ('Present', 'Absent')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE RESTRICT,
    CONSTRAINT unique_student_date_period UNIQUE (student_id, date, period_number)
);

-- 5. Leave Records Table
CREATE TABLE IF NOT EXISTS leave_records (
    leave_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    date TEXT NOT NULL, -- Format: YYYY-MM-DD
    reason TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('Pending', 'Approved', 'Rejected')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
);

-- 6. Notifications Table (Stored in SQLite, retrieved by AI Agent / Notification Consumer)
CREATE TABLE IF NOT EXISTS notifications (
    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    subject_id TEXT,
    message TEXT NOT NULL,
    priority TEXT NOT NULL CHECK(priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_read INTEGER NOT NULL DEFAULT 0 CHECK(is_read IN (0, 1)),
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE SET NULL
);

-- 7. Persistent Attendance Memory Table (Attendance-Only Events)
CREATE TABLE IF NOT EXISTS attendance_memory (
    memory_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    subject_id TEXT,
    event_type TEXT NOT NULL CHECK(event_type IN ('WARNING', 'STATUS_CHANGE', 'RECOVERY_PLAN', 'AGENT_ACTION', 'IMPORTANT_EVENT')),
    description TEXT NOT NULL,
    metadata TEXT, -- JSON-formatted structured context
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE SET NULL
);

-- Indexes for optimal lookup performance
CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance_records(student_id);
CREATE INDEX IF NOT EXISTS idx_attendance_student_subject ON attendance_records(student_id, subject_id);
CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance_records(date);
CREATE INDEX IF NOT EXISTS idx_timetable_day_period ON timetable(day_of_week, period_number);
CREATE INDEX IF NOT EXISTS idx_notifications_student ON notifications(student_id, is_read);
CREATE INDEX IF NOT EXISTS idx_memory_student ON attendance_memory(student_id);
CREATE INDEX IF NOT EXISTS idx_memory_student_subject ON attendance_memory(student_id, subject_id);