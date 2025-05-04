from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3, os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

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
        session['user_id'] = user[0]           
        session['user_email'] = user[1]  
        return redirect(url_for('dashboard'))
    else:
        flash('Incorrect email or password.')
        return "User not found or Incorrect password."

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

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user_email=session['user_email'])

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))    

if __name__ == '__main__':
    app.run(debug=True)