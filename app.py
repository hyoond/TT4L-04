from flask import Flask, render_template, request, redirect, url_for, session, make_response
import sqlite3
import os
from werkzeug.utils import secure_filename
from functools import wraps

def nocache(view):
    @wraps(view)
    def no_cache_view(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response
    return no_cache_view

app = Flask(__name__)
app.secret_key = 'supersecretkey123'  # Use a secure key in production

# Upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Helper: File extension check
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
@nocache
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=session['username'])

@app.route('/logout', methods=['POST', 'GET'])
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/upload', methods=['GET', 'POST'])
@nocache
def upload_timetable():
    if 'user_email' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        if 'file' not in request.files:
            return "No file part"
        file = request.files['file']
        if file.filename == '':
            return "No selected file"
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            return f"File uploaded successfully! Saved to: {filepath}"
        else:
            return "Invalid file type. Allowed types: pdf, jpg, jpeg, png."

    return render_template('upload.html')

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