"""
Application factory module
"""
import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import config

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config_name='default'):
    """Application factory function"""
    
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(config[config_name])

    # Ensure upload directory exists
    upload_path = os.path.join(app.root_path, 'static/uploads')
    os.makedirs(upload_path, exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Configure login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    # Register blueprints
    from app.routes import main_bp
    from app.auth import auth_bp
    from app.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Register error handlers
    register_error_handlers(app)

    # Create database tables and default admin
    with app.app_context():
        db.create_all()

        from app.models import User
        from werkzeug.security import generate_password_hash

        admin = User.query.filter_by(role='admin').first()

        if not admin and os.environ.get('ADMIN_USERNAME'):
            admin = User(
                username=os.environ.get('ADMIN_USERNAME'),
                email=os.environ.get('ADMIN_EMAIL'),
                password_hash=generate_password_hash(
                    os.environ.get('ADMIN_PASSWORD')
                ),
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()

    return app


def register_error_handlers(app):
    """Register error handlers"""

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500