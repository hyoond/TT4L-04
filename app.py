from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey123'  # Use a secure key in production

# Helper: Password validation
def valid_password(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long.<a href='/signup'>Enter Again</a>"
    if not any(char.isdigit() for char in password):
        return False, "Password must include at least one number.<a href='/signup'>Enter Again</a>"
    if not any(char in "!@#$%^&*()_-+=<>:;?/,.{[]}" for char in password):
        return False, "Password must include at least one symbol.<a href='/signup'>Enter Again</a>"
    return True, ""

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/signup', methods=['GET'])
def signup_form():
    return render_template('signup.html')

@app.route('/signup', methods=['POST'])
def signup():
    email = request.form['email']
    username = request.form['username']
    password = request.form['password']

    if not email.endswith("mmu.edu.my"):
        return "Only MMU email addresses are allowed.<a href='/signup'>Enter Again</a>"

    is_valid, message = valid_password(password)
    if not is_valid:
        return message

    insert_user(email, username, password)
    return f"User {username} added successfully! Please <a href='/login'>login here</a>."

@app.route('/login', methods=['GET'])
def login_form():
    return render_template('userlogin.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    user = compare_database(email, password)

    if user:
        session['username'] = user[2]  # username from DB
        session['user_email'] = user[1]
        return redirect(url_for('dashboard'))
    else:
        return "User not found or incorrect password."

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT subject, day, start_time, end_time, location FROM timetable WHERE user_email = ?', (session['user_email'],))
    timetable_data = cursor.fetchall()
    conn.close()

    return render_template('dashboard.html', username=session['username'], timetable=timetable_data)

@app.route('/logout', methods=['POST', 'GET'])
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/timetable', methods=['GET', 'POST'])
def timetable():
    if 'user_email' not in session:
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
            INSERT INTO timetable (user_email, subject, day, start_time, end_time, location)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session['user_email'], subject, day, start_time, end_time, location))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))

    return render_template('timetable.html')

# Database helpers
def insert_user(email, username, password):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS timetable (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            subject TEXT NOT NULL,
            day TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            location TEXT NOT NULL
        )
    ''')
    cursor.execute('INSERT INTO users (email, username, password) VALUES (?, ?, ?)', (email, username, password))
    conn.commit()
    conn.close()

def compare_database(email, password):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password))
    user = cursor.fetchone()
    conn.close()
    return user

if __name__ == '__main__':
    app.run(debug=True)
    