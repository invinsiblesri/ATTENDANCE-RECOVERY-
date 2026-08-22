import sqlite3
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

db_path = 'data/attendance_system.db'
if not os.path.exists(db_path):
    print('ERROR: DB file not found at', db_path)
    exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# 1. Integrity check
cur.execute('PRAGMA integrity_check;')
print('INTEGRITY CHECK:', [dict(r) for r in cur.fetchall()])

# 2. Tables and counts
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
tables = [r['name'] for r in cur.fetchall()]
print('\n=== TABLES AND ROW COUNTS ===')
for t in tables:
    cur.execute(f'SELECT COUNT(*) as cnt FROM {t}')
    count = cur.fetchone()['cnt']
    print(f'Table: {t:<25} | Rows: {count}')

# 3. Sample check on students
print('\n=== STUDENTS SAMPLE ===')
cur.execute('SELECT * FROM students LIMIT 5;')
for r in cur.fetchall():
    print(dict(r))

# 4. Check S001 Attendance summary
print('\n=== S001 ATTENDANCE BY SUBJECT ===')
cur.execute('''
    SELECT s.subject_code, s.subject_name, ah.conducted_classes, ah.attended_classes, ah.attendance_percentage
    FROM attendance_history ah
    JOIN subjects s ON ah.subject_id = s.subject_id
    WHERE ah.student_id = 'S001';
''')
for r in cur.fetchall():
    print(dict(r))

# 5. Check Timetable
print('\n=== TIMETABLE SLOTS PER DAY ===')
cur.execute('SELECT day_of_week, COUNT(*) as cnt FROM timetable GROUP BY day_of_week;')
for r in cur.fetchall():
    print(dict(r))

# 6. Check Notifications
print('\n=== RECENT NOTIFICATIONS ===')
cur.execute('SELECT * FROM notifications ORDER BY created_at DESC LIMIT 5;')
for r in cur.fetchall():
    print(dict(r))

# 7. Check Memory
print('\n=== RECENT MEMORY EVENTS ===')
cur.execute('SELECT * FROM attendance_memory ORDER BY created_at DESC LIMIT 5;')
for r in cur.fetchall():
    print(dict(r))
