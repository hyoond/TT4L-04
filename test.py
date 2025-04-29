from flask import Flask, render_template, request, redirect, url_for
import sqlite3

test = Flask(__name__)

@test.route('/')
def signup_form():
    return render_template('signup.html')

@test.route('/signup', methods=['POST'])
def signup():
    email = request.form['email']
    password = request.form['password']

    insert_user(email, password)
    return f"User added successfully! Please <a href='/login'>login here</a>."

@test.route('/login')
def login_form():
    return render_template('login.html')

@test.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    user = compare_database(email, password)

    if user:
        return f"Welcome!"
    else:
        return "User not found or Incorrect password."

def insert_user(email, password):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute('''
       CREATE TABLE IF NOT EXISTS users (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           email TEXT NOT NULL,
           password TEXT NOT NULL
       )
    ''')

    cursor.execute('''
    INSERT INTO users (email, password) VALUES (?, ?)
    ''', (email, password))

    conn.commit()
    conn.close()

def compare_database(email, password):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute('''
    SELECT * FROM users WHERE email = ? AND password = ?
    ''', (email, password))

    user = cursor.fetchone()
    conn.close()
    return user

test.run(debug=True)
