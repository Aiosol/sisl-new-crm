# crm/signals.py - Django Signals for Audit Logging

from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import (
    Contact, Company, Lead, Activity, 
    ContactCompanyHistory, LeadStatus
)
from .utils import log_audit_trail

# Track field changes
def track_field_changes(sender, instance, **kwargs):
    """Track which fields changed"""
    if not instance.pk:
        return None
    
    try:
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return None
    
    changed_fields = []
    for field in instance._meta.fields:
        field_name = field.name
        old_value = getattr(old_instance, field_name)
        new_value = getattr(instance, field_name)
        
        if old_value != new_value:
            changed_fields.append({
                'field': field_name,
                'old_value': old_value,
                'new_value': new_value
            })
    
    return changed_fields

# Contact signals
@receiver(pre_save, sender=Contact)
def contact_pre_save(sender, instance, **kwargs):
    """Track contact changes before save"""
    if instance.pk:
        instance._changed_fields = track_field_changes(sender, instance)

@receiver(post_save, sender=Contact)
def contact_post_save(sender, instance, created, **kwargs):
    """Log contact changes after save"""
    user = getattr(instance, 'updated_by', None) or getattr(instance, 'created_by', None)
    
    if created:
        log_audit_trail(
            'Contact', instance.id, 'create',
            None, None, None, user
        )
    elif hasattr(instance, '_changed_fields') and instance._changed_fields:
        for change in instance._changed_fields:
            log_audit_trail(
                'Contact', instance.id, 'update',
                change['field'], change['old_value'], change['new_value'], user
            )

# Company signals
@receiver(pre_save, sender=Company)
def company_pre_save(sender, instance, **kwargs):
    """Track company changes before save"""
    if instance.pk:
        instance._changed_fields = track_field_changes(sender, instance)

@receiver(post_save, sender=Company)
def company_post_save(sender, instance, created, **kwargs):
    """Log company changes after save"""
    user = getattr(instance, 'updated_by', None) or getattr(instance, 'created_by', None)
    
    if created:
        log_audit_trail(
            'Company', instance.id, 'create',
            None, None, None, user
        )
    elif hasattr(instance, '_changed_fields') and instance._changed_fields:
        for change in instance._changed_fields:
            log_audit_trail(
                'Company', instance.id, 'update',
                change['field'], change['old_value'], change['new_value'], user
            )

# Lead signals
@receiver(pre_save, sender=Lead)
def lead_pre_save(sender, instance, **kwargs):
    """Track lead changes and handle approval requirements"""
    if instance.pk:
        instance._changed_fields = track_field_changes(sender, instance)
        
        # Check if status changed to one requiring approval
        old_lead = Lead.objects.get(pk=instance.pk)
        if instance.status != old_lead.status and instance.status and instance.status.requires_approval:
            instance.requires_approval = True
            # Reset approval if status changed
            if old_lead.approved_by:
                instance.approved_by = None
                instance.approved_at = None

@receiver(post_save, sender=Lead)
def lead_post_save(sender, instance, created, **kwargs):
    """Log lead changes and send notifications"""
    user = getattr(instance, 'updated_by', None) or getattr(instance, 'created_by', None)
    
    if created:
        log_audit_trail(
            'Lead', instance.id, 'create',
            None, None, None, user
        )
        
        # Send notification to owner
        if instance.owner and instance.owner.email:
            from .utils import send_notification_email
            try:
                send_notification_email(
                    subject=f'New Lead Assigned: {instance.lead_number}',
                    template_name='emails/lead_assigned.html',
                    context={'lead': instance},
                    recipient_list=[instance.owner.email]
                )
            except:
                pass  # Don't break on email errors
                
    elif hasattr(instance, '_changed_fields') and instance._changed_fields:
        for change in instance._changed_fields:
            log_audit_trail(
                'Lead', instance.id, 'update',
                change['field'], change['old_value'], change['new_value'], user
            )
        
        # Check if approval is needed
        if instance.requires_approval and not instance.approved_by:
            # Notify managers
            managers = User.objects.filter(
                groups__permissions__codename='can_approve_leads'
            ).distinct()
            
            if managers:
                from .utils import send_notification_email
                try:
                    send_notification_email(
                        subject=f'Lead Approval Required: {instance.lead_number}',
                        template_name='emails/lead_approval_required.html',
                        context={'lead': instance},
                        recipient_list=list(managers.values_list('email', flat=True))
                    )
                except:
                    pass

# Activity signals
@receiver(post_save, sender=Activity)
def activity_post_save(sender, instance, created, **kwargs):
    """Send reminders for new activities"""
    if created and instance.assigned_to and instance.assigned_to.email:
        from .utils import send_notification_email, get_activity_reminder_time
        
        try:
            send_notification_email(
                subject=f'New Activity: {instance.subject}',
                template_name='emails/activity_assigned.html',
                context={'activity': instance},
                recipient_list=[instance.assigned_to.email]
            )
        except:
            pass
        
        # Schedule reminder (would need Celery in production)
        # reminder_time = get_activity_reminder_time(instance.scheduled_date, instance.priority)
        # schedule_activity_reminder.apply_async(args=[instance.id], eta=reminder_time)

# Contact Company History signals
@receiver(post_save, sender=ContactCompanyHistory)
def contact_company_history_post_save(sender, instance, created, **kwargs):
    """Update contact's current company when history changes"""
    if instance.is_current:
        # Set all other histories as not current
        ContactCompanyHistory.objects.filter(
            contact=instance.contact
        ).exclude(pk=instance.pk).update(is_current=False)
        
        # Update contact's current company
        instance.contact.current_company = instance.company
        instance.contact.designation = instance.designation
        instance.contact.save()

# Soft delete signal
@receiver(post_save)
def handle_soft_delete(sender, instance, **kwargs):
    """Log soft deletes"""
    if hasattr(instance, 'is_deleted') and hasattr(instance, 'deleted_by'):
        if instance.is_deleted and instance.deleted_by:
            log_audit_trail(
                sender.__name__, instance.id, 'delete',
                None, None, None, instance.deleted_by
            )