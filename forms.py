from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SubmitField, EmailField
from wtforms.validators import DataRequired, Length, Email, Regexp

class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=4, max=50), Regexp(r'^[\w]+$')])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=8)])
    submit = SubmitField('Войти')

class RegisterForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=4, max=50), Regexp(r'^[\w]+$')])
    email = EmailField('Email', validators=[DataRequired(), Email(), Length(max=100)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=8)])
    submit = SubmitField('Зарегистрироваться')

class CommentForm(FlaskForm):
    author_name = StringField('Ваше имя', validators=[DataRequired(), Length(min=1, max=50), Regexp(r'^[\w\s]+$')])
    content = TextAreaField('Комментарий', validators=[DataRequired(), Length(min=1, max=1000)])
    submit = SubmitField('Отправить комментарий')

class PostForm(FlaskForm):
    title = StringField('Заголовок', validators=[DataRequired(), Length(min=1, max=200)])
    content = TextAreaField('Содержание', validators=[DataRequired(), Length(min=1, max=10000)])
    submit = SubmitField('Создать пост')
