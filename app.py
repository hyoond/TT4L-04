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
        session['alert'] = "Login successfully"
        return redirect(url_for('dashboard'))
    else:
        return render_template("login.html", alert = "User not found or incorrect password")

@app.route('/dashboard')
def dashboard():
    alert = session.pop('alert', None)
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=session['username'], alert=alert)

@app.route('/logout', methods=['POST', 'GET'])
def logout():
    session.clear()
    session['alert'] = "Logout successfully"
    return redirect(url_for('home'))

@app.route('/upload', methods=['GET', 'POST'])
def upload_timetable():
    if 'username' not in session:
        session['alert'] = "Please login first"
        return redirect(url_for('login'))

    alert = None

    if request.method == 'POST':
        if 'file' not in request.files:
            alert = "No file part in request"
        else:
            file = request.files['file']
            if file.filename == '':
                alert = "No selected file"
            elif file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.save(filepath)
                alert = f"File uploaded successfully! Saved to: {filepath}"
            else:
                alert = "File type not allowed."

    return render_template('upload.html', alert=alert)



def compare_database(email, password):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password))
    user = cursor.fetchone()
    conn.close()
    return user

def insert_user(email, password, username):
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

if __name__ == '__main__':
    app.run(debug=True)
