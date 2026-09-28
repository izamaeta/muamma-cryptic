from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField
from wtforms.validators import DataRequired, Length


class LoginForm(FlaskForm):
    email = EmailField("E-posta", validators=[DataRequired(), Length(max=255)])
    password = PasswordField("Şifre", validators=[DataRequired(), Length(max=256)])