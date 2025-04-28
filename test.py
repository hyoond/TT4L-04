from flask import Flask, render_template, request, redirect, url_for
import sqlite3

test = Flask(__name__)

@test.route('/')
def signup_form():
    return render_template('usersignup.html')

@test.route('/signup', methods=['POST'])
def signup():
    username = request.form['username']
    password = request.form['password']

    insert_user(username, password)
    return f"User {username} added successfully! Please <a href='/login'>login here</a>."

@test.route('/login')
def login_form():
    return render_template('userlogin.html')

@test.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    user = compare_database(username, password)

    if user:
        return f"Welcome, {username}!"
    else:
        return "User not found or Incorrect password."

def compare_database(username, password):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute('''
    SELECT * FROM users WHERE name = ? AND password = ?
    ''', (username, password))

    user = cursor.fetchone()
    conn.close()
    return user

def insert_user(username, password):
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
    ''', (username, password))

    conn.commit()
    conn.close()

test.run(debug=True)
