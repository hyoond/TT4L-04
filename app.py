from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import datetime

#temporarily for test
conn = sqlite3.connect('database.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS enrollments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        course_id INTEGER NOT NULL,
        FOREIGN KEY (user_email) REFERENCES users(email),
        FOREIGN KEY (course_id) REFERENCES courses(id)
    )
''')
conn.commit()
conn.close()


app = Flask(__name__)
app.secret_key = 'supersecretkey123'

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Helper: File type check
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Helper: Password validation
def valid_password(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not any(char.isdigit() for char in password):
        return False, "Password must include at least one number."
    if not any(char in "!@#$%^&*()_-+=<>:;?/,.{[]}" for char in password):
        return False, "Password must include at least one symbol."
    return True, ""

# Routes
@app.route('/')
def home():
    alert = session.pop("alert", None)
    return render_template('home.html', alert=alert)

@app.route('/signup', methods=['GET'])
def signup_form():
    return render_template('signup.html')

@app.route('/signup', methods=['POST'])
def signup():
    email = request.form['email']
    password = request.form['password']
    username = request.form['username']

    if not email.endswith("mmu.edu.my"):
        return render_template("signup.html", alert="Only MMU email addresses are allowed.")

    is_valid, alert = valid_password(password)
    if not is_valid:
        return render_template("signup.html", alert=alert)

    insert_user(email, password, username)
    alert = f"User {username} added successfully!"
    return render_template("login.html", alert=alert)

@app.route('/login')
def login_form():
    alert = session.pop('alert', None)
    return render_template('login.html', alert=alert)

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    user = compare_database(email, password)

    if user:
        session['username'] = user[2]
        session['email'] = user[1]
        session['role'] = user[4]
        session['alert'] = "Login successfully"

        if user[4] == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('dashboard'))
    else:
        return render_template("login.html", alert="User not found or incorrect password")

@app.route('/dashboard')
def dashboard():
    alert = session.pop('alert', None)
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Fetch timetable entries
    cursor.execute('''
    SELECT subject, day, start_time, end_time, location
    FROM courses
    WHERE id IN (
        SELECT course_id FROM enrollments WHERE user_email = ?
    )
''', (session['email'],))
    timetable_data = cursor.fetchall()

    # Fetch user settings
    cursor.execute('SELECT time_format FROM settings WHERE email = ?', (session['email'],))
    settings_data = cursor.fetchone()

    cursor.execute('''
        SELECT * FROM courses WHERE id NOT IN (
            SELECT c.id FROM courses c
            JOIN timetable t ON 
                c.subject = t.subject AND 
                c.day = t.day AND 
                c.start_time = t.start_time AND 
                c.end_time = t.end_time AND 
                c.location = t.location
            WHERE t.email = ?
        )
    ''', (session['email'],))
    available_courses = cursor.fetchall() 

    conn.close()

    time_format = settings_data[0] if settings_data else '24h'

    formatted_timetable = []
    for entry in timetable_data:
        subject, day, start_str, end_str, location = entry

        # Convert string times to datetime objects
        start_dt = datetime.strptime(start_str, '%H:%M')
        end_dt = datetime.strptime(end_str, '%H:%M')

        # Format according to user setting
        if time_format == '12h':
            formatted_start = start_dt.strftime('%I:%M %p')
            formatted_end = end_dt.strftime('%I:%M %p')
        else:
            formatted_start = start_dt.strftime('%H:%M')
            formatted_end = end_dt.strftime('%H:%M')

        formatted_timetable.append((subject, day, formatted_start, formatted_end, location))

    return render_template(
        'dashboard.html',
        username=session['username'],
        alert=alert,
        timetable=formatted_timetable,
        settings=settings_data,
        available_courses=available_courses
    )

@app.route('/enroll_course', methods=['POST'])
def enroll_course():
    if 'email' not in session:
        session['alert'] = "Please login first"
        return redirect(url_for('login'))

    course_id = request.form.get('course_id')
    email = session['email']

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Create enrollments table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            course_id INTEGER NOT NULL,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        )
    ''')

    # Check if already enrolled
    cursor.execute('SELECT * FROM enrollments WHERE user_email = ? AND course_id = ?', (email, course_id))
    already_enrolled = cursor.fetchone()

    if already_enrolled:
        session['alert'] = "You are already enrolled in this course."
    else:
        cursor.execute('INSERT INTO enrollments (user_email, course_id) VALUES (?, ?)', (email, course_id))
        conn.commit()
        session['alert'] = "Enrolled in course successfully!"

    conn.close()
    return redirect(url_for('dashboard'))



@app.route('/logout', methods=['POST', 'GET'])
def logout():
    session.clear()
    session['alert'] = "Logout successfully"
    return redirect(url_for('home'))

@app.route('/timetable', methods=['GET', 'POST'])
def timetable():
    if 'username' not in session:
        session['alert'] = "Please login first"
        return redirect(url_for('login'))

    if request.method == 'POST':
        subject = request.form['subject']
        day = request.form['day']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        location = request.form['location']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO timetable (email, subject, day, start_time, end_time, location)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session['email'], subject, day, start_time, end_time, location))
        conn.commit()
        conn.close()
        session['alert'] = "Timetable added successfully"
        return redirect(url_for('dashboard'))

    return render_template('timetable.html')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'email' not in session:
        session['alert'] = "Please login first"
        return redirect(url_for('login'))

    email = session['email']
    role = session.get('role')
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        time_format = request.form.get('time_format')
        cursor.execute('''
            UPDATE settings SET time_format = ?
            WHERE email = ?
        ''', (time_format, email))
        conn.commit()
        session['alert'] = "Settings updated successfully"
        if role == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('dashboard'))


    cursor.execute('SELECT time_format FROM settings WHERE email = ?', (email,))
    settings_data = cursor.fetchone()
    conn.close()

    return render_template('settings.html', settings=settings_data)

@app.route('/admin')
def admin_dashboard():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute('SELECT username, email FROM users WHERE role = "user"')
    users = cursor.fetchall()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            day TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            location TEXT NOT NULL
        )
    ''')
    cursor.execute('SELECT * FROM courses')
    courses = cursor.fetchall()

    conn.close()
    return render_template('admin_dashboard.html', users=users, courses=courses)


@app.route('/create_subject', methods=['POST'])
def create_subject():
    if 'role' not in session or session['role'] != 'admin':
        session['alert'] = "Unauthorized access"
        return redirect(url_for('login'))

    subject = request.form['subject_name']
    day = request.form['day']
    start_time = request.form['start_time']
    end_time = request.form['end_time']
    location = request.form['location']

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Create table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            day TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            location TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        INSERT INTO courses (subject, day, start_time, end_time, location)
        VALUES (?, ?, ?, ?, ?)
    ''', (subject, day, start_time, end_time, location))
    conn.commit()
    conn.close()

    session['alert'] = "Course added successfully"
    return redirect(url_for('admin_dashboard'))


# Helper functions
def compare_database(email, password):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password))
    user = cursor.fetchone()
    conn.close()
    return user

def insert_user(email, password, username, role='user'):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Create tables if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS timetable (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            subject TEXT NOT NULL,
            day TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            location TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            email TEXT PRIMARY KEY,
            time_format TEXT DEFAULT '24h'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            day TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            location TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            course_id INTEGER NOT NULL,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        )
    ''')

    # Insert user if not exists
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    if cursor.fetchone() is None:
        cursor.execute('INSERT INTO users (email, username, password, role) VALUES (?, ?, ?, ?)', (email, username, password, role))
        cursor.execute('INSERT OR IGNORE INTO settings (email) VALUES (?)', (email,))
        conn.commit()

    conn.close()

if __name__ == '__main__':
    # Insert admin user only if not exists
    insert_user('admin@mmu.edu.my', 'Admin@123!', 'AdminUser', role='admin')
    app.run(debug=True)