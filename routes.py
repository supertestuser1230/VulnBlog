import os
import sqlite3
import re
from flask import render_template, request, redirect, url_for, session, flash, send_from_directory, abort
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect
from app import app
from models import get_db_connection, User, Post, Comment

# Включение защиты CSRF
csrf = CSRFProtect(app)

# Настройка загрузки файлов
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
UPLOAD_FOLDER = app.config['UPLOAD_FOLDER']
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB limit
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

def allowed_file(filename):
    """Проверка допустимого расширения файла."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_input(input_str, max_length, pattern=None):
    """Валидация входных данных для предотвращения инъекций."""
    if not input_str or len(input_str) > max_length or len(input_str.strip()) == 0:
        return False
    if pattern and not re.match(pattern, input_str):
        return False
    if any(char in input_str for char in [';', '--', '/*', '*/']):
        return False
    return True

@app.route('/')
def index():
    """Главная страница с отображением всех постов."""
    try:
        posts = Post.get_all()
        return render_template('index.html', posts=posts)
    except sqlite3.Error:
        flash('Ошибка загрузки постов.', 'error')
        return render_template('index.html', posts=[])

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Вход в систему с безопасной проверкой учетных данных."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # Валидация входных данных
        if not validate_input(username, 50, r'^[\w]+$'):
            flash('Недопустимое имя пользователя!', 'error')
            return render_template('login.html')

        try:
            user = User.get_by_username(username)
            if user and check_password_hash(user.password_hash, password):
                session.permanent = True  # Сессия сохраняется
                session['user_id'] = user.id
                session['username'] = user.username
                session['is_admin'] = user.is_admin
                flash('Вход выполнен успешно!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Неверные учетные данные!', 'error')
        except sqlite3.Error:
            flash('Ошибка базы данных.', 'error')
        
        return render_template('login.html')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Регистрация нового пользователя с усиленной валидацией."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        # Валидация входных данных
        if not validate_input(username, 50, r'^[\w]+$'):
            flash('Недопустимое имя пользователя!', 'error')
            return render_template('register.html')
        if not validate_input(email, 100, r'^[\w\.-]+@[\w\.-]+\.\w+$'):
            flash('Недопустимый email!', 'error')
            return render_template('register.html')
        if len(password) < 8:
            flash('Пароль должен содержать не менее 8 символов!', 'error')
            return render_template('register.html')

        user = User.create(username, email, password)
        if user:
            flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Пользователь с таким именем или email уже существует!', 'error')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    """Выход из системы с очисткой сессии."""
    session.clear()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))

@app.route('/post/<int:post_id>')
def view_post(post_id):
    """Просмотр поста и связанных комментариев."""
    if not isinstance(post_id, int) or post_id < 1:
        flash('Недопустимый идентификатор поста!', 'error')
        return redirect(url_for('index'))

    try:
        post = Post.get_by_id(post_id)
        if not post:
            flash('Пост не найден!', 'error')
            return redirect(url_for('index'))
        
        comments = Comment.get_by_post_id(post_id)
        return render_template('post.html', post=post, comments=comments)
    except sqlite3.Error:
        flash('Ошибка загрузки поста.', 'error')
        return redirect(url_for('index'))

@app.route('/post/<int:post_id>/comment', methods=['POST'])
@csrf.exempt  # В реальном приложении включите CSRF в шаблоне
def add_comment(post_id):
    """Добавление комментария к посту."""
    if not isinstance(post_id, int) or post_id < 1:
        flash('Недопустимый идентификатор поста!', 'error')
        return redirect(url_for('index'))

    author_name = request.form.get('author_name', '').strip()
    content = request.form.get('content', '').strip()

    if not validate_input(author_name, 50, r'^[\w\s]+$'):
        flash('Недопустимое имя автора!', 'error')
        return redirect(url_for('view_post', post_id=post_id))
    if not validate_input(content, 1000):
        flash('Недопустимый комментарий!', 'error')
        return redirect(url_for('view_post', post_id=post_id))

    comment_id = Comment.create(post_id, author_name, content)
    if comment_id:
        flash('Комментарий добавлен!', 'success')
    else:
        flash('Ошибка добавления комментария.', 'error')
    
    return redirect(url_for('view_post', post_id=post_id))

@app.route('/create_post', methods=['GET', 'POST'])
def create_post():
    """Создание нового поста с безопасной загрузкой файлов."""
    if 'user_id' not in session:
        flash('Необходимо войти в систему для создания постов!', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()

        if not validate_input(title, 200):
            flash('Недопустимый заголовок!', 'error')
            return render_template('create_post.html')
        if not validate_input(content, 10000):
            flash('Недопустимое содержимое!', 'error')
            return render_template('create_post.html')

        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"{secrets.token_hex(8)}_{filename}"  # Уникальное имя файла
                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                try:
                    file.save(file_path)
                    image_path = unique_filename
                except Exception:
                    flash('Ошибка загрузки изображения.', 'error')
                    return render_template('create_post.html')
            elif file.filename:
                flash('Недопустимый формат изображения!', 'error')
                return render_template('create_post.html')

        post_id = Post.create(title, content, session['user_id'], image_path)
        if post_id:
            flash('Пост создан успешно!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Ошибка создания поста.', 'error')

    return render_template('create_post.html')

@app.route('/search')
def search():
    """Поиск постов с безопасной обработкой запросов."""
    query = request.args.get('q', '').strip()
    posts = []

    if query and validate_input(query, 100):
        try:
            conn = get_db_connection()
            posts = conn.execute('''
                SELECT p.*, u.username
                FROM posts p
                JOIN users u ON p.author_id = u.id
                WHERE p.title LIKE ? OR p.content LIKE ?
                ORDER BY p.created_at DESC
            ''', (f'%{query}%', f'%{query}%')).fetchall()
            conn.close()
        except sqlite3.Error:
            flash('Ошибка поиска.', 'error')

    return render_template('search.html', posts=posts, query=query)

@app.route('/admin')
def admin():
    """Панель администратора с проверкой доступа."""
    if 'user_id' not in session:
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('login'))
    if not session.get('is_admin'):
        flash('Недостаточно прав доступа!', 'error')
        return redirect(url_for('index'))

    try:
        conn = get_db_connection()
        users = conn.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
        posts = conn.execute('SELECT * FROM posts ORDER BY created_at DESC').fetchall()
        comments = conn.execute('SELECT * FROM comments ORDER BY created_at DESC').fetchall()
        conn.close()
        return render_template('admin.html', users=users, posts=posts, comments=comments)
    except sqlite3.Error:
        flash('Ошибка загрузки данных.', 'error')
        return redirect(url_for('index'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Безопасная отдача загруженных файлов."""
    if not validate_input(filename, 255):
        abort(403)
    try:
        return send_from_directory(UPLOAD_FOLDER, filename)
    except FileNotFoundError:
        abort(404)

@app.route('/delete_post/<int:post_id>')
def delete_post(post_id):
    """Удаление поста с проверкой прав доступа."""
    if 'user_id' not in session:
        flash('Необходимо войти в систему!', 'error')
        return redirect(url_for('login'))

    if not isinstance(post_id, int) or post_id < 1:
        flash('Недопустимый идентификатор поста!', 'error')
        return redirect(url_for('index'))

    try:
        conn = get_db_connection()
        post = conn.execute('SELECT author_id FROM posts WHERE id = ?', (post_id,)).fetchone()
        if not post:
            flash('Пост не найден!', 'error')
            return redirect(url_for('index'))

        # Проверка прав: только автор или админ
        if post['author_id'] != session['user_id'] and not session.get('is_admin'):
            flash('Недостаточно прав для удаления!', 'error')
            return redirect(url_for('index'))

        conn.execute('DELETE FROM posts WHERE id = ?', (post_id,))
        conn.execute('DELETE FROM comments WHERE post_id = ?', (post_id,))
        conn.commit()
        conn.close()
        flash('Пост удален!', 'success')
    except sqlite3.Error:
        flash('Ошибка удаления поста.', 'error')

    return redirect(url_for('index'))