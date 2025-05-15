from flask import Flask, render_template, request, redirect, url_for, session, make_response
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'supersecretkey123'  # Update to a secure secret key

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

        if user[4] == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
          return redirect(url_for('dashboard'))
    else:
        return render_template("login.html", alert = "User not found or incorrect password")

@app.route('/dashboard')
def dashboard():
    alert = session.pop('alert', None)
    if 'username' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT subject, day, start_time, end_time, location FROM timetable WHERE email = ?', (session['email'],))
    timetable_data = cursor.fetchall()
    conn.close()

    return render_template('dashboard.html', username=session['username'], alert=alert, timetable=timetable_data)

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
         session['alert'] = "Time table added successfully"
         return redirect(url_for('dashboard'))

    return render_template('timetable.html')

def compare_database(email, password):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password))
    user = cursor.fetchone()
    conn.close()
    return user

def ensure_users_table_has_role_column():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e).lower():
            raise
    conn.commit()
    conn.close()

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
            day TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            location TEXT NOT NULL
        )
    ''')

    cursor.execute('INSERT INTO users (email, username, password, role) VALUES (?, ?, ?, ?)', (email, username, password, role))
    conn.commit()
    conn.close()

if __name__ == '__main__':
     ensure_users_table_has_role_column()
     insert_user('admin@mmu.edu.my', 'Admin@123!', 'AdminUser', role='admin')
     app.run(debug=True)