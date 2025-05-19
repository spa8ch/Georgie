from flask import Flask, render_template, url_for, request, redirect, session, flash, jsonify
import sqlite3
import secrets
import logging

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import uuid

# Setup flask to run
app = Flask(__name__) # Create a Flask application instance
app.secret_key = secrets.token_hex(32)  # Generates a random 32-character key
app.config['UPLOAD_FOLDER'] = 'uploads' # Name of the upload folder
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'} # Uploaded file types
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16 MB limit

logging.basicConfig(level=logging.INFO) # Show errors in the console

# Function to return the database connection object 
def get_db_connection():
    conn = sqlite3.connect('database.db')  #Name of the database
    conn.row_factory = sqlite3.Row # This allows us to access columns by name
    return conn #   Return the connection object

# Function to return true if file extention is in the list - only allows image files
def allowed_file(filename): # Check if the file is allowed
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'} # Set of allowed file extensions
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS # Check if the file extension is in the allowed list


#Index Route
#@app.route('/')  # Home Page

# Register Route
@app.route('/sign_up', methods=['GET', 'POST']) #  Register Page
def register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        surname = request.form['surname']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if not username or not email or not password:
            #flash("All fields are required.", "danger")
            return render_template('sign_up.html')

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        try:
            conn.execute(
                'INSERT INTO Users (first_name, surname, email, username, password) VALUES (?, ?, ?, ?,?)',
                (first_name, surname, email, username, hashed_password)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            #flash("Username or email already exists.", "danger")
            return render_template('sign_up.html')
        finally:
            conn.close()

        #flash("Registration successful. Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('sign_up.html')

'''
# Login Route
@app.route('/login', methods=['GET', 'POST']) # Login Page
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection() # Connect to the database
        query = "SELECT * FROM Users WHERE username = ?" # SQL query to find the user
        user = conn.execute(query, (username,)).fetchone()# Fetch the user from the database
        conn.close()# Close the database connection


        if user and check_password_hash(user['password'], password):# Check if the user exists and the password is correct
            session['user_id'] = user['user_id'] # Store the user ID in the session
            session['username'] = user['username'] # Store the username in the session
        
            flash('Login successful!', 'success') # Show success message
            return redirect(url_for('index'))  # Redirect to the home page
        else:
            flash('Invalid username or password.', 'danger') # Show error message
            return render_template('login.html') # Render the login page with error message

    return render_template('login.html') # Render the login page


'''





def init_db():
    conn = get_db_connection()
    conn.execute('PRAGMA foreign_keys = ON')
    conn.executescript('''
        DROP TABLE IF EXISTS Comments;
        DROP TABLE IF EXISTS Artworks;
        DROP TABLE IF EXISTS Users;
        DROP TABLE IF EXISTS Artists;


        CREATE TABLE Users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            first_name TEXT NOT NULL,
            surname TEXT NOT NULL,                                  
        );

        CREATE TABLE Artworks (
            artwork_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            image_path TEXT,
            pending INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES Users(users_id)
        );

        CREATE TABLE Comments (
            comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            artwork_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            comment TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (artwork_id) REFERENCES Artworks(artwork_id),
            FOREIGN KEY (user_id) REFERENCES Users(user_id)
        );
                       
        CREATE TABLE Likes (
            like_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            artwork_id INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(user_id),
            FOREIGN KEY (artwork_id) REFERENCES Artworks(artwork_id),
            UNIQUE (user_id, artwork_id)
        );
    ''')

    conn.commit()
    conn.close()
    print("Database initialized.")






if __name__ == '__main__':
    try:
        os.makedirs(os.path.join(app.static_folder, app.config['UPLOAD_FOLDER']), exist_ok=True)
    except OSError as e:
        logging.error(f"Could not create upload folder: {e}")

    app.run(host='0.0.0.0')
    init_db()  # Uncomment to reset DB
    app.run(debug=True)