from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length
from .models import User
from flask_wtf.file import FileAllowed, FileField

class RegistrationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    phone = StringField('Phone Number', validators=[DataRequired()])
    address = StringField('Address', validators=[DataRequired()])
    user_type = SelectField('User Type', choices=[('restaurant', 'Restaurant/Hotel'),
                                                  ('ngo', 'NGO/Organization'),
                                                  ('donor', 'Individual Donor'),
                                                  ('beneficiary', 'End Beneficiary'),
    ('delivery', 'Delivery Personnel')],
                            validators=[DataRequired()])
    submit = SubmitField('Register')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email is already registered.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class FoodPostForm(FlaskForm):
    item_name = StringField('Food Item Name', validators=[DataRequired()])
    description = StringField('Description', validators=[DataRequired()])
    quantity = StringField('Quantity', validators=[DataRequired()])
    expiry_timeline = StringField('Expiry Timeline', validators=[DataRequired()])
    city = StringField('Address', validators=[DataRequired()])
    pin_code = StringField('City', validators=[DataRequired()])
    image = FileField('Optional Image', validators=[FileAllowed(['jpg', 'png', 'jpeg'])])
    submit = SubmitField('Post Food')
    is_paid = BooleanField('Is this a paid item?')
    price = StringField('Price (if paid)')

class OTPForm(FlaskForm):
    otp = StringField('Enter OTP', validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField('Verify OTP')

from wtforms.validators import Optional

class ProfileEditForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    phone = StringField('Phone', validators=[DataRequired(), Length(max=15)])
    address = StringField('Address', validators=[DataRequired(), Length(max=200)])

    bank_account_holder = StringField('Account Holder Name', validators=[Optional(), Length(max=100)])
    bank_name = StringField('Bank Name', validators=[Optional(), Length(max=100)])
    account_number = StringField('Account Number', validators=[Optional(), Length(max=30)])
    ifsc_code = StringField('IFSC Code', validators=[Optional(), Length(max=15)])
    upi_id = StringField('UPI ID', validators=[Optional(), Length(max=50)])
    pan_number = StringField('PAN Number', validators=[Optional(), Length(max=10)])

    password = PasswordField('New Password', validators=[Optional(), Length(min=6)])
    submit = SubmitField('Save Changes')
