# crm/templatetags/crm_tags.py - Custom template tags for CRM

from django import template
from django.utils.html import format_html

register = template.Library()

@register.filter
def currency_format(value, currency='৳'):
    """Format currency values"""
    try:
        value = float(value)
        return format_html("{} {:,.0f}", currency, value)
    except (ValueError, TypeError):
        return "-"

@register.filter
def percentage(value):
    """Format percentage values"""
    try:
        value = float(value)
        return f"{value:.0f}%"
    except (ValueError, TypeError):
        return "0%"

@register.simple_tag
def status_badge(status):
    """Render a status badge with color"""
    if not status:
        return ""
    
    return format_html(
        '<span class="badge" style="background-color: {};">{}</span>',
        status.color,
        status.name
    )

@register.filter
def has_group(user, group_name):
    """Check if user belongs to a group"""
    return user.groups.filter(name=group_name).exists()

@register.filter
def multiply(value, arg):
    """Multiply filter"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0