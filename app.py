from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
import random
import string
import qrcode
import os
from datetime import datetime
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = 'qrattendance2026'
DB = 'attendance.db'

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'greatsky176@gmail.com'
app.config['MAIL_PASSWORD'] = 'ihkvfykxwcznfhgd'
mail = Mail(app)
def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def send_otp(email):
    otp = str(random.randint(100000, 999999))
    session['otp'] = otp
    session['otp_email'] = email
    try:
        msg = Message('Your OTP - Attendance System',
                      sender='greatsky176@gmail.com',
                      recipients=[email])
        msg.body = f'Your OTP is: {otp}\nValid for 10 minutes.'
        mail.send(msg)
        print("OTP sent to:", email)
    except Exception as e:
        print("EMAIL ERROR:", str(e))
        raise e
    return otp

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/teacher/register', methods=['GET', 'POST'])
def teacher_register():
    error = None
    step = session.get('register_step', 1)
    if request.method == 'POST':
        if 'send_otp' in request.form:
            email = request.form['email']
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute("SELECT * FROM teachers WHERE email=?", (email,))
            existing = c.fetchone()
            conn.close()
            if existing:
                error = "Email already registered!"
            else:
                session['reg_name'] = request.form['name']
                session['reg_college'] = request.form['college']
                session['reg_email'] = email
                session['reg_password'] = request.form['password']
                session['register_step'] = 2
                try:
                    send_otp(email)
                    step = 2
                except:
                    error = "Failed to send OTP!"
                    session['register_step'] = 1
                    step = 1
        elif 'verify_otp' in request.form:
            if request.form['otp'] == session.get('otp'):
                code = generate_code()
                conn = sqlite3.connect(DB)
                c = conn.cursor()
                c.execute("INSERT INTO teachers (name, email, password, college, code) VALUES (?,?,?,?,?)",
                          (session['reg_name'], session['reg_email'],
                           session['reg_password'], session['reg_college'], code))
                conn.commit()
                conn.close()
                session.pop('register_step', None)
                session.pop('otp', None)
                return redirect('/teacher/login')
            else:
                error = "Wrong OTP! Try again."
                step = 2
        elif 'resend_otp' in request.form:
            email = session.get('reg_email')
            try:
                send_otp(email)
                step = 2
            except:
                error = "Failed to resend OTP!"
                step = 2
    return render_template('teacher_register.html', error=error, step=step,
                           session_email=session.get('reg_email', ''))

@app.route('/teacher/login', methods=['GET', 'POST'])
def teacher_login():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT * FROM teachers WHERE email=? AND password=?", (email, password))
        teacher = c.fetchone()
        conn.close()
        if teacher:
            session['teacher_id'] = teacher[0]
            session['teacher_name'] = teacher[1]
            session['teacher_college'] = teacher[4]
            session['teacher_code'] = teacher[5]
            return redirect('/teacher/dashboard')
        else:
            error = "Wrong email or password!"
    return render_template('teacher_login.html', error=error)

@app.route('/teacher/forgot', methods=['GET', 'POST'])
def teacher_forgot():
    error = None
    message = None
    if request.method == 'GET':
        session['forgot_step'] = 1
        session.pop('forgot_email', None)
        session.pop('otp', None)
    step = session.get('forgot_step', 1)
    if request.method == 'POST':
        if 'send_otp' in request.form:
            email = request.form['email']
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute("SELECT * FROM teachers WHERE email=?", (email,))
            teacher = c.fetchone()
            conn.close()
            if not teacher:
                error = "Email not found!"
            else:
                session['forgot_email'] = email
                session['forgot_step'] = 2
                step = 2
                try:
                    send_otp(email)
                    message = "OTP sent to your email!"
                except Exception as e:
                    print("ERROR:", str(e))
                    error = "Failed to send OTP!"
                    session['forgot_step'] = 1
                    step = 1
        elif 'resend_otp' in request.form:
            email = session.get('forgot_email')
            try:
                send_otp(email)
                message = "OTP resent successfully!"
                step = 2
            except:
                error = "Failed to resend OTP!"
                step = 2
        elif 'verify_otp' in request.form:
            if request.form['otp'] == session.get('otp'):
                session['forgot_step'] = 3
                step = 3
            else:
                error = "Wrong OTP! Try again."
                step = 2
        elif 'reset_password' in request.form:
            new_password = request.form['password']
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute("UPDATE teachers SET password=? WHERE email=?",
                      (new_password, session.get('forgot_email')))
            conn.commit()
            conn.close()
            session.pop('forgot_step', None)
            session.pop('forgot_email', None)
            return redirect('/teacher/login')
    return render_template('forgot_password.html',
                           error=error, message=message,
                           step=step, user_type='teacher',
                           session_email=session.get('forgot_email', ''))

@app.route('/teacher/dashboard')
def teacher_dashboard():
    if 'teacher_id' not in session:
        return redirect('/teacher/login')
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM requests WHERE teacher_id=? AND status='pending'", (session['teacher_id'],))
    pending = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM requests WHERE teacher_id=? AND status='accepted'", (session['teacher_id'],))
    total_students = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM subjects WHERE teacher_id=?", (session['teacher_id'],))
    total_subjects = c.fetchone()[0]
    conn.close()
    return render_template('teacher_dashboard.html',
        name=session['teacher_name'],
        college=session['teacher_college'],
        code=session['teacher_code'],
        total_students=total_students,
        total_subjects=total_subjects,
        pending=pending)

@app.route('/teacher/classes', methods=['GET', 'POST'])
def teacher_classes():
    if 'teacher_id' not in session:
        return redirect('/teacher/login')
    message = None
    if request.method == 'POST':
        subject_name = request.form['subject_name']
        time_slot = request.form['time_slot']
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("INSERT INTO subjects (teacher_id, name, time_slot) VALUES (?,?,?)",
                  (session['teacher_id'], subject_name, time_slot))
        conn.commit()
        conn.close()
        message = f"{subject_name} added successfully!"
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM subjects WHERE teacher_id=?", (session['teacher_id'],))
    subjects = c.fetchall()
    conn.close()
    return render_template('teacher_classes.html', subjects=subjects, message=message)

@app.route('/teacher/delete_subject/<int:subject_id>')
def delete_subject(subject_id):
    if 'teacher_id' not in session:
        return redirect('/teacher/login')
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM subjects WHERE id=? AND teacher_id=?", (subject_id, session['teacher_id']))
    conn.commit()
    conn.close()
    return redirect('/teacher/classes')

@app.route('/teacher/approvals')
def teacher_approvals():
    if 'teacher_id' not in session:
        return redirect('/teacher/login')
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""SELECT s.id, s.name, s.college FROM requests r
                 JOIN students s ON r.student_id = s.id
                 WHERE r.teacher_id=? AND r.status='pending'""", (session['teacher_id'],))
    pending = c.fetchall()
    c.execute("""SELECT s.id, s.name, s.college FROM requests r
                 JOIN students s ON r.student_id = s.id
                 WHERE r.teacher_id=? AND r.status='accepted'""", (session['teacher_id'],))
    accepted = c.fetchall()
    c.execute("""SELECT s.id, s.name, s.college FROM requests r
                 JOIN students s ON r.student_id = s.id
                 WHERE r.teacher_id=? AND r.status='rejected'""", (session['teacher_id'],))
    rejected = c.fetchall()
    conn.close()
    return render_template('teacher_approvals.html',
        pending=pending, accepted=accepted, rejected=rejected)

@app.route('/teacher/approve/<int:student_id>')
def approve_student(student_id):
    if 'teacher_id' not in session:
        return redirect('/teacher/login')
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE requests SET status='accepted' WHERE student_id=? AND teacher_id=?",
              (student_id, session['teacher_id']))
    conn.commit()
    conn.close()
    return redirect('/teacher/approvals')

@app.route('/teacher/reject/<int:student_id>')
def reject_student(student_id):
    if 'teacher_id' not in session:
        return redirect('/teacher/login')
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE requests SET status='rejected' WHERE student_id=? AND teacher_id=?",
              (student_id, session['teacher_id']))
    conn.commit()
    conn.close()
    return redirect('/teacher/approvals')

@app.route('/teacher/remove/<int:student_id>')
def remove_student(student_id):
    if 'teacher_id' not in session:
        return redirect('/teacher/login')
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE requests SET status='rejected' WHERE student_id=? AND teacher_id=?",
              (student_id, session['teacher_id']))
    conn.commit()
    conn.close()
    return redirect('/teacher/approvals')

@app.route('/teacher/scanner')
def teacher_scanner():
    if 'teacher_id' not in session:
        return redirect('/teacher/login')
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM subjects WHERE teacher_id=?", (session['teacher_id'],))
    subjects = c.fetchall()
    conn.close()
    return render_template('teacher_scanner.html', subjects=subjects)

@app.route('/teacher/mark_attendance', methods=['POST'])
def mark_attendance():
    data = request.get_json()
    qr_data = data['qr_data']
    subject_id = data['subject_id']
    student_id = qr_data.replace('STUDENT_ID:', '')
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM students WHERE id=?", (student_id,))
    student = c.fetchone()
    if not student:
        conn.close()
        return jsonify({'success': False, 'message': '❌ Student not found!'})
    c.execute("SELECT * FROM requests WHERE student_id=? AND teacher_id=? AND status='accepted'",
              (student_id, session['teacher_id']))
    approved = c.fetchone()
    if not approved:
        conn.close()
        return jsonify({'success': False, 'message': '❌ Student not approved!'})
    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    time = now.strftime("%H:%M:%S")
    c.execute("SELECT * FROM attendance WHERE student_id=? AND subject_id=? AND date=?",
              (student_id, subject_id, date))
    already = c.fetchone()
    if already:
        conn.close()
        return jsonify({'success': False, 'message': f'⚠️ {student[1]} already marked today!'})
    c.execute("INSERT INTO attendance (student_id, teacher_id, subject_id, date, time) VALUES (?,?,?,?,?)",
              (student_id, session['teacher_id'], subject_id, date, time))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': f'✅ {student[1]} marked present!'})

@app.route('/teacher/attendance')
def teacher_attendance():
    if 'teacher_id' not in session:
        return redirect('/teacher/login')
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM subjects WHERE teacher_id=?", (session['teacher_id'],))
    subjects = c.fetchall()
    selected_subject = request.args.get('subject_id')
    records = []
    if selected_subject:
        c.execute("""SELECT s.name, s.college, a.date, a.time
                     FROM attendance a
                     JOIN students s ON a.student_id = s.id
                     WHERE a.teacher_id=? AND a.subject_id=?
                     ORDER BY a.date DESC, a.time DESC""",
                  (session['teacher_id'], selected_subject))
        records = c.fetchall()
    conn.close()
    return render_template('teacher_attendance.html',
        subjects=subjects, records=records, selected_subject=selected_subject)

@app.route('/student/register', methods=['GET', 'POST'])
def student_register():
    error = None
    step = session.get('student_register_step', 1)
    if request.method == 'POST':
        if 'send_otp' in request.form:
            email = request.form['email']
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute("SELECT * FROM students WHERE email=?", (email,))
            existing = c.fetchone()
            conn.close()
            if existing:
                error = "Email already registered!"
            else:
                session['s_reg_name'] = request.form['name']
                session['s_reg_college'] = request.form['college']
                session['s_reg_email'] = email
                session['s_reg_password'] = request.form['password']
                session['student_register_step'] = 2
                step = 2
                try:
                    send_otp(email)
                except:
                    error = "Failed to send OTP!"
                    session['student_register_step'] = 1
                    step = 1
        elif 'verify_otp' in request.form:
            if request.form['otp'] == session.get('otp'):
                conn = sqlite3.connect(DB)
                c = conn.cursor()
                c.execute("INSERT INTO students (name, email, password, college) VALUES (?,?,?,?)",
                          (session['s_reg_name'], session['s_reg_email'],
                           session['s_reg_password'], session['s_reg_college']))
                conn.commit()
                conn.close()
                session.pop('student_register_step', None)
                session.pop('otp', None)
                return redirect('/student/login')
            else:
                error = "Wrong OTP! Try again."
                step = 2
        elif 'resend_otp' in request.form:
            email = session.get('s_reg_email')
            try:
                send_otp(email)
                step = 2
            except:
                error = "Failed to resend OTP!"
                step = 2
    return render_template('student_register.html', error=error, step=step,
                           session_email=session.get('s_reg_email', ''))

@app.route('/student/login', methods=['GET', 'POST'])
def student_login():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT * FROM students WHERE email=? AND password=?", (email, password))
        student = c.fetchone()
        conn.close()
        if student:
            session['student_id'] = student[0]
            session['student_name'] = student[1]
            session['student_college'] = student[4]
            return redirect('/student/dashboard')
        else:
            error = "Wrong email or password!"
    return render_template('student_login.html', error=error)

@app.route('/student/forgot', methods=['GET', 'POST'])
def student_forgot():
    error = None
    message = None
    if request.method == 'GET':
        session['s_forgot_step'] = 1
        session.pop('s_forgot_email', None)
        session.pop('otp', None)
    step = session.get('s_forgot_step', 1)
    if request.method == 'POST':
        if 'send_otp' in request.form:
            email = request.form['email']
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute("SELECT * FROM students WHERE email=?", (email,))
            student = c.fetchone()
            conn.close()
            if not student:
                error = "Email not found!"
            else:
                session['s_forgot_email'] = email
                session['s_forgot_step'] = 2
                step = 2
                try:
                    send_otp(email)
                    message = "OTP sent to your email!"
                except Exception as e:
                    print("ERROR:", str(e))
                    error = "Failed to send OTP!"
                    session['s_forgot_step'] = 1
                    step = 1
        elif 'resend_otp' in request.form:
            email = session.get('s_forgot_email')
            try:
                send_otp(email)
                message = "OTP resent successfully!"
                step = 2
            except:
                error = "Failed to resend OTP!"
                step = 2
        elif 'verify_otp' in request.form:
            if request.form['otp'] == session.get('otp'):
                session['s_forgot_step'] = 3
                step = 3
            else:
                error = "Wrong OTP! Try again."
                step = 2
        elif 'reset_password' in request.form:
            new_password = request.form['password']
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute("UPDATE students SET password=? WHERE email=?",
                      (new_password, session.get('s_forgot_email')))
            conn.commit()
            conn.close()
            session.pop('s_forgot_step', None)
            return redirect('/student/login')
    return render_template('forgot_password.html',
                           error=error, message=message,
                           step=step, user_type='student',
                           session_email=session.get('s_forgot_email', ''))

@app.route('/student/dashboard')
def student_dashboard():
    if 'student_id' not in session:
        return redirect('/student/login')
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM requests WHERE student_id=? AND status='accepted'", (session['student_id'],))
    total_teachers = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM requests WHERE student_id=? AND status='pending'", (session['student_id'],))
    pending = c.fetchone()[0]
    conn.close()
    return render_template('student_dashboard.html',
        name=session['student_name'],
        college=session['student_college'],
        total_teachers=total_teachers,
        pending=pending)

@app.route('/student/qr')
def student_qr():
    if 'student_id' not in session:
        return redirect('/student/login')
    qr_folder = 'static/qrcodes'
    os.makedirs(qr_folder, exist_ok=True)
    qr_path = f"{qr_folder}/{session['student_id']}.png"
    qr_data = f"STUDENT_ID:{session['student_id']}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=20,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(qr_path)
    return render_template('student_qr.html',
        student_id=session['student_id'],
        name=session['student_name'],
        college=session['student_college'])

@app.route('/student/join', methods=['GET', 'POST'])
def student_join():
    if 'student_id' not in session:
        return redirect('/student/login')
    message = None
    error = None
    if request.method == 'POST':
        code = request.form['code'].upper()
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT * FROM teachers WHERE code=?", (code,))
        teacher = c.fetchone()
        if not teacher:
            error = "Invalid code! Please check with your teacher."
        else:
            c.execute("SELECT * FROM requests WHERE student_id=? AND teacher_id=?",
                      (session['student_id'], teacher[0]))
            existing = c.fetchone()
            if existing:
                if existing[3] == 'rejected':
                    c.execute("UPDATE requests SET status='pending' WHERE student_id=? AND teacher_id=?",
                              (session['student_id'], teacher[0]))
                    conn.commit()
                    message = "Request sent again!"
                else:
                    error = "Request already sent!"
            else:
                c.execute("INSERT INTO requests (student_id, teacher_id, status) VALUES (?,?,?)",
                          (session['student_id'], teacher[0], 'pending'))
                conn.commit()
                message = "Request sent to teacher successfully!"
        conn.close()
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""SELECT t.name, t.college, r.status FROM requests r
                 JOIN teachers t ON r.teacher_id = t.id
                 WHERE r.student_id=?""", (session['student_id'],))
    requests_list = c.fetchall()
    conn.close()
    return render_template('student_join.html',
        message=message, error=error, requests=requests_list)

@app.route('/student/attendance')
def student_attendance():
    if 'student_id' not in session:
        return redirect('/student/login')
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""SELECT t.id, t.name, t.college FROM requests r
                 JOIN teachers t ON r.teacher_id = t.id
                 WHERE r.student_id=? AND r.status='accepted'""", (session['student_id'],))
    teachers = c.fetchall()
    selected_teacher = request.args.get('teacher_id')
    records = []
    percentage = 0
    total = 0
    present = 0
    if selected_teacher:
        c.execute("""SELECT sub.name, a.date, a.time FROM attendance a
                     JOIN subjects sub ON a.subject_id = sub.id
                     WHERE a.student_id=? AND a.teacher_id=?
                     ORDER BY a.date DESC""",
                  (session['student_id'], selected_teacher))
        records = c.fetchall()
        present = len(records)
        c.execute("SELECT COUNT(DISTINCT date) FROM attendance WHERE teacher_id=?", (selected_teacher,))
        total = c.fetchone()[0]
        if total > 0:
            percentage = round((present / total) * 100)
    conn.close()
    return render_template('student_attendance.html',
        teachers=teachers, records=records,
        selected_teacher=selected_teacher,
        percentage=percentage, present=present, total=total)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')