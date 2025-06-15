from flask import Flask, render_template, request, redirect, url_for, session, make_response
import sqlite3
import os
import calendar
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

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
        return render_template ("signup.html", alert="Only MMU email addresses are allowed.")

    is_valid, alert = valid_password(password)
    if not is_valid:
        return render_template ("signup.html", alert = alert)

    insert_user(email, password,username)
    alert = f"User {username} added successfully!"
    return render_template("login.html", alert = alert)

@app.route('/login')
def login_form():
    alert = session.pop('alert', None)
    return render_template('login.html', alert = alert)

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
        return redirect(url_for('dashboard'))
    else:
        return render_template("login.html", alert = "User not found or incorrect password")

@app.route('/dashboard')
def dashboard():
    alert = session.pop('alert', None)
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if 'role' in session and session['role'] == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT subject, date, start_time, end_time, location, day FROM timetable WHERE email = ?', (session['email'],))
    timetable_data = cursor.fetchall()
    cursor.execute('SELECT time_format FROM settings WHERE email = ?', (session['email'],))
    settings_data = cursor.fetchone()

    cursor.execute('''
        SELECT * FROM courses WHERE id NOT IN (
            SELECT c.id FROM courses c
            JOIN timetable t ON 
                c.subject = t.subject AND 
                c.date = t.date AND
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
        subject, date, start_str, end_str, location, day = entry

        start_dt = datetime.strptime(start_str, '%H:%M')
        end_dt = datetime.strptime(end_str, '%H:%M')

        if time_format == '12h':
            formatted_start = start_dt.strftime('%I:%M %p')
            formatted_end = end_dt.strftime('%I:%M %p')
        else:
            formatted_start = start_dt.strftime('%H:%M')
            formatted_end = end_dt.strftime('%H:%M')

        formatted_timetable.append((subject, date, day, formatted_start, formatted_end, location))


    return render_template('dashboard.html',username=session['username'],alert=alert,timetable=formatted_timetable,settings=settings_data, available_courses=available_courses)

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

    
    cursor.execute('SELECT * FROM enrollments WHERE user_email = ? AND course_id = ?', (email, course_id))
    already_enrolled = cursor.fetchone()

    if already_enrolled:
        session['alert'] = "You are already enrolled in this course."
        conn.close()
        return redirect(url_for('dashboard'))

    
    cursor.execute('SELECT id, subject, start_time, end_time, location, date, day FROM courses WHERE id = ?', (course_id,))
    new_course = cursor.fetchone()

    if not new_course:
        session['alert'] = "Course not found!"
        conn.close()
        return redirect(url_for('dashboard'))

    new_course_id, new_subject, new_start_time, new_end_time, new_location, new_date, new_day = new_course

    
    cursor.execute('''
        SELECT c.subject, c.start_time, c.end_time, c.date, c.day
        FROM courses c
        JOIN enrollments e ON c.id = e.course_id
        WHERE e.user_email = ?
    ''', (email,))
    enrolled_courses = cursor.fetchall()

    new_start = datetime.strptime(new_start_time, '%H:%M')
    new_end = datetime.strptime(new_end_time, '%H:%M')
    new_date_only = new_date.split(' ')[0]

    if enrolled_courses:  
        for course in enrolled_courses:
            subject, start_time, end_time, exist_date, day = course
            exist_start = datetime.strptime(start_time, '%H:%M')
            exist_end = datetime.strptime(end_time, '%H:%M')
            exist_date_only = exist_date.split(' ')[0]

            if new_date_only == exist_date_only and (new_start < exist_end) and (new_end > exist_start):
                session['alert'] = f"Clash detected with your enrolled course '{subject}' on {exist_date_only}!"
                conn.close()
                return redirect(url_for('dashboard'))

    cursor.execute('INSERT INTO enrollments (user_email, course_id) VALUES (?, ?)', (email, course_id))
    
    
    cursor.execute('''
        INSERT INTO timetable (email, subject, date, start_time, end_time, location, day)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (email, new_subject, new_date, new_start_time, new_end_time, new_location, new_day))

    conn.commit()
    conn.close()

    session['alert'] = "Enrolled in course successfully!"
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

    alert = None

    if request.method == 'POST':
         subject = request.form['subject']
         date = request.form['date']
         start_time = request.form['start_time']
         end_time = request.form['end_time']
         location = request.form['location']

         date_obj = datetime.strptime(date, '%Y-%m-%d')
         day_of_week = date_obj.strftime('%A')

         conn = sqlite3.connect('database.db')
         cursor = conn.cursor()
         cursor.execute('''
             INSERT INTO timetable (email, subject, date, day, start_time, end_time, location)
             VALUES (?, ?, ?, ?, ?, ?, ?)
         ''', (session['email'], subject, date, day_of_week, start_time, end_time, location))
         conn.commit()
         conn.close()
         session['alert'] = "Time table added successfully"
         return redirect(url_for('dashboard'))

    return render_template('timetable.html')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'email' not in session:
        session['alert'] = "Please login first"
        return redirect(url_for('login'))

    email = session['email']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
            SELECT username FROM users
             WHERE email = ?
         ''', (email,))
    result = cursor.fetchone()
    username = result[0]

    if request.method == 'POST':
        new_username = request.form.get('username')
        cursor.execute(''' 
            UPDATE users SET username = ?
            WHERE email = ?
            ''', (new_username, email))
        conn.commit()
        time_format = request.form.get('time_format')
        cursor.execute('''
            UPDATE settings SET time_format = ?
            WHERE email = ?
        ''', (time_format, email))
        conn.commit()
        session['alert'] = "Settings updated successfully"
        return redirect(url_for('dashboard'))

    cursor.execute('SELECT time_format FROM settings WHERE email = ?', (email,))
    settings_data = cursor.fetchone()
    conn.close()

    return render_template('settings.html', settings=settings_data, username = username)


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
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            location TEXT NOT NULL,
            date TEXT,
            day TEXT NOT NULL
        )
    ''')
    cursor.execute('SELECT * FROM courses')
    courses = cursor.fetchall()
    conn.close()

    alert = session.pop('alert', None)  
    return render_template('admin_dashboard.html', users=users, courses=courses, alert=alert)



@app.route('/create_subject', methods=['POST'])
def create_subject():
    if 'role' not in session or session['role'] != 'admin':
        session['alert'] = "Unauthorized access"
        return redirect(url_for('login'))

    subject = request.form['subject_name']
    start_time = request.form['start_time']
    end_time = request.form['end_time']
    location = request.form['location']
    start_date = request.form['start_date']
    duration = request.form['duration']
    date = f"{start_date} ({duration})"

    date_obj = datetime.strptime(start_date, '%Y-%m-%d')
    day_of_week = date_obj.strftime('%A')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()


    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            location TEXT NOT NULL,
            date TEXT,
            day TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        SELECT subject, start_time, end_time, date FROM courses
        WHERE location = ? 
    ''', (location,))

    existing_courses = cursor.fetchall()

    new_start = datetime.strptime(start_time, '%H:%M')
    new_end = datetime.strptime(end_time, '%H:%M')

    for existing in existing_courses:
        exist_subject, exist_start_time, exist_end_time, exist_date = existing
        exist_date_only = exist_date.split(' ')[0]  

        if exist_date_only == start_date:  
            exist_start = datetime.strptime(exist_start_time, '%H:%M')
            exist_end = datetime.strptime(exist_end_time, '%H:%M')

            # Check overlap
            if (new_start < exist_end) and (new_end > exist_start):
                conn.close()
                session['alert'] = f"Time conflict with existing subject '{exist_subject}' at this location!"
                return redirect(url_for('admin_dashboard'))

  
    cursor.execute('''
        INSERT INTO courses (subject, start_time, end_time, location, date, day)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (subject, start_time, end_time, location, date, day_of_week))
    conn.commit()
    conn.close()

    session['alert'] = "Course added successfully"
    return redirect(url_for('admin_dashboard'))

@app.route('/deletion', methods=['POST'])
def deletion():
    user_email = request.form.get('user_email')
    course_id = request.form.get('course_id')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if user_email:
        cursor.execute('''
                       DELETE FROM users
                       WHERE email = ?
                       ''',(user_email,))
        conn.commit()
        session['alert'] = "Deleted successfully."
        
    if course_id:
        cursor.execute('''
                       DELETE FROM courses
                       WHERE id = ?
                       ''', (course_id,))
        conn.commit()
        session['alert'] = "Deleted successfully."
    
    return redirect(url_for('admin_dashboard'))

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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
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
            date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            location TEXT NOT NULL,
            day TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            email TEXT PRIMARY KEY,
            time_format TEXT DEFAULT '24h'
        )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS enrollments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        course_id INTEGER NOT NULL,
        FOREIGN KEY (user_email) REFERENCES users(email),
        FOREIGN KEY (course_id) REFERENCES courses(id)
    )
''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            location TEXT NOT NULL,
            date TEXT,
            day TEXT NOT NULL
        )
    ''')


    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    if cursor.fetchone() is None:
        cursor.execute('INSERT INTO users (email, username, password, role) VALUES (?, ?, ?, ?)', (email, username, password, role))
        cursor.execute('INSERT OR IGNORE INTO settings (email) VALUES (?)', (email,))
        conn.commit()
    conn.close()

@app.route('/calander_index', methods=['GET', 'POST'])
def calander_index():
    now = datetime.now()
    year = now.year
    month = now.month
    today = [year,month]

    if request.method == 'POST':
        action = request.form.get('action')
        year = int(request.form.get('year'))
        month = int(request.form.get('month'))

        if action == 'prev_month':
            month -= 1
            if month < 1:
                month = 12
                year -= 1
        elif action == 'next_month':
            month += 1
            if month > 12:
                month = 1
                year += 1
        elif action == 'prev_year':
            year -= 1
        elif action == 'next_year':
            year += 1

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT subject, date, start_time, end_time, location FROM timetable')
    events = cursor.fetchall()
    conn.close()

    event_dict = {}
    for subject, date_str, start_time, end_time, location in events:
        if '(' in date_str and ')' in date_str:
            base_date_str = date_str.split('(')[0].strip()
            duration = int(date_str.split('(')[1].split(')')[0].strip())
        else:
            base_date_str = date_str
            duration = 1  # Default: only once

        try:
            base_date = datetime.strptime(base_date_str, '%Y-%m-%d')
        except ValueError:
            continue
        for i in range(duration):
            event_date = base_date + timedelta(weeks=i)
            if event_date.year == year and event_date.month == month:
                day = event_date.day
                if day not in event_dict:
                    event_dict[day] = []
                event_dict[day].append({
                    'subject': subject,
                    'start': start_time,
                    'end': end_time,
                    'location': location
                })

    cal = calendar.HTMLCalendar(firstweekday=6)
    month_days = cal.itermonthdays(year, month)

    calendar_html = '<table border="0" cellpadding="0" cellspacing="0" class="calendar">\n'
    calendar_html += f'<tr><th colspan="7">{calendar.month_name[month]} {year}</th></tr>\n'
    calendar_html += '<tr>' + ''.join(f'<th>{day}</th>' for day in ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']) + '</tr>\n<tr>'

    week_day = 0
    for day in month_days:
        if week_day == 7:
            calendar_html += '</tr>\n<tr>'
            week_day = 0

        if day == 0:
            calendar_html += '<td></td>'
        else:
            if day in event_dict:
                events_html = ""
                for e in event_dict[day]:
                    events_html += (
                        f'<div style="font-size: 0.85em;">'
                        f'<a>{e["subject"]}</a><br>'
                        f'{e["start"]} - {e["end"]}<br>'
                        f'<a>{e["location"]}</a>'
                        f'</div>'
                    )
                calendar_html += f'<td class="event">{day}<br>{events_html}</td>'
            else:
                calendar_html += f'<td>{day}</td>'

        week_day += 1

    calendar_html += '</tr>\n</table>'

    return render_template('calendar.html', calendar=calendar_html, year=year, month=month, today=today)


if __name__ == '__main__':
    insert_user('admin@mmu.edu.my', 'Admin@123!', 'AdminUser', role='admin')
    app.run(debug=True)