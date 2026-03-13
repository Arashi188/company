"""
Utility functions module
"""
import os
import secrets
from PIL import Image
from flask import current_app
from werkzeug.utils import secure_filename
import bleach

def save_image(file):
    """
    Save uploaded image with optimization
    
    Args:
        file: FileStorage object
        
    Returns:
        str: Filename of saved image
    """
    # Generate secure filename
    filename = secure_filename(file.filename)
    # Add random string to prevent filename collisions
    random_hex = secrets.token_hex(8)
    filename = f"{random_hex}_{filename}"
    
    # Save path
    upload_path = os.path.join(current_app.root_path, 'static/uploads')
    filepath = os.path.join(upload_path, filename)
    
    # Open and optimize image
    image = Image.open(file)
    
    # Convert RGBA to RGB if necessary
    if image.mode in ('RGBA', 'P'):
        image = image.convert('RGB')
    
    # Resize if too large (max 1200px width)
    max_size = (1200, 1200)
    image.thumbnail(max_size, Image.Resampling.LANCZOS)
    
    # Save with optimization
    image.save(filepath, optimize=True, quality=85)
    
    return filename

def sanitize_html(text):
    """
    Sanitize HTML content
    
    Args:
        text: HTML text to sanitize
        
    Returns:
        str: Sanitized HTML
    """
    allowed_tags = [
        'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'span', 'div'
    ]
    allowed_attributes = {
        '*': ['class', 'style']
    }
    return bleach.clean(text, tags=allowed_tags, attributes=allowed_attributes)

def format_whatsapp_url(phone_number, message):
    """
    Format WhatsApp URL with message
    
    Args:
        phone_number: WhatsApp phone number
        message: Message to send
        
    Returns:
        str: WhatsApp URL
    """
    from urllib.parse import quote
    encoded_message = quote(message)
    return f"https://wa.me/{phone_number}?text={encoded_message}"