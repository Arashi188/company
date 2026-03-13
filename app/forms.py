"""
Form definitions module
"""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, TextAreaField, FloatField, SelectField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Optional
from app.models import Category, User
import re

class LoginForm(FlaskForm):
    """Admin login form"""
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')

class CategoryForm(FlaskForm):
    """Category management form"""
    name = StringField('Category Name', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    
    def validate_name(self, field):
        """Validate category name uniqueness"""
        category = Category.query.filter_by(name=field.data).first()
        if category:
            raise ValidationError('Category name already exists.')

class ProductForm(FlaskForm):
    """Product management form"""
    name = StringField('Product Name', validators=[DataRequired(), Length(min=3, max=200)])
    description = TextAreaField('Description', validators=[DataRequired()])
    price = FloatField('Price', validators=[DataRequired()])
    shipping_details = TextAreaField('Shipping Information', validators=[Optional()])
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    image = FileField('Product Image', validators=[
        FileRequired(),
        FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Images only!')
    ])
    
    def __init__(self, *args, **kwargs):
        """Initialize with category choices"""
        super().__init__(*args, **kwargs)
        self.category_id.choices = [(c.id, c.name) for c in Category.query.order_by('name').all()]
    
    def validate_price(self, field):
        """Validate price is positive"""
        if field.data <= 0:
            raise ValidationError('Price must be greater than zero.')

class ProductEditForm(ProductForm):
    """Product edit form (image optional)"""
    image = FileField('Product Image', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Images only!')
    ])

class SearchForm(FlaskForm):
    """Search form"""
    query = StringField('Search', validators=[Optional()])
    category = SelectField('Category', coerce=int, validators=[Optional()])
    
    def __init__(self, *args, **kwargs):
        """Initialize with category choices"""
        super().__init__(*args, **kwargs)
        categories = [(0, 'All Categories')] + [(c.id, c.name) for c in Category.query.order_by('name').all()]
        self.category.choices = categories