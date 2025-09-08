# crm/validators.py - Custom validators for CRM fields

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
import re

# Phone number validator for Bangladesh
bangladesh_phone_validator = RegexValidator(
    regex=r'^\+?880?[1-9]\d{8,9}$',
    message='Enter a valid Bangladesh phone number.'
)

def validate_phone_number(value):
    """Validate Bangladesh phone numbers with various formats"""
    # Remove spaces, dashes, parentheses
    cleaned = re.sub(r'[\s\-\(\)]', '', value)
    
    # Check various formats
    patterns = [
        r'^\+8801[3-9]\d{8}$',  # +8801XXXXXXXXX
        r'^8801[3-9]\d{8}$',     # 8801XXXXXXXXX  
        r'^01[3-9]\d{8}$',       # 01XXXXXXXXX
        r'^1[3-9]\d{8}$'         # 1XXXXXXXXX
    ]
    
    if not any(re.match(pattern, cleaned) for pattern in patterns):
        raise ValidationError('Enter a valid Bangladesh mobile number.')
    
    return cleaned

def validate_positive_number(value):
    """Ensure number is positive"""
    if value <= 0:
        raise ValidationError('Value must be greater than zero.')

def validate_percentage(value):
    """Validate percentage between 0 and 100"""
    if value < 0 or value > 100:
        raise ValidationError('Percentage must be between 0 and 100.')

def validate_file_size(file):
    """Validate file size (max 10MB)"""
    file_size = file.size
    limit_mb = 10
    if file_size > limit_mb * 1024 * 1024:
        raise ValidationError(f'File size cannot exceed {limit_mb}MB.')

def validate_file_extension(file):
    """Validate allowed file extensions"""
    allowed_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.png', '.jpg', '.jpeg', '.txt']
    file_name = file.name.lower()
    
    if not any(file_name.endswith(ext) for ext in allowed_extensions):
        raise ValidationError(
            f'File type not allowed. Allowed types: {", ".join(allowed_extensions)}'
        )