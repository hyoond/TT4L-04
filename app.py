from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a strong secret key in production

# Upload config
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Helper function to check file type
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/signup', methods=['GET'])
def signup_form():
    return render_template('signup.html')

@app.route('/signup', methods=['POST'])
def signup():
    email = request.form['email']
    password = request.form['password']
    insert_user(email, password)
    return f"User {email} added successfully! Please <a href='/login'>login here</a>."

@app.route('/login')
def login_form():
    return render_template('userlogin.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    user = compare_database(email, password)

    if user:
        session['user'] = email
        return redirect(url_for('dashboard'))
    else:
        return "User not found or Incorrect password."

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login_form'))
    return render_template('dashboard.html', user=session['user'])

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

@app.route('/upload', methods=['GET', 'POST'])
def upload_timetable():
    if 'user' not in session:
        return redirect(url_for('login_form'))

    if request.method == 'POST':
        if 'file' not in request.files:
            return "No file part"

        file = request.files['file']

        if file.filename == '':
            return "No selected file"

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

            file.save(filepath)
            return f"File uploaded successfully! Saved to: {filepath}"

    return render_template('upload.html')

# Database helpers
def compare_database(email, password):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT * FROM users WHERE name = ? AND password = ?
    ''', (email, password))
    user = cursor.fetchone()
    conn.close()
    return user

def insert_user(email, password):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
       CREATE TABLE IF NOT EXISTS users (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           name TEXT NOT NULL,
           password TEXT NOT NULL
       )
    ''')
    cursor.execute('''
    INSERT INTO users (name, password) VALUES (?, ?)
    ''', (email, password))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    app.run(debug=True)
