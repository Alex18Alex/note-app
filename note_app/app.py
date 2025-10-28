#!/usr/bin/python3
import os
import secrets

from flask import Flask, render_template, request, redirect, url_for, flash, session
from markupsafe import escape
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, TextAreaField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Length
from dotenv import load_dotenv
from sqlalchemy import text
load_dotenv()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    "DATABASE_URL",
    "postgresql://app_user:secure_password_123@localhost:5432/notes_app"
)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')
app.config['WTF_CSRF_ENABLED'] = True

app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600

db = SQLAlchemy(app)
csrf = CSRFProtect(app)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    notes = db.relationship('Note', backref='user', lazy=True)

class Note(db.Model):
    __tablename__ = 'notes'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return '<Note %r>' % self.id

class NoteForm(FlaskForm):
    title = StringField('Заголовок', validators=[
        DataRequired(message='Заголовок обязателен'),
        Length(min=1, max=100, message='Заголовок должен быть от 1 до 100 символов')
    ])
    content = TextAreaField('Содержание', validators=[
        DataRequired(message='Содержание обязательно'),
        Length(min=1, message='Содержание не может быть пустым')
    ])
    submit = SubmitField('Сохранить')

class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

class RegisterForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Зарегистрироваться')

def generate_nonce():
    return secrets.token_urlsafe(16)

@app.context_processor
def inject_nonce():
    return {'csp_nonce': generate_nonce()}

@app.after_request
def set_security_headers(response):
    nonce = generate_nonce()
    csp_policy = (
        f"default-src 'self'; "
        f"script-src 'self' 'nonce-{nonce}'; "
        f"style-src 'self' 'unsafe-inline'; "
        f"img-src 'self' data:; "
        f"font-src 'self'; "
        f"connect-src 'self'; "
        f"frame-ancestors 'self'; "
        f"form-action 'self'; "
        f"object-src 'none'; "
        f"base-uri 'self'; "
    )
    response.headers['Content-Security-Policy'] = csp_policy
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

# def get_db_connection():
#     conn = sqlite3.connect('notes.db')
#     conn.row_factory = sqlite3.Row
#     return conn
#
# def init_user_table():
#     conn = get_db_connection()
#     try:
#         result = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user'").fetchone()
#         if not result:
#             conn.execute('''
#                 CREATE TABLE user (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     username TEXT UNIQUE NOT NULL,
#                     password TEXT NOT NULL
#                 )
#             ''')
#     except Exception as e:
#         print(f"❌ Ошибка при инициализации таблицы user: {e}")
#     finally:
#         conn.close()


def secure_login(username, password):
    try:
        # Используем правильное имя таблицы 'users' и параметризованный запрос
        query = text("SELECT * FROM users WHERE username = :username AND password = :password")
        result = db.session.execute(query, {'username': username, 'password': password})
        user = result.fetchone()

        print(f"✅ Выполняется БЕЗОПАСНЫЙ запрос: username={username}, password={password}")
        return user
    except Exception as e:
        print(f"❌ Ошибка в безопасном запросе: {e}")
        return None


def secure_register(username, password):
    try:
        query = text("INSERT INTO users (username, password) VALUES (:username, :password)")
        db.session.execute(query, {'username': username, 'password': password})
        db.session.commit()

        print(f"✅ Выполняется БЕЗОПАСНЫЙ запрос: username={username}, password={password}")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"❌ Ошибка в безопасном запросе: {e}")
        return False


def is_note_owner(note_id):
    if not is_authenticated():
        return False
    note = Note.query.get(note_id)
    return note and note.user_id == session['user_id']

def is_authenticated():
    return session.get('user_id') is not None

# Инициализация базы данных
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    if not is_authenticated():
        return redirect(url_for('login'))
    notes = Note.query.filter_by(user_id=session['user_id']).all()
    form = NoteForm()
    return render_template('index.html', notes=notes, form=form, username=session.get('username'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_authenticated():
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = secure_login(form.username.data, form.password.data)
        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Успешный вход!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль', 'error')
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if is_authenticated():
        return redirect(url_for('index'))
    form = RegisterForm()
    if form.validate_on_submit():
        if secure_register(form.username.data, form.password.data):
            flash('Регистрация успешна! Теперь вы можете войти.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Имя пользователя уже существует', 'error')
    return render_template('register.html', form=form)

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'success')
    return redirect(url_for('login'))

@app.route('/add', methods=['POST'])
def add_note():
    if not is_authenticated():
        return redirect(url_for('login'))
    form = NoteForm()
    if form.validate_on_submit():
        try:
            new_note = Note(
                title=form.title.data,
                content=form.content.data,
                user_id=session['user_id']
            )
            db.session.add(new_note)
            db.session.commit()
            flash('Заметка успешно добавлена', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении заметки: {str(e)}', 'error')
    return redirect(url_for('index'))

@app.route('/edit/<int:note_id>', methods=['GET', 'POST'])
def edit_note(note_id):
    if not is_authenticated():
        return redirect(url_for('login'))
    if not is_note_owner(note_id):
        flash('У вас нет прав для редактирования этой заметки', 'error')
        return redirect(url_for('index'))
    note = Note.query.get_or_404(note_id)
    form = NoteForm(obj=note)
    if form.validate_on_submit():
        try:
            note.title = form.title.data
            note.content = form.content.data
            db.session.commit()
            flash('Заметка успешно обновлена!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении заметки: {str(e)}', 'error')
    return render_template('edit.html', note=note, form=form)

@app.route('/delete/<int:note_id>')
def delete_note(note_id):
    if not is_authenticated():
        return redirect(url_for('login'))
    if not is_note_owner(note_id):
        flash('У вас нет прав для удаления этой заметки', 'error')
        return redirect(url_for('index'))
    note = Note.query.get_or_404(note_id)
    try:
        db.session.delete(note)
        db.session.commit()
        flash('Заметка успешно удалена!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении заметки: {str(e)}', 'error')
    return redirect(url_for('index'))

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    if not is_authenticated():
        return redirect(url_for('login'))
    username = escape(request.form.get('username'))
    feedback = escape(request.form.get('feedback'))
    return f'Отзыв получен: {feedback} от {username}'

if __name__ == '__main__':
    app.run(debug=False)