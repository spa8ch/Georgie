from flask import Flask, render_template, url_for, request, redirect, session, flash, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import uuid
import logging

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

logging.basicConfig(level=logging.INFO)

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('PRAGMA foreign_keys = ON')
    conn.executescript('''
        DROP TABLE IF EXISTS Comments;
        DROP TABLE IF EXISTS Artworks;
        DROP TABLE IF EXISTS Users;
        DROP TABLE IF EXISTS Artists;

        CREATE TABLE Artists (
            artist_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        );

        CREATE TABLE Users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            user_type TEXT NOT NULL CHECK (user_type IN ('artist', 'enthusiast', 'admin'))
        );

        CREATE TABLE Artworks (
            artwork_id INTEGER PRIMARY KEY AUTOINCREMENT,
            artist_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            image_path TEXT,
            pending INTEGER DEFAULT 1,
            FOREIGN KEY (artist_id) REFERENCES Artists(artist_id)
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

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


#Index Route
@app.route('/')  # Home Page
def index():
    conn = get_db_connection()
    artworks = conn.execute('''
        SELECT a.*, u.username AS artist_name
        FROM Artworks a
        JOIN Users u ON a.artist_id = u.user_id
        WHERE a.pending = 0
        ORDER BY RANDOM()
        LIMIT 3
    ''').fetchall()
    conn.close()

    return render_template('index.html', artworks=artworks)

# Register Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        user_type = request.form['user_type']

        if not username or not email or not password or not user_type:
            flash("All fields are required.", "danger")
            return render_template('register.html')

        if user_type not in ('artist', 'enthusiast'):
            flash("Invalid user type. Choose artist or enthusiast.", "danger")
            return render_template('register.html')

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        try:
            conn.execute(
                'INSERT INTO Users (username, email, password, user_type) VALUES (?, ?, ?, ?)',
                (username, email, hashed_password, user_type)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            flash("Username or email already exists.", "danger")
            return render_template('register.html')
        finally:
            conn.close()

        flash("Registration successful. Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')



# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM Users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['user_type'] = user['user_type']

            flash('Login successful!', 'success')
            return redirect(url_for('index'))  # Corrected redirect
        else:
            flash('Invalid username or password.', 'danger')
            return render_template('login.html')

    return render_template('login.html')


# Gallery Route
@app.route('/gallery')
def gallery():
    conn = get_db_connection()
    artworks = conn.execute('''
        SELECT a.*, u.username AS artist_name
        FROM Artworks a
        JOIN Users u ON a.artist_id = u.user_id
        WHERE a.pending = 0
        ORDER BY a.submission_date DESC
    ''').fetchall()

    liked_artworks = set()
    if 'user_id' in session:
        liked_artworks_data = conn.execute(
            'SELECT artwork_id FROM Likes WHERE user_id = ?', (session['user_id'],)
        ).fetchall()
        liked_artworks = {like['artwork_id'] for like in liked_artworks_data}

    artworks_with_likes = []
    for artwork in artworks:
        like_count = conn.execute(
            'SELECT COUNT(*) FROM Likes WHERE artwork_id = ?', (artwork['artwork_id'],)
        ).fetchone()[0]
        is_liked = artwork['artwork_id'] in liked_artworks
        artwork_dict = dict(artwork)  # Convert Row object to dictionary
        artwork_dict['like_count'] = like_count
        artwork_dict['is_liked'] = is_liked
        artworks_with_likes.append(artwork_dict)

    conn.close()
    return render_template('gallery.html', artworks=artworks_with_likes)

# Logout Route
@app.route('/logout')
def logout():
    session.clear() # Clear the sessions that hold user name, user type
    flash("You have been logged out.", "success")
    
    return redirect(url_for('index')) # Redirect back to the index route




#Upload Route
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session:
        flash("You must be logged in to upload artwork.", "warning")
        return redirect(url_for('login'))

    if session.get('user_type') not in ('artist'):
        flash("Only artists can upload artwork.", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        image = request.files['image']
        artist_id = session['user_id']

        if image:
            if image.filename == '':
                flash('No file selected.', 'danger')
                return redirect(request.url)

            if allowed_file(image.filename):
                try:
                    original_filename = image.filename
                    filename = secure_filename(image.filename)
                    if not filename:
                        flash('Invalid filename.', 'danger')
                        return render_template('upload.html')

                    filename = filename.replace('\\', '_').replace('%5C', '_')
                    filename = filename.replace(' ', '_').replace('%20', '_')
                    filename = ''.join(c for c in filename if c.isalnum() or c in '._-')

                    file_extension = filename.rsplit('.', 1)[1].lower()
                    unique_filename = str(uuid.uuid4()) + '.' + file_extension
                    filename = unique_filename.replace(' ', '_')
                    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename).replace('\\', '/')
                    image.save(os.path.join(app.static_folder, image_path))

                    conn = get_db_connection()
                    conn.execute('''
                        INSERT INTO Artworks (artist_id, title, description, image_path, pending)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (artist_id, title, description, image_path, 1))
                    conn.commit()
                    conn.close()

                    logging.info(f"File uploaded: Original='{original_filename}', Sanitized='{filename}', Unique='{unique_filename}', Saved to='{image_path}'")
                    flash("Artwork uploaded and pending approval.", "success")
                    return redirect(url_for('gallery'))
                except Exception as e:
                    logging.error(f"Error during file upload: {e}")
                    flash("An error occurred during upload. Please try again.", "danger")
                    return render_template('upload.html')
            else:
                flash('Invalid file type', 'danger')
                return render_template('upload.html')
        else:
            flash('No file uploaded', 'danger')
            return render_template('upload.html')

    return render_template('upload.html')


# Admin Approve Route
@app.route('/admin/approve', methods=['GET', 'POST'])
def admin_approve():
    if 'user_type' not in session or session['user_type'] != 'admin':
        flash("You must be an admin to access this page.", "danger")
        return redirect(url_for('index')) # Return use to the index page

    conn = get_db_connection() # Get database connection

    if request.method == 'POST':  # If a POST request
        artwork_id = request.form['artwork_id']
        action = request.form['action']

        if action == 'approve':
            conn.execute('UPDATE Artworks SET pending = 0 WHERE artwork_id = ?', (artwork_id,))
            flash("Artwork approved!", "success")
        elif action == 'reject': # Deletes the artwork from the database
            conn.execute('DELETE FROM Artworks WHERE artwork_id = ?', (artwork_id,))
            flash("Artwork rejected and removed.", "warning")

        conn.commit()
        return redirect(url_for('admin_approve'))

    artworks = conn.execute('SELECT * FROM Artworks WHERE pending = 1').fetchall()
    conn.close()
    return render_template('admin_approve.html', artworks=artworks)


# Artwork Comment Route
@app.route('/comment/<int:artwork_id>', methods=['POST'])
def post_comment(artwork_id):
    if 'user_id' not in session:
        flash("You must be logged in to comment.", "warning")
        return redirect(url_for('login'))

    comment_text = request.form['comment']
    user_id = session['user_id']

    conn = get_db_connection()
    conn.execute('INSERT INTO Comments (artwork_id, user_id, comment) VALUES (?, ?, ?)',
                 (artwork_id, user_id, comment_text))
    conn.commit()
    conn.close()

    flash("Comment posted!", "success")
    return redirect(url_for('view_artwork', artwork_id=artwork_id))

# Artwork Like Route
@app.route('/like/<int:artwork_id>', methods=['POST'])
def like_artwork(artwork_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'You must be logged in to like artwork.'}), 401

    user_id = session['user_id']
    conn = get_db_connection()
    liked = False  # Track if the action was a like or unlike

    try:
        existing_like = conn.execute(
            'SELECT * FROM Likes WHERE user_id = ? AND artwork_id = ?',
            (user_id, artwork_id)
        ).fetchone()

        if existing_like:
            conn.execute(
                'DELETE FROM Likes WHERE user_id = ? AND artwork_id = ?',
                (user_id, artwork_id)
            )
            conn.commit()
            liked = False
        else:
            conn.execute(
                'INSERT INTO Likes (user_id, artwork_id) VALUES (?, ?)',
                (user_id, artwork_id)
            )
            conn.commit()
            liked = True

        like_count = conn.execute(
            'SELECT COUNT(*) FROM Likes WHERE artwork_id = ?', (artwork_id,)
        ).fetchone()[0]

        return jsonify({'success': True, 'like_count': like_count, 'is_liked': liked})

    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'error': 'You have already liked this artwork.'}), 400
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({'success': False, 'error': f'Database error: {e}'}), 500
    finally:
        conn.close()

# Artwork Int Route
@app.route('/artwork/<int:artwork_id>')
def view_artwork(artwork_id):
    conn = get_db_connection()
    artwork = conn.execute('SELECT * FROM Artworks WHERE artwork_id = ?', (artwork_id,)).fetchone()

    # This is the crucial part for fetching the like count:
    like_count = conn.execute(
        'SELECT COUNT(*) FROM Likes WHERE artwork_id = ?', (artwork_id,)
    ).fetchone()[0]

    user_liked = False
    if 'user_id' in session:
        user_liked = conn.execute(
            'SELECT 1 FROM Likes WHERE user_id = ? AND artwork_id = ?',
            (session['user_id'], artwork_id)
        ).fetchone() is not None

    comments = conn.execute('''
        SELECT c.comment, c.timestamp, u.username
        FROM Comments c
        JOIN Users u ON c.user_id = u.user_id
        WHERE c.artwork_id = ?
        ORDER BY c.timestamp DESC
    ''', (artwork_id,)).fetchall()
    conn.close()

    # The like_count variable needs to be passed to the template:
    return render_template(
        'view_artwork.html',
        artwork=artwork,
        comments=comments,
        like_count=like_count,  # Make sure this is included
        user_liked=user_liked
    )


# My Upload Route
@app.route('/my_uploads')
def my_uploads():
    if 'user_id' not in session or session.get('user_type') not in ('artist', 'admin'):
        flash("You must be logged in as an artist or admin to view this page.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    artworks = conn.execute('''
        SELECT * FROM Artworks
        WHERE artist_id = ?
        ORDER BY submission_date DESC
    ''', (session['user_id'],)).fetchall()
    conn.close()

    return render_template('my_uploads.html', artworks=artworks)



# Add artist detail route
@app.route('/artist_detail/<int:artist_id>')
def artist_detail(artist_id):
    conn = get_db_connection()
    artist = conn.execute('SELECT * FROM Artists WHERE artist_id = ?', (artist_id,)).fetchone()
    artworks = conn.execute('SELECT * FROM Artworks WHERE artist_id = ?', (artist_id,)).fetchall()
    conn.close()
    return render_template('artist_detail.html', artist=artist, artworks=artworks)


# Add feedback route
@app.route('/feedback/<int:artwork_id>', methods=['GET', 'POST'])
def feedback(artwork_id):
    if request.method == 'POST':
        user_id = request.form['user_id']
        comment = request.form['comment']
        conn = get_db_connection()
        conn.execute('INSERT INTO Comments (artwork_id, user_id, comment) VALUES (?, ?, ?)',
                     (artwork_id, user_id, comment))
        conn.commit()
        conn.close()
        return redirect(url_for('artist_detail', artist_id=artwork_id))  # Redirect back to artist detail
    return render_template('give_feedback.html')



if __name__ == '__main__':
    try:
        os.makedirs(os.path.join(app.static_folder, app.config['UPLOAD_FOLDER']), exist_ok=True)
    except OSError as e:
        logging.error(f"Could not create upload folder: {e}")

    app.run(host='0.0.0.0')
    #init_db()  # Uncomment to reset DB
    app.run(debug=True)