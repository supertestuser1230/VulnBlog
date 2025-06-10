import os
import re
import secrets
import sqlite3
import logging
from flask import render_template, request, redirect, url_for, session, flash, send_from_directory, abort, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect
from app import app
from models import get_db_connection, User, Post, Comment
from forms import LoginForm, RegisterForm, CommentForm, PostForm
import bleach
from time import *

logging.basicConfig(filename='app.log', level=logging.ERROR)

csrf = CSRFProtect(app)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
UPLOAD_FOLDER = app.config['UPLOAD_FOLDER']
MAX_CONTENT_LENGTH = 5 * 1024 * 1024
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

def allowed_file(filename):
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return ext in ALLOWED_EXTENSIONS and not re.search(pattern=r'[^\w.\-]', string=filename)

def validate_input(input_str, max_length, pattern=None):
    if not input_str or len(input_str.strip()) == 0 or len(input_str) > max_length:
        return False
    if pattern and not re.match(pattern, input_str):
        return False
    if any(char in input_str for char in [';', '--', '/*', '*/']):
        return False
    return True

@app.route('/')
def index():
    try:
        posts = Post.get_all()
        return render_template('index.html', posts=posts)
    except sqlite3.Error as e:
        logging.error(f'Index error: {e}')
        flash('Ошибка загрузки постов.', 'danger')
        return render_template('index.html', posts=[])

@app.route('/login', methods=['GET', 'POST'])
def login():
    login_attempts = session.get('login_attempts', {'count': 0, 'last_attempt': 0})
    if login_attempts['count'] >= 5 and time() - login_attempts['last_attempt'] < 300:
        flash('Слишком много попыток входа. Попробуйте снова через 5 минут.', 'danger')
        return render_template('login.html', form=LoginForm())

    form = LoginForm()
    if form.validate_on_submit():
        try:
            user = User.get_by_username(form.username.data)
            if user and check_password_hash(user.password_hash, form.password.data):
                session.clear()
                session.permanent = True
                session['user_id'] = user.id
                session['username'] = user.username
                session['is_admin'] = user.is_admin
                session['login_attempts'] = {'count': 0, 'last_attempt': 0}
                flash('Вход выполнен успешно!', 'success')
                return redirect(url_for('index'))
            else:
                login_attempts['count'] += 1
                login_attempts['last_attempt'] = time()
                session['login_attempts'] = login_attempts
                flash('Неверные учетные данные!', 'danger')
        except sqlite3.Error as e:
            logging.error(f'Login error: {e}')
            flash(f'Ошибка базы данных: {e}', 'danger')
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        user = User.create(form.username.data, form.email.data, form.password.data)
        if user:
            flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Пользователь с таким именем или email уже существует!', 'danger')
    return render_template('register.html', form=form)

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))

@app.route('/post/<int:post_id>')
def view_post(post_id):
    if not isinstance(post_id, int) or post_id < 1:
        flash('Недопустимый идентификатор поста!', 'danger')
        return redirect(url_for('index'))

    try:
        post = Post.get_by_id(post_id)
        if not post:
            flash('Пост не найден!', 'danger')
            return redirect(url_for('index'))

        comments = Comment.get_by_post_id(post_id)
        return render_template('post.html', post=post, comments=comments, form=CommentForm())
    except sqlite3.Error as e:
        logging.error(f'View post error: {e}')
        flash('Ошибка загрузки поста.', 'danger')
        return redirect(url_for('index'))

@app.route('/post/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    if not isinstance(post_id, int) or post_id < 1:
        flash('Недопустимый идентификатор поста!', 'danger')
        return redirect(url_for('index'))

    form = CommentForm()
    if form.validate_on_submit():
        sanitized_author_name = bleach.clean(form.author_name.data, tags=[], strip=True)
        sanitized_content = bleach.clean(form.content.data, tags=['p', 'br', 'strong', 'em'], strip=True)
        comment_id = Comment.create(post_id, sanitized_author_name, sanitized_content)
        if comment_id:
            flash('Комментарий добавлен!', 'success')
        else:
            flash('Ошибка добавления комментария.', 'danger')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'Ошибка в поле {field}: {error}', 'danger')
    return redirect(url_for('view_post', post_id=post_id))

@app.route('/create_post', methods=['GET', 'POST'])
def create_post():
    if 'user_id' not in session:
        flash('Необходимо войти в систему для создания постов!', 'danger')
        return redirect(url_for('login'))

    form = PostForm()
    if form.validate_on_submit():
        sanitized_title = bleach.clean(form.title.data, tags=[], strip=True)
        sanitized_content = bleach.clean(form.content.data, tags=['p', 'br', 'strong', 'em'], strip=True)
        image_path = None
#        if form.image.data:
#            file = form.image.data
#            if allowed_file(file.filename):
#                filename = secure_filename(file.filename)
#                unique_filename = f"{secrets.token_hex(8)}_{filename}"
#                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
#                try:
#                    file.save(file_path)
#                    image_path = unique_filename
#                except Exception as e:
#                    flash(f'Ошибка загрузки изображения: {e}', 'danger')
#                    return render_template('create_post.html', form=form)
#            else:
#                flash('Недопустимый формат изображения!', 'danger')
#                return render_template('create_post.html', form=form)

        post_id = Post.create(sanitized_title, sanitized_content, session['user_id'], image_path)
        if post_id:
            flash('Пост создан успешно!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Ошибка создания поста.', 'danger')
    return render_template('create_post.html', form=form)

@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    posts = []
    if query and validate_input(query, 100):
        sanitized_query = bleach.clean(query, tags=[], strip=True)
        try:
            conn = get_db_connection()
            posts = conn.execute('''
                SELECT p.*, u.username
                FROM posts p
                JOIN users u ON p.author_id = u.id
                WHERE p.title LIKE ? OR p.content LIKE ?
                ORDER BY p.created_at DESC
            ''', (f'%{sanitized_query}%', f'%{sanitized_query}%')).fetchall()
            conn.close()
        except sqlite3.Error as e:
            logging.error(f'Search error: {e}')
            flash('Ошибка поиска.', 'danger')
    return render_template('search.html', posts=posts, query=query)

@app.route('/admin')
def admin():
    if 'user_id' not in session:
        flash('Доступ запрещен!', 'danger')
        return redirect(url_for('login'))
    if not session.get('is_admin'):
        flash('Недостаточно прав доступа!', 'danger')
        return redirect(url_for('index'))

    try:
        conn = get_db_connection()
        page = request.args.get('page', 1, type=int)
        per_page = 10
        offset = (page - 1) * per_page
        users = conn.execute('SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?', (per_page, offset)).fetchall()
        posts = conn.execute('SELECT * FROM posts ORDER BY created_at DESC LIMIT ? OFFSET ?', (per_page, offset)).fetchall()
        comments = conn.execute('SELECT * FROM comments ORDER BY created_at DESC LIMIT ? OFFSET ?', (per_page, offset)).fetchall()
        conn.close()
        return render_template('admin.html', users=users, posts=posts, comments=comments, page=page, per_page=per_page)
    except sqlite3.Error as e:
        logging.error(f'Admin error: {e}')
        flash('Ошибка загрузки данных.', 'danger')
        return redirect(url_for('index'))

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    if not validate_input(filename, 255) or any(c in filename for c in ['..', '/', '\\', ':']):
        abort(403, description="Invalid filename")
    filename = secure_filename(filename)
    try:
        return send_from_directory(UPLOAD_FOLDER, filename)
    except FileNotFoundError:
        abort(404)

@app.route('/delete_post/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    if 'user_id' not in session:
        flash('Необходимо войти в систему!', 'danger')
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        # Получаем пост как словарь (не как sqlite3.Row)
        post = conn.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
        
        if not post:
            flash('Пост не найден!', 'danger')
            return jsonify({'message': 'Post not found'}), 404

        # Проверяем права доступа (используем post['author_id'] вместо post.author_id)
        if post['author_id'] != session['user_id'] and not session.get('is_admin'):
            flash('Недостаточно прав для удаления!', 'danger')
            return jsonify({'message': 'Permission denied'}), 403

        # Удаляем пост и связанные комментарии
        conn.execute('DELETE FROM posts WHERE id = ?', (post_id,))
        conn.execute('DELETE FROM comments WHERE post_id = ?', (post_id,))
        conn.commit()
        conn.close()
        
        flash('Пост удален!', 'success')
        return jsonify({'message': 'Post deleted'})
        
    except sqlite3.Error as e:
        logging.error(f'Delete post error: {e}')
        flash(f'Ошибка удаления поста: {e}', 'danger')
        return jsonify({'message': 'Database error'}), 500



@app.errorhandler(Exception)
def handle_error(e):
    logging.error(f'Error: {str(e)}', exc_info=True)
    flash('Произошла ошибка сервера.', 'danger')
    return redirect(url_for('index'))
