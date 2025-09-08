# utils.py - SISL CRM Utility Functions

from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import csv
import io
from datetime import datetime, timedelta

def log_audit_trail(model_name, object_id, change_type, field_name=None, old_value=None, 
                   new_value=None, user=None, request=None):
    """Log changes to audit trail"""
    from .models import AuditLog
    
    audit_log = AuditLog(
        model_name=model_name,
        object_id=str(object_id),
        change_type=change_type,
        field_name=field_name or '',
        old_value=str(old_value) if old_value is not None else '',
        new_value=str(new_value) if new_value is not None else '',
        changed_by=user
    )
    
    if request:
        # Get IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        audit_log.ip_address = ip
        
        # Get user agent
        audit_log.user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
    
    audit_log.save()

def send_notification_email(subject, template_name, context, recipient_list):
    """Send notification emails"""
    html_message = render_to_string(template_name, context)
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipient_list,
        html_message=html_message,
        fail_silently=False,
    )

def generate_csv_report(queryset, fields, filename):
    """Generate CSV report from queryset"""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    
    for obj in queryset:
        row = {}
        for field in fields:
            # Handle nested fields
            if '__' in field:
                parts = field.split('__')
                value = obj
                for part in parts:
                    value = getattr(value, part, None)
                    if value is None:
                        break
                row[field] = value or ''
            else:
                row[field] = getattr(obj, field, '')
        writer.writerow(row)
    
    output.seek(0)
    return output.getvalue(), f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

def calculate_commission(lead_value, commission_rate=0.02):
    """Calculate commission for sales team"""
    if lead_value:
        return float(lead_value) * commission_rate
    return 0

def format_currency(amount, currency='BDT'):
    """Format currency for display"""
    if amount is None:
        return f"{currency} 0.00"
    return f"{currency} {amount:,.2f}"

def get_quarter_dates(quarter=None, year=None):
    """Get start and end dates for a quarter"""
    if not year:
        year = datetime.now().year
    if not quarter:
        # Determine current quarter
        month = datetime.now().month
        quarter = (month - 1) // 3 + 1
    
    quarters = {
        1: (datetime(year, 1, 1), datetime(year, 3, 31)),
        2: (datetime(year, 4, 1), datetime(year, 6, 30)),
        3: (datetime(year, 7, 1), datetime(year, 9, 30)),
        4: (datetime(year, 10, 1), datetime(year, 12, 31)),
    }
    
    return quarters.get(quarter)

def validate_bangladesh_phone(phone):
    """Validate Bangladesh phone number"""
    import re
    
    # Remove spaces, dashes, and other common separators
    cleaned_phone = re.sub(r'[\s\-\(\)]', '', phone)
    
    # Check if it starts with +880 or 880
    if cleaned_phone.startswith('+880'):
        cleaned_phone = cleaned_phone[4:]
    elif cleaned_phone.startswith('880'):
        cleaned_phone = cleaned_phone[3:]
    elif cleaned_phone.startswith('0'):
        cleaned_phone = cleaned_phone[1:]
    
    # Should be 10 digits after country code
    if len(cleaned_phone) == 10 and cleaned_phone.isdigit():
        # Valid prefixes for BD mobile numbers
        valid_prefixes = ['13', '14', '15', '16', '17', '18', '19']
        if cleaned_phone[:2] in valid_prefixes:
            return f"+880{cleaned_phone}"
    
    return None

def get_activity_reminder_time(activity_date, priority):
    """Calculate when to send reminder for an activity"""
    reminder_times = {
        'urgent': timedelta(hours=1),
        'high': timedelta(hours=2),
        'medium': timedelta(hours=4),
        'low': timedelta(days=1),
    }
    
    reminder_delta = reminder_times.get(priority, timedelta(hours=2))
    return activity_date - reminder_delta

def parse_mitsubishi_product_code(code):
    """Parse Mitsubishi product code to extract model info"""
    # Example: FX5U-32MR/ES -> {'series': 'FX5U', 'points': '32', 'type': 'MR', 'suffix': 'ES'}
    import re
    
    pattern = r'([A-Z0-9]+)-(\d+)([A-Z]+)(?:/([A-Z]+))?'
    match = re.match(pattern, code)
    
    if match:
        return {
            'series': match.group(1),
            'points': match.group(2),
            'type': match.group(3),
            'suffix': match.group(4) or ''
        }
    return None

def calculate_lead_score(lead):
    """Calculate a score for lead prioritization"""
    score = 0
    
    # Value-based scoring
    if lead.estimated_value:
        if lead.estimated_value > 5000000:  # Above 50 lakhs
            score += 50
        elif lead.estimated_value > 1000000:  # Above 10 lakhs
            score += 30
        elif lead.estimated_value > 500000:  # Above 5 lakhs
            score += 20
        else:
            score += 10
    
    # Probability scoring
    score += (lead.probability or 0) * 0.3
    
    # Stage scoring
    if lead.status:
        if lead.status.is_won:
            score += 100
        elif lead.status.stage_order >= 3:  # Later stages
            score += 20
    
    # Time-based scoring (urgency)
    if lead.expected_close_date:
        days_to_close = (lead.expected_close_date - datetime.now().date()).days
        if days_to_close <= 7:
            score += 20
        elif days_to_close <= 30:
            score += 10
    
    # Activity scoring
    recent_activities = lead.activities.filter(
        created_at__gte=datetime.now() - timedelta(days=7)
    ).count()
    score += min(recent_activities * 5, 20)  # Max 20 points for activities
    
    return round(score)

def get_fiscal_year_dates(date=None):
    """Get fiscal year start and end dates (July-June for Bangladesh)"""
    if not date:
        date = datetime.now()
    
    if date.month >= 7:
        start_date = datetime(date.year, 7, 1)
        end_date = datetime(date.year + 1, 6, 30)
    else:
        start_date = datetime(date.year - 1, 7, 1)
        end_date = datetime(date.year, 6, 30)
    
    return start_date.date(), end_date.date()

def sanitize_filename(filename):
    """Sanitize filename for safe storage"""
    import re
    import unicodedata
    
    # Normalize unicode characters
    filename = unicodedata.normalize('NFKD', filename)
    filename = filename.encode('ascii', 'ignore').decode('ascii')
    
    # Remove non-alphanumeric characters except dots and dashes
    filename = re.sub(r'[^\w\s.-]', '', filename)
    filename = re.sub(r'[\s]+', '_', filename)
    
    # Limit length
    name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
    if len(name) > 100:
        name = name[:100]
    
    return f"{name}.{ext}" if ext else name