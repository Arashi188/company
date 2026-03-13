"""
Database models module
"""
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager
import re

def slugify(text):
    """Generate URL-friendly slug from text"""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')

class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user', nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Notification preferences
    email_orders = db.Column(db.Boolean, default=True)
    whatsapp_orders = db.Column(db.Boolean, default=True)
    promotions = db.Column(db.Boolean, default=False)
    newsletter = db.Column(db.Boolean, default=False)
    
    # Relationships
    orders = db.relationship('Order', backref='user', lazy='dynamic')
    wishlist_items = db.relationship('Wishlist', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    addresses = db.relationship('Address', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Set hashed password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        """Check if user is admin"""
        return self.role == 'admin'
    
    def __repr__(self):
        return f'<User {self.username}>'

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    return User.query.get(int(user_id))

class Category(db.Model):
    """Product category model"""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    products = db.relationship('Product', backref='category', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, *args, **kwargs):
        """Initialize with slug generation"""
        if 'name' in kwargs and not kwargs.get('slug'):
            kwargs['slug'] = slugify(kwargs['name'])
        super().__init__(*args, **kwargs)
    
    def save(self):
        """Save category with slug"""
        if not self.slug:
            self.slug = slugify(self.name)
        db.session.add(self)
        db.session.commit()
    
    def __repr__(self):
        return f'<Category {self.name}>'

class Product(db.Model):
    """Product model"""
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    slug = db.Column(db.String(220), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    original_price = db.Column(db.Float)  # For showing discounts
    discount = db.Column(db.Integer, default=0)  # Discount percentage
    image = db.Column(db.String(500), nullable=False)
    shipping_details = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    stock = db.Column(db.Integer, default=0)
    
    # Relationships
    order_items = db.relationship('OrderItem', backref='product', lazy='dynamic')
    wishlist_items = db.relationship('Wishlist', backref='product', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, *args, **kwargs):
        """Initialize with slug generation"""
        if 'name' in kwargs and not kwargs.get('slug'):
            kwargs['slug'] = slugify(kwargs['name'])
        super().__init__(*args, **kwargs)
    
    @property
    def formatted_price(self):
        """Return formatted price"""
        return f"${self.price:,.2f}"
    
    @property
    def formatted_original_price(self):
        """Return formatted original price if exists"""
        if self.original_price:
            return f"${self.original_price:,.2f}"
        return None
    
    @property
    def image_url(self):
        """Return image URL"""
        return f"/static/uploads/{self.image}"
    
    def save(self):
        """Save product with slug"""
        if not self.slug:
            self.slug = slugify(self.name)
        db.session.add(self)
        db.session.commit()
    
    def get_whatsapp_message(self):
        """Generate WhatsApp message for this product"""
        message = (
            f"Hello, I saw this product on your website.\n\n"
            f"Product Name: {self.name}\n"
            f"Product ID: {self.id}\n"
            f"Price: {self.formatted_price}\n\n"
            f"I would like to order this item."
        )
        return message
    
    def __repr__(self):
        return f'<Product {self.name}>'

class Order(db.Model):
    """Order model"""
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    customer_email = db.Column(db.String(120))
    shipping_address = db.Column(db.Text, nullable=False)
    notes = db.Column(db.Text)
    status = db.Column(db.String(50), default='pending')
    total = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, *args, **kwargs):
        """Initialize with order number generation"""
        if 'order_number' not in kwargs:
            # Generate order number: ORD-YYYYMMDD-XXXX
            date_str = datetime.utcnow().strftime('%Y%m%d')
            last_order = Order.query.filter(Order.order_number.like(f'ORD-{date_str}-%')) \
                                   .order_by(Order.id.desc()).first()
            if last_order:
                last_num = int(last_order.order_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            kwargs['order_number'] = f"ORD-{date_str}-{new_num:04d}"
        super().__init__(*args, **kwargs)
    
    @property
    def status_color(self):
        """Return color class for status badge"""
        colors = {
            'pending': 'warning',
            'processing': 'info',
            'completed': 'success',
            'cancelled': 'danger'
        }
        return colors.get(self.status, 'secondary')
    
    def __repr__(self):
        return f'<Order {self.order_number}>'

class OrderItem(db.Model):
    """Order items model"""
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    product_name = db.Column(db.String(200), nullable=False)  # Snapshot of product name at time of order
    price = db.Column(db.Float, nullable=False)  # Snapshot of price at time of order
    quantity = db.Column(db.Integer, default=1)
    subtotal = db.Column(db.Float, nullable=False)
    
    def __repr__(self):
        return f'<OrderItem {self.product_name} x{self.quantity}>'

class Wishlist(db.Model):
    """Wishlist model"""
    __tablename__ = 'wishlists'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    added_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensure a user can't add the same product twice
    __table_args__ = (db.UniqueConstraint('user_id', 'product_id', name='unique_user_product'),)
    
    def __repr__(self):
        return f'<Wishlist User:{self.user_id} Product:{self.product_id}>'

class Address(db.Model):
    """Address model for users"""
    __tablename__ = 'addresses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # Recipient name
    address_line1 = db.Column(db.String(200), nullable=False)
    address_line2 = db.Column(db.String(200))
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    zip_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(100), nullable=False, default='United States')
    phone = db.Column(db.String(20), nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Address {self.name} - {self.city}>'

class Cart(db.Model):
    """Cart model for database storage (optional, can also use session)"""
    __tablename__ = 'carts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = db.relationship('CartItem', backref='cart', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Cart User:{self.user_id}>'

class CartItem(db.Model):
    """Cart items model"""
    __tablename__ = 'cart_items'
    
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('carts.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensure a product can't be added twice to the same cart
    __table_args__ = (db.UniqueConstraint('cart_id', 'product_id', name='unique_cart_product'),)
    
    def __repr__(self):
        return f'<CartItem Product:{self.product_id} x{self.quantity}>'

class SiteSettings(db.Model):
    """Site settings model"""
    __tablename__ = 'site_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    store_name = db.Column(db.String(100), default='E-Commerce Catalog')
    store_description = db.Column(db.Text)
    store_email = db.Column(db.String(120))
    store_phone = db.Column(db.String(20))
    store_address = db.Column(db.Text)
    currency = db.Column(db.String(3), default='USD')
    products_per_page = db.Column(db.Integer, default=12)
    
    # WhatsApp settings
    whatsapp_number = db.Column(db.String(20))
    whatsapp_template = db.Column(db.Text, default="Hello, I saw this product on your website.\n\nProduct Name: {product_name}\nProduct ID: {product_id}\nPrice: {price}\n\nI would like to order this item.")
    auto_response = db.Column(db.Boolean, default=False)
    auto_response_message = db.Column(db.Text)
    
    # SEO settings
    meta_title = db.Column(db.String(200))
    meta_description = db.Column(db.Text)
    meta_keywords = db.Column(db.String(200))
    google_analytics = db.Column(db.String(50))
    enable_sitemap = db.Column(db.Boolean, default=True)
    
    # Shipping settings
    shipping_cost = db.Column(db.Float, default=9.99)
    free_shipping_threshold = db.Column(db.Float, default=100)
    delivery_days = db.Column(db.String(50), default='3-7 business days')
    shipping_policy = db.Column(db.Text)
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @classmethod
    def get_settings(cls):
        """Get or create settings"""
        settings = cls.query.first()
        if not settings:
            settings = cls()
            db.session.add(settings)
            db.session.commit()
        return settings
    
    def __repr__(self):
        return f'<SiteSettings {self.store_name}>'

class ActivityLog(db.Model):
    """Activity log model for tracking user actions"""
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ActivityLog {self.action} at {self.created_at}>'