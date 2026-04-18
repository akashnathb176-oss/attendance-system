import sqlite3

DB = 'c:/project/attendance_v2/attendance.db'

conn = sqlite3.connect(DB)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS teachers (
    id INTEGER PRIMARY KEY,
    name TEXT,
    email TEXT UNIQUE,
    password TEXT,
    college TEXT,
    code TEXT UNIQUE,
    photo TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY,
    name TEXT,
    email TEXT UNIQUE,
    password TEXT,
    college TEXT,
    photo TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY,
    student_id INTEGER,
    teacher_id INTEGER,
    status TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY,
    teacher_id INTEGER,
    name TEXT,
    time_slot TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY,
    student_id INTEGER,
    teacher_id INTEGER,
    subject_id INTEGER,
    date TEXT,
    time TEXT
)''')

conn.commit()
conn.close()
print("Database ready!")