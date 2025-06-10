import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import secrets
import re

DATABASE = 'blog.db'

def secure_database_file():
    """Set secure permissions for the database file."""
    try:
        os.chmod(DATABASE, 0o600)
    except OSError as e:
        print(f"Failed to set database permissions: {e}")

def get_db_connection():
    """Establish a secure database connection with error handling."""
    try:
        conn = sqlite3.connect(DATABASE, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        raise Exception(f"Database connection failed: {e}")

def init_db():
    """Initialize the database with secure schema and stronger default credentials."""
    conn = get_db_connection()
    
    # Enable foreign key constraints for referential integrity
    conn.execute('PRAGMA foreign_keys = ON')
    
    # Create users table with stronger constraints
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL CHECK(length(username) >= 4 AND length(username) <= 50),
            email TEXT UNIQUE NOT NULL CHECK(email LIKE '%_@_%._%'),
            password_hash TEXT NOT NULL CHECK(length(password_hash) >= 8),
            is_admin INTEGER DEFAULT 0 CHECK(is_admin IN (0, 1)),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create posts table with additional constraints
    conn.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL CHECK(length(title) >= 1 AND length(title) <= 200),
            content TEXT NOT NULL CHECK(length(content) >= 1),
            author_id INTEGER NOT NULL,
            image_path TEXT CHECK(length(image_path) <= 255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (author_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # Create comments table with constraints
    conn.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            author_name TEXT NOT NULL CHECK(length(author_name) >= 1 AND length(author_name) <= 50),
            content TEXT NOT NULL CHECK(length(content) >= 1 AND length(content) <= 1000),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE
        )
    ''')

    # Generate secure credentials
    try:
        admin_password = secrets.token_urlsafe(16)
        admin_password_hash = generate_password_hash(admin_password, method='pbkdf2:sha256', salt_length=16)
        conn.execute('''
            INSERT  INTO users (username, email, password_hash, is_admin)
            VALUES (?, ?, ?, ?)
        ''', ('admin', 'admin@blog.ru', admin_password_hash, 1))

        # Save admin credentials securely
        try:
            with open('admin_credentials.txt', 'w', encoding='utf-8') as f:
                os.chmod('admin_credentials.txt', 0o600)
                f.write(f"Admin username: admin\nAdmin password: {admin_password}\n")
        except OSError as e:
            print(f"Failed to save admin credentials: {e}")

        conn.commit()
    except sqlite3.IntegrityError as e:
        print(f"Initialization skipped due to existing data: {e}")
    except sqlite3.Error as e:
        print(f"Database error during initialization: {e}")
    finally:
        conn.close()
        secure_database_file()

def validate_input(input_str, max_length, pattern=None):
    """Validate input to prevent injection and ensure reasonable length."""
    if not input_str or len(input_str.strip()) == 0 or len(input_str) > max_length:
        return False
    if pattern and not re.match(pattern, input_str):
        return False
    dangerous_chars = [';', '--', '/*', '*/', '<', '>', '"', "'", '&']
    if any(char in input_str for char in dangerous_chars):
        return False
    return True

class User:
    def __init__(self, id, username, email, password_hash, is_admin=0):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.is_admin = is_admin

    @staticmethod
    def get_by_id(user_id):
        """Retrieve a user by ID with input validation and error handling."""
        if not isinstance(user_id, int) or user_id < 1:
            return None
        try:
            conn = get_db_connection()
            user_data = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
            conn.close()
            if user_data:
                return User(user_data['id'], user_data['username'], user_data['email'],
                           user_data['password_hash'], user_data['is_admin'])
            return None
        except sqlite3.Error:
            return None

    @staticmethod
    def get_by_username(username):
        """Retrieve a user by username with input validation."""
        if not validate_input(username, 50, r'^[\w]+$'):
            return None
        try:
            conn = get_db_connection()
            user_data = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
            conn.close()
            if user_data:
                return User(user_data['id'], user_data['username'], user_data['email'],
                           user_data['password_hash'], user_data['is_admin'])
            return None
        except sqlite3.Error:
            return None

    @staticmethod
    def create(username, email, password):
        """Create a new user with secure password hashing and input validation."""
        if not validate_input(username, 50, r'^[\w]+$') or not validate_input(email, 100, r'^[\w\.-]+@[\w\.-]+\.\w+$'):
            return None
        if len(password) < 8:
            return None
        try:
            password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, is_admin)
                VALUES (?, ?, ?, ?)
            ''', (username, email, password_hash, 0))
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            return User(user_id, username, email, password_hash, 0)
        except sqlite3.IntegrityError:
            return None
        except sqlite3.Error:
            return None

class Post:
    def __init__(self, id, title, content, author_id, image_path=None, created_at=None):
        self.id = id
        self.title = title
        self.content = content
        self.author_id = author_id
        self.image_path = image_path
        self.created_at = created_at

    @staticmethod
    def get_all():
        """Retrieve all posts with error handling."""
        try:
            conn = get_db_connection()
            posts = conn.execute('''
                SELECT p.*, u.username
                FROM posts p
                JOIN users u ON p.author_id = u.id
                ORDER BY p.created_at DESC
            ''').fetchall()
            conn.close()
            return posts
        except sqlite3.Error:
            return []

    @staticmethod
    def get_by_id(post_id):
        """Retrieve a post by ID with input validation."""
        if not isinstance(post_id, int) or post_id < 1:
            return None
        try:
            conn = get_db_connection()
            post = conn.execute('''
                SELECT p.*, u.username
                FROM posts p
                JOIN users u ON p.author_id = u.id
                WHERE p.id = ?
            ''', (post_id,)).fetchone()
            conn.close()
            return post
        except sqlite3.Error:
            return None

    @staticmethod
    def create(title, content, author_id, image_path=None):
        """Create a new post with input validation."""
        if not validate_input(title, 200) or not validate_input(content, 10000) or not isinstance(author_id, int):
            return None
        if image_path and not validate_input(image_path, 255):
            return None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO posts (title, content, author_id, image_path)
                VALUES (?, ?, ?, ?)
            ''', (title, content, author_id, image_path))
            conn.commit()
            post_id = cursor.lastrowid
            conn.close()
            return post_id
        except sqlite3.Error:
            return None

class Comment:
    @staticmethod
    def get_by_post_id(post_id):
        """Retrieve comments by post ID with input validation."""
        if not isinstance(post_id, int) or post_id < 1:
            return []
        try:
            conn = get_db_connection()
            comments = conn.execute('''
                SELECT * FROM comments
                WHERE post_id = ?
                ORDER BY created_at ASC
            ''', (post_id,)).fetchall()
            conn.close()
            return comments
        except sqlite3.Error:
            return []

    @staticmethod
    def create(post_id, author_name, content):
        """Create a new comment with input validation."""
        if not isinstance(post_id, int) or not validate_input(author_name, 50, r'^[\w\s]+$') or not validate_input(content, 1000):
            return None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO comments (post_id, author_name, content)
                VALUES (?, ?, ?)
            ''', (post_id, author_name, content))
            conn.commit()
            comment_id = cursor.lastrowid
            conn.close()
            return comment_id
        except sqlite3.Error:
            return None
