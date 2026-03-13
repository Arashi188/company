"""
Public routes module
"""
from flask import render_template, request, Blueprint, current_app, abort, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from app import db
from app.models import Product, Category, User, Order, Wishlist, Cart, Address
from app.forms import SearchForm
from app.utils import format_whatsapp_url
from datetime import datetime
import json

main_bp = Blueprint('main', __name__)

@main_bp.context_processor
def inject_search_form():
    """Inject search form into all templates"""
    form = SearchForm()
    return dict(search_form=form, Category=Category)

@main_bp.route('/')
def index():
    """Homepage"""
    featured_products = Product.query.order_by(Product.created_at.desc()).limit(8).all()
    categories = Category.query.limit(6).all()
    
    # Get counts for stats
    product_count = Product.query.count()
    
    return render_template('index.html',
                         featured_products=featured_products,
                         categories=categories,
                         product_count=product_count,
                         title='Home - E-Commerce Catalog')

@main_bp.route('/products')
def products():
    """Product catalog page with filtering and pagination"""
    page = request.args.get('page', 1, type=int)
    category_slug = request.args.get('category', '')
    search_query = request.args.get('q', '')
    
    # Build query
    query = Product.query
    
    if category_slug:
        category = Category.query.filter_by(slug=category_slug).first_or_404()
        query = query.filter_by(category_id=category.id)
    
    if search_query:
        query = query.filter(Product.name.ilike(f'%{search_query}%'))
    
    # Get paginated results
    pagination = query.order_by(Product.created_at.desc()).paginate(
        page=page,
        per_page=current_app.config.get('PRODUCTS_PER_PAGE', 12),
        error_out=False
    )
    
    products = pagination.items
    categories = Category.query.all()
    
    return render_template('products.html',
                         products=products,
                         pagination=pagination,
                         categories=categories,
                         current_category=category_slug,
                         search_query=search_query,
                         title='Products - E-Commerce Catalog')

@main_bp.route('/product/<slug>')
def product_detail(slug):
    """Product detail page"""
    product = Product.query.filter_by(slug=slug).first_or_404()
    
    # Generate WhatsApp URL
    whatsapp_url = format_whatsapp_url(
        current_app.config['WHATSAPP_PHONE_NUMBER'],
        product.get_whatsapp_message()
    )
    
    # Get related products (same category)
    related_products = Product.query.filter(
        Product.category_id == product.category_id,
        Product.id != product.id
    ).limit(4).all()
    
    return render_template('product_detail.html',
                         product=product,
                         whatsapp_url=whatsapp_url,
                         related_products=related_products,
                         title=f'{product.name} - E-Commerce Catalog',
                         meta_description=product.description[:160])

@main_bp.route('/faq')
def faq():
    """FAQ page"""
    return render_template('faq.html', title='FAQ - E-Commerce Catalog')

@main_bp.route('/shipping')
def shipping():
    """Shipping information page"""
    return render_template('shipping.html', title='Shipping Information')

@main_bp.route('/returns')
def returns():
    """Returns policy page"""
    return render_template('returns.html', title='Returns & Refunds')

@main_bp.route('/terms')
def terms():
    """Terms and conditions page"""
    return render_template('terms.html', title='Terms and Conditions')

@main_bp.route('/privacy')
def privacy():
    """Privacy policy page"""
    return render_template('privacy.html', title='Privacy Policy')

@main_bp.route('/cart')
def cart():
    """Shopping cart page"""
    # Get cart from session
    cart_items = session.get('cart', {})
    cart_data = []
    subtotal = 0
    
    for product_id, quantity in cart_items.items():
        product = Product.query.get(int(product_id))
        if product:
            item_total = product.price * quantity
            subtotal += item_total
            cart_data.append({
                'product': product,
                'quantity': quantity,
                'total': item_total,
                'total_formatted': f"${item_total:,.2f}"
            })
    
    # Calculate shipping (free over $100)
    shipping = 0 if subtotal > 100 else 9.99
    total = subtotal + shipping
    
    return render_template('cart.html',
                         cart={'items': cart_data, 'total_items': len(cart_data),
                               'subtotal': f"${subtotal:,.2f}", 'shipping': f"${shipping:,.2f}",
                               'total': f"${total:,.2f}"},
                         title='Shopping Cart')

@main_bp.route('/cart/add', methods=['POST'])
def add_to_cart():
    """Add item to cart"""
    data = request.get_json()
    product_id = str(data.get('product_id'))
    quantity = int(data.get('quantity', 1))
    
    # Initialize cart in session if not exists
    if 'cart' not in session:
        session['cart'] = {}
    
    # Update quantity
    if product_id in session['cart']:
        session['cart'][product_id] += quantity
    else:
        session['cart'][product_id] = quantity
    
    # Update cart count
    session['cart_count'] = sum(session['cart'].values())
    session.modified = True
    
    return jsonify({'success': True, 'cart_count': session['cart_count']})

@main_bp.route('/cart/update', methods=['POST'])
def update_cart():
    """Update cart item quantity"""
    data = request.get_json()
    product_id = str(data.get('product_id'))
    quantity = int(data.get('quantity'))
    
    if 'cart' in session and product_id in session['cart']:
        if quantity > 0:
            session['cart'][product_id] = quantity
        else:
            del session['cart'][product_id]
        
        session['cart_count'] = sum(session['cart'].values())
        session.modified = True
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Item not found'})

@main_bp.route('/cart/remove', methods=['POST'])
def remove_from_cart():
    """Remove item from cart"""
    data = request.get_json()
    product_id = str(data.get('product_id'))
    
    if 'cart' in session and product_id in session['cart']:
        del session['cart'][product_id]
        session['cart_count'] = sum(session['cart'].values())
        session.modified = True
        return jsonify({'success': True})
    
    return jsonify({'success': False})

@main_bp.route('/wishlist')
def wishlist():
    """Wishlist page"""
    # Get wishlist from session (or database for logged-in users)
    if current_user.is_authenticated:
        wishlist_items = Wishlist.query.filter_by(user_id=current_user.id).all()
    else:
        wishlist_ids = session.get('wishlist', [])
        wishlist_items = []
        for product_id in wishlist_ids:
            product = Product.query.get(product_id)
            if product:
                wishlist_items.append({'product': product, 'added_date': datetime.now()})
    
    # Get recommended products
    recommended = Product.query.order_by(Product.created_at.desc()).limit(4).all()
    
    return render_template('wishlist.html',
                         wishlist={'items': wishlist_items},
                         recommended_products=recommended,
                         title='My Wishlist')

@main_bp.route('/wishlist/add', methods=['POST'])
def add_to_wishlist():
    """Add item to wishlist"""
    data = request.get_json()
    product_id = data.get('product_id')
    
    if current_user.is_authenticated:
        # Check if already in wishlist
        existing = Wishlist.query.filter_by(
            user_id=current_user.id, 
            product_id=product_id
        ).first()
        
        if not existing:
            wishlist_item = Wishlist(user_id=current_user.id, product_id=product_id)
            db.session.add(wishlist_item)
            db.session.commit()
    else:
        # Store in session
        if 'wishlist' not in session:
            session['wishlist'] = []
        
        if product_id not in session['wishlist']:
            session['wishlist'].append(product_id)
            session['wishlist_count'] = len(session['wishlist'])
            session.modified = True
    
    return jsonify({'success': True})

@main_bp.route('/wishlist/remove', methods=['POST'])
def remove_from_wishlist():
    """Remove item from wishlist"""
    data = request.get_json()
    product_id = data.get('product_id')
    
    if current_user.is_authenticated:
        Wishlist.query.filter_by(
            user_id=current_user.id, 
            product_id=product_id
        ).delete()
        db.session.commit()
    else:
        if 'wishlist' in session and product_id in session['wishlist']:
            session['wishlist'].remove(product_id)
            session['wishlist_count'] = len(session['wishlist'])
            session.modified = True
    
    return jsonify({'success': True})

@main_bp.route('/wishlist/clear', methods=['POST'])
def clear_wishlist():
    """Clear entire wishlist"""
    if current_user.is_authenticated:
        Wishlist.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
    else:
        session['wishlist'] = []
        session['wishlist_count'] = 0
        session.modified = True
    
    return jsonify({'success': True})

@main_bp.route('/wishlist/add-all-to-cart', methods=['POST'])
def add_all_wishlist_to_cart():
    """Add all wishlist items to cart"""
    if current_user.is_authenticated:
        wishlist_items = Wishlist.query.filter_by(user_id=current_user.id).all()
        product_ids = [item.product_id for item in wishlist_items]
    else:
        product_ids = session.get('wishlist', [])
    
    # Initialize cart
    if 'cart' not in session:
        session['cart'] = {}
    
    # Add all items to cart
    for product_id in product_ids:
        str_id = str(product_id)
        if str_id in session['cart']:
            session['cart'][str_id] += 1
        else:
            session['cart'][str_id] = 1
    
    session['cart_count'] = sum(session['cart'].values())
    session.modified = True
    
    return jsonify({'success': True})

@main_bp.route('/account')
@login_required
def account():
    """User account page"""
    # Get user's recent orders
    recent_orders = Order.query.filter_by(user_id=current_user.id)\
                               .order_by(Order.created_at.desc())\
                               .limit(5).all()
    
    # Get wishlist count
    wishlist_count = Wishlist.query.filter_by(user_id=current_user.id).count()
    
    # Get addresses
    addresses = Address.query.filter_by(user_id=current_user.id).all()
    
    return render_template('account.html',
                         order_count=len(recent_orders),
                         wishlist_count=wishlist_count,
                         pending_orders=sum(1 for o in recent_orders if o.status == 'pending'),
                         recent_orders=recent_orders,
                         addresses=addresses,
                         title='My Account')

@main_bp.route('/orders')
@login_required
def orders():
    """User orders page"""
    page = request.args.get('page', 1, type=int)
    
    pagination = Order.query.filter_by(user_id=current_user.id)\
                           .order_by(Order.created_at.desc())\
                           .paginate(page=page, per_page=10, error_out=False)
    
    return render_template('orders.html',
                         orders=pagination,
                         title='My Orders')

@main_bp.route('/account/update-profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile"""
    # Get form data
    email = request.form.get('email')
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    phone = request.form.get('phone')
    
    # Update user
    current_user.email = email
    current_user.first_name = first_name
    current_user.last_name = last_name
    current_user.phone = phone
    
    # Handle password change
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    
    if current_password and new_password:
        if current_user.check_password(current_password):
            current_user.set_password(new_password)
            flash('Password updated successfully!', 'success')
        else:
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('main.account'))
    
    db.session.commit()
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('main.account'))

@main_bp.route('/account/addresses/add', methods=['POST'])
@login_required
def add_address():
    """Add new address"""
    address = Address(
        user_id=current_user.id,
        name=request.form.get('name'),
        address_line1=request.form.get('address_line1'),
        address_line2=request.form.get('address_line2'),
        city=request.form.get('city'),
        state=request.form.get('state'),
        zip_code=request.form.get('zip_code'),
        country=request.form.get('country'),
        phone=request.form.get('phone'),
        is_default=request.form.get('is_default') == 'on'
    )
    
    # If this is default, remove default from others
    if address.is_default:
        Address.query.filter_by(user_id=current_user.id, is_default=True).update({'is_default': False})
    
    db.session.add(address)
    db.session.commit()
    
    flash('Address added successfully!', 'success')
    return redirect(url_for('main.account'))

@main_bp.route('/account/addresses/set-default/<int:address_id>', methods=['POST'])
@login_required
def set_default_address(address_id):
    """Set address as default"""
    # Remove default from all
    Address.query.filter_by(user_id=current_user.id, is_default=True).update({'is_default': False})
    
    # Set new default
    address = Address.query.get_or_404(address_id)
    if address.user_id == current_user.id:
        address.is_default = True
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'success': False})

@main_bp.route('/account/addresses/delete/<int:address_id>', methods=['POST'])
@login_required
def delete_address(address_id):
    """Delete address"""
    address = Address.query.get_or_404(address_id)
    if address.user_id == current_user.id:
        db.session.delete(address)
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'success': False})

@main_bp.route('/account/update-notifications', methods=['POST'])
@login_required
def update_notifications():
    """Update notification preferences"""
    # Update user preferences
    current_user.email_orders = request.form.get('email_orders') == 'on'
    current_user.whatsapp_orders = request.form.get('whatsapp_orders') == 'on'
    current_user.promotions = request.form.get('promotions') == 'on'
    current_user.newsletter = request.form.get('newsletter') == 'on'
    
    db.session.commit()
    flash('Notification preferences updated!', 'success')
    return redirect(url_for('main.account'))

@main_bp.route('/checkout')
def checkout():
    """Checkout page"""
    # Get cart from session
    cart_items = session.get('cart', {})
    if not cart_items:
        flash('Your cart is empty!', 'warning')
        return redirect(url_for('main.products'))
    
    cart_data = []
    subtotal = 0
    
    for product_id, quantity in cart_items.items():
        product = Product.query.get(int(product_id))
        if product:
            item_total = product.price * quantity
            subtotal += item_total
            cart_data.append({
                'product': product,
                'quantity': quantity,
                'total': item_total,
                'total_formatted': f"${item_total:,.2f}"
            })
    
    # Calculate shipping
    shipping = 0 if subtotal > 100 else 9.99
    total = subtotal + shipping
    
    return render_template('checkout.html',
                         cart={'items': cart_data},
                         subtotal=f"${subtotal:,.2f}",
                         shipping_cost=f"${shipping:,.2f}",
                         total=f"${total:,.2f}",
                         title='Checkout')

@main_bp.route('/checkout/process', methods=['POST'])
def process_checkout():
    """Process checkout and create order"""
    # Get form data
    name = request.form.get('name')
    phone = request.form.get('phone')
    email = request.form.get('email')
    address = request.form.get('address')
    city = request.form.get('city')
    state = request.form.get('state')
    zip_code = request.form.get('zip')
    notes = request.form.get('notes')
    
    # Get cart items
    cart_items = session.get('cart', {})
    
    # Create order in database
    order = Order(
        user_id=current_user.id if current_user.is_authenticated else None,
        customer_name=name,
        customer_phone=phone,
        customer_email=email,
        shipping_address=f"{address}, {city}, {state} {zip_code}",
        notes=notes,
        status='pending',
        total=0  # Will calculate below
    )
    
    db.session.add(order)
    db.session.flush()  # Get order ID
    
    # Add order items and calculate total
    total = 0
    for product_id, quantity in cart_items.items():
        product = Product.query.get(int(product_id))
        if product:
            item_total = product.price * quantity
            total += item_total
            # You would add OrderItem here if you have that model
    
    order.total = total
    db.session.commit()
    
    # Clear cart
    session.pop('cart', None)
    session.pop('cart_count', None)
    session.modified = True
    
    return render_template('checkout_success.html',
                         order=order,
                         title='Order Confirmed')

@main_bp.route('/contact', methods=['POST'])
def contact_submit():
    """Handle contact form submission"""
    name = request.form.get('name')
    email = request.form.get('email')
    subject = request.form.get('subject')
    message = request.form.get('message')
    
    # Here you would typically send an email or save to database
    # For now, just flash a success message
    
    flash(f'Thank you {name}! Your message has been sent. We\'ll get back to you soon.', 'success')
    return redirect(url_for('main.index') + '#contact')

@main_bp.route('/search')
def search():
    """Search products"""
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'relevance')
    category_id = request.args.get('category', type=int)
    price_range = request.args.get('price', '')
    
    # Build query
    search_query = Product.query
    
    if query:
        search_query = search_query.filter(Product.name.ilike(f'%{query}%') | 
                                          Product.description.ilike(f'%{query}%'))
    
    if category_id:
        search_query = search_query.filter_by(category_id=category_id)
    
    # Price filter
    if price_range:
        if price_range == '0-25':
            search_query = search_query.filter(Product.price <= 25)
        elif price_range == '25-50':
            search_query = search_query.filter(Product.price.between(25, 50))
        elif price_range == '50-100':
            search_query = search_query.filter(Product.price.between(50, 100))
        elif price_range == '100-200':
            search_query = search_query.filter(Product.price.between(100, 200))
        elif price_range == '200+':
            search_query = search_query.filter(Product.price >= 200)
    
    # Sorting
    if sort == 'price_asc':
        search_query = search_query.order_by(Product.price.asc())
    elif sort == 'price_desc':
        search_query = search_query.order_by(Product.price.desc())
    elif sort == 'newest':
        search_query = search_query.order_by(Product.created_at.desc())
    elif sort == 'name_asc':
        search_query = search_query.order_by(Product.name.asc())
    elif sort == 'name_desc':
        search_query = search_query.order_by(Product.name.desc())
    else:  # relevance (newest first as default)
        search_query = search_query.order_by(Product.created_at.desc())
    
    # Pagination
    pagination = search_query.paginate(page=page, per_page=12, error_out=False)
    
    # Get all categories for filter
    categories = Category.query.all()
    
    return render_template('search.html',
                         query=query,
                         products=pagination.items,
                         pagination=pagination,
                         categories=categories,
                         total_results=pagination.total,
                         selected_category=category_id,
                         sort=sort,
                         title=f'Search Results for "{query}"')

@main_bp.route('/request-return', methods=['POST'])
def request_return():
    """Submit return request"""
    order_number = request.form.get('order_number')
    phone = request.form.get('phone')
    email = request.form.get('email')
    product_id = request.form.get('product_id')
    reason = request.form.get('reason')
    comments = request.form.get('comments')
    
    # Here you would process the return request
    # For now, just flash a success message
    
    flash('Your return request has been submitted. We\'ll contact you shortly via WhatsApp.', 'success')
    return redirect(url_for('main.returns'))

# Error handlers
@main_bp.app_errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@main_bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

# Context processor to inject cart and wishlist counts
@main_bp.context_processor
def inject_counts():
    """Inject cart and wishlist counts into all templates"""
    cart_count = session.get('cart_count', 0)
    wishlist_count = session.get('wishlist_count', 0)
    return dict(cart_count=cart_count, wishlist_count=wishlist_count)