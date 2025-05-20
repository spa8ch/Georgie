from flask import Flask, render_template, url_for, request, redirect, session, flash, jsonify
import sqlite3
import secrets
import logging

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# Setup flask to run
app = Flask(__name__) # Create a Flask application instance
app.secret_key = secrets.token_hex(32)  # Generates a random 32-character key
app.config['UPLOAD_FOLDER'] = 'uploads' # Name of the upload folder
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'} # Uploaded file types
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16 MB limit

logging.basicConfig(level=logging.INFO) # Show errors in the console

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Function to return the database connection object 
def get_db_connection():
    print("Attempting to connect to the database...")  # Add this line
    conn = sqlite3.connect('database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row # This allows us to access columns by name
    return conn


# Function to return true if file extention is in the list - only allows image files
def allowed_file(filename): # Check if the file is allowed
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'} # Set of allowed file extensions
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS # Check if the file extension is in the allowed list

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# Index Route
@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# Register Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('sign_up.html')


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():

    return render_template('login.html')

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# Gallery Route
@app.route('/gallery', methods=['GET', 'POST'])
def gallery():
    return render_template('gallery.html')

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# Upload Route
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    print ("hello")
    return render_template('submit.html')

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# View ROUTE
@app.route('/view')
def view():
    return redirect(url_for('view'))

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Logout Route
@app.route('/logout')
def logout():

    return redirect(url_for('index'))





#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

if __name__ == '__main__':
    try:
        os.makedirs(os.path.join(app.static_folder, app.config['UPLOAD_FOLDER']), exist_ok=True)
    except OSError as e:
        logging.error(f"Could not create upload folder: {e}")

    init_db()  # Uncomment to reset DB
    #app.run(host='0.0.0.0')
    app.run(debug=True)