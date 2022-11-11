from flask_wtf import Form, FlaskForm
from wtforms import StringField, PasswordField, BooleanField, RadioField
from wtforms.validators import DataRequired, Length, EqualTo, Email

class RegisterForm(Form):
    name = StringField(
        'Username',
        validators=[DataRequired(), Length(min=6, max=25)]
    )
    email = StringField(
        'Email',
        validators=[DataRequired(), Email(), Length(min=6, max=40)]
    )
    password = PasswordField(
        'Password',
        validators=[DataRequired(), Length(min=6, max=40)]
    )
    confirm = PasswordField(
        'Repeat Password',
        validators=[DataRequired(), EqualTo('password')]
    )
    jury = BooleanField(
        'Jury Duty',
    )



class LoginForm(Form):
    name = StringField(
        'Username',
        validators=[DataRequired()]
    )
    password = PasswordField(
        'Password',
        validators=[DataRequired()]
    )

class JuryForm(Form):
    title = StringField(
        'Title',
        validators=[DataRequired()]
    )
    prompts = StringField(
        'Prompts',
        validators=[DataRequired()]
    )
    question = StringField(
        'Question',
        validators=[DataRequired()]
    )
    vote = RadioField(
        'Vote Type',
        choices=[(0,'Scale Rating'),(1,'Plain Vote'), (2, 'Feedback Only')]
    )

class PostJuryForm(FlaskForm):
    comment = StringField(
        'Comment',
        validators=[DataRequired(), Length(min=6, max=140)]
    )
