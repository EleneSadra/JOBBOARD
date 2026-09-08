from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from wtforms import (StringField, PasswordField, SubmitField, TextAreaField,
                     SelectField)
from wtforms.validators import (DataRequired, Length, Email, EqualTo,
                                ValidationError)

from app.models import User


class RegistrationForm(FlaskForm):
    username = StringField("სახელი", validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField("ელფოსტა", validators=[DataRequired(), Email()])
    password = PasswordField("პაროლი", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField("გაიმეორეთ პაროლი",
                                     validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("რეგისტრაცია")

    def validate_username(self, username):
        if User.query.filter_by(username=username.data).first():
            raise ValidationError("ეს სახელი დაკავებულია.")

    def validate_email(self, email):
        if User.query.filter_by(email=email.data).first():
            raise ValidationError("ეს ელფოსტა უკვე რეგისტრირებულია.")


class LoginForm(FlaskForm):
    email = StringField("ელფოსტა", validators=[DataRequired(), Email()])
    password = PasswordField("პაროლი", validators=[DataRequired()])
    submit = SubmitField("შესვლა")


class UpdateProfileForm(FlaskForm):
    username = StringField("სახელი", validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField("ელფოსტა", validators=[DataRequired(), Email()])
    picture = FileField("პროფილის სურათი",
                        validators=[FileAllowed(["jpg", "jpeg", "png"])])
    submit = SubmitField("შენახვა")

    def validate_username(self, username):
        if username.data != current_user.username:
            if User.query.filter_by(username=username.data).first():
                raise ValidationError("ეს სახელი დაკავებულია.")

    def validate_email(self, email):
        if email.data != current_user.email:
            if User.query.filter_by(email=email.data).first():
                raise ValidationError("ეს ელფოსტა უკვე რეგისტრირებულია.")


class JobForm(FlaskForm):
    title = StringField("სათაური", validators=[DataRequired(), Length(max=120)])
    company = StringField("კომპანია", validators=[DataRequired()])
    location = StringField("ლოკაცია", validators=[DataRequired()])
    salary = StringField("ხელფასი", validators=[DataRequired()])
    category = SelectField("კატეგორია", choices=[
        ("IT", "IT"), ("Design", "Design"), ("Marketing", "Marketing"),
        ("Finance", "Finance"), ("Other", "Other")
    ])
    short_description = StringField("მოკლე აღწერა",
                                    validators=[DataRequired(), Length(max=250)])
    full_description = TextAreaField("სრული აღწერა", validators=[DataRequired()])
    submit = SubmitField("შენახვა")