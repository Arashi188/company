"""
Admin routes module
"""
import os
from flask import render_template, redirect, url_for, flash, request, Blueprint, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import Product, Category
from app.forms import ProductForm, ProductEditForm, CategoryForm, SearchForm
from app.utils import save_image, sanitize_html
from functools import wraps

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('You need admin privileges to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# Dashboard
@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    """Admin dashboard"""
    product_count = Product.query.count()
    category_count = Category.query.count()
    recent_products = Product.query.order_by(Product.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         product_count=product_count,
                         category_count=category_count,
                         recent_products=recent_products,
                         title='Admin Dashboard')

# Product Management
@admin_bp.route('/products')
@login_required
@admin_required
def products():
    """Product list management"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = Product.query
    
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    
    products = query.order_by(Product.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    return render_template('admin/products.html',
                         products=products,
                         search=search,
                         title='Manage Products')

@admin_bp.route('/products/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_product():
    """Add new product"""
    form = ProductForm()
    
    if form.validate_on_submit():
        try:
            # Save image
            filename = save_image(form.image.data)
            
            # Sanitize description
            description = sanitize_html(form.description.data)
            shipping_details = sanitize_html(form.shipping_details.data) if form.shipping_details.data else ''
            
            # Create product
            product = Product(
                name=form.name.data,
                description=description,
                price=form.price.data,
                image=filename,
                shipping_details=shipping_details,
                category_id=form.category_id.data
            )
            
            db.session.add(product)
            db.session.commit()
            
            flash(f'Product "{product.name}" added successfully!', 'success')
            return redirect(url_for('admin.products'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding product: {str(e)}', 'danger')
    
    return render_template('admin/product_form.html',
                         form=form,
                         title='Add Product',
                         action='Add')

@admin_bp.route('/products/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_product(id):
    """Edit existing product"""
    product = Product.query.get_or_404(id)
    form = ProductEditForm(obj=product)
    
    if form.validate_on_submit():
        try:
            product.name = form.name.data
            product.description = sanitize_html(form.description.data)
            product.price = form.price.data
            product.shipping_details = sanitize_html(form.shipping_details.data) if form.shipping_details.data else ''
            product.category_id = form.category_id.data
            
            # Handle image upload if provided
            if form.image.data:
                # Delete old image
                old_image = os.path.join(current_app.root_path, 'static/uploads', product.image)
                if os.path.exists(old_image):
                    os.remove(old_image)
                
                # Save new image
                filename = save_image(form.image.data)
                product.image = filename
            
            db.session.commit()
            flash(f'Product "{product.name}" updated successfully!', 'success')
            return redirect(url_for('admin.products'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating product: {str(e)}', 'danger')
    
    return render_template('admin/product_form.html',
                         form=form,
                         product=product,
                         title='Edit Product',
                         action='Edit')

@admin_bp.route('/products/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_product(id):
    """Delete product"""
    product = Product.query.get_or_404(id)
    
    try:
        # Delete image file
        image_path = os.path.join(current_app.root_path, 'static/uploads', product.image)
        if os.path.exists(image_path):
            os.remove(image_path)
        
        # Delete product from database
        db.session.delete(product)
        db.session.commit()
        
        flash(f'Product "{product.name}" deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting product: {str(e)}', 'danger')
    
    return redirect(url_for('admin.products'))

# Category Management
@admin_bp.route('/categories')
@login_required
@admin_required
def categories():
    """Category list management"""
    categories = Category.query.order_by(Category.name).all()
    return render_template('admin/categories.html',
                         categories=categories,
                         title='Manage Categories')

@admin_bp.route('/categories/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_category():
    """Add new category"""
    form = CategoryForm()
    
    if form.validate_on_submit():
        try:
            category = Category(
                name=form.name.data,
                description=form.description.data
            )
            category.save()
            
            flash(f'Category "{category.name}" added successfully!', 'success')
            return redirect(url_for('admin.categories'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding category: {str(e)}', 'danger')
    
    return render_template('admin/category_form.html',
                         form=form,
                         title='Add Category',
                         action='Add')

@admin_bp.route('/categories/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_category(id):
    """Edit existing category"""
    category = Category.query.get_or_404(id)
    form = CategoryForm(obj=category)
    
    if form.validate_on_submit():
        try:
            category.name = form.name.data
            category.description = form.description.data
            category.slug = None  # Will regenerate on save
            category.save()
            
            flash(f'Category "{category.name}" updated successfully!', 'success')
            return redirect(url_for('admin.categories'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating category: {str(e)}', 'danger')
    
    return render_template('admin/category_form.html',
                         form=form,
                         category=category,
                         title='Edit Category',
                         action='Edit')

@admin_bp.route('/categories/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_category(id):
    """Delete category"""
    category = Category.query.get_or_404(id)
    
    # Check if category has products
    if category.products.count() > 0:
        flash(f'Cannot delete category "{category.name}" because it has products.', 'danger')
        return redirect(url_for('admin.categories'))
    
    try:
        db.session.delete(category)
        db.session.commit()
        flash(f'Category "{category.name}" deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting category: {str(e)}', 'danger')
    
    return redirect(url_for('admin.categories'))