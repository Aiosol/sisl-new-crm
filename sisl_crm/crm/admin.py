# admin.py - SISL CRM Django Admin Configuration
# Complete admin interface for managing CRM data

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Sum, Q
from django.contrib.admin import SimpleListFilter
from datetime import datetime, timedelta
from .models import (
    # Choice Models
    ContactStatus, Designation, Industry, StakeholderType, Zone,
    LeadSource, LeadStatus, ProductCategory, Brand,
    # Core Models
    Company, Contact, ContactCompanyHistory, Stakeholder,
    Product, Lead, LeadProduct, Activity, AuditLog, Document
)

# ============== CUSTOM FILTERS ==============

class LeadValueFilter(SimpleListFilter):
    title = 'Lead Value'
    parameter_name = 'value_range'
    
    def lookups(self, request, model_admin):
        return (
            ('0-100000', 'Below 1 Lakh'),
            ('100000-500000', '1-5 Lakhs'),
            ('500000-1000000', '5-10 Lakhs'),
            ('1000000-5000000', '10-50 Lakhs'),
            ('5000000+', 'Above 50 Lakhs'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == '0-100000':
            return queryset.filter(estimated_value__lt=100000)
        elif self.value() == '100000-500000':
            return queryset.filter(estimated_value__gte=100000, estimated_value__lt=500000)
        elif self.value() == '500000-1000000':
            return queryset.filter(estimated_value__gte=500000, estimated_value__lt=1000000)
        elif self.value() == '1000000-5000000':
            return queryset.filter(estimated_value__gte=1000000, estimated_value__lt=5000000)
        elif self.value() == '5000000+':
            return queryset.filter(estimated_value__gte=5000000)

class ActivityDueFilter(SimpleListFilter):
    title = 'Activity Due'
    parameter_name = 'due'
    
    def lookups(self, request, model_admin):
        return (
            ('overdue', 'Overdue'),
            ('today', 'Today'),
            ('tomorrow', 'Tomorrow'),
            ('week', 'This Week'),
            ('month', 'This Month'),
        )
    
    def queryset(self, request, queryset):
        from django.utils import timezone
        now = timezone.now()
        
        if self.value() == 'overdue':
            return queryset.filter(scheduled_date__lt=now, status='scheduled')
        elif self.value() == 'today':
            return queryset.filter(scheduled_date__date=now.date(), status='scheduled')
        elif self.value() == 'tomorrow':
            tomorrow = now + timedelta(days=1)
            return queryset.filter(scheduled_date__date=tomorrow.date(), status='scheduled')
        elif self.value() == 'week':
            week_end = now + timedelta(days=7)
            return queryset.filter(scheduled_date__gte=now, scheduled_date__lte=week_end, status='scheduled')
        elif self.value() == 'month':
            month_end = now + timedelta(days=30)
            return queryset.filter(scheduled_date__gte=now, scheduled_date__lte=month_end, status='scheduled')

# ============== INLINE ADMIN CLASSES ==============

class ContactCompanyHistoryInline(admin.TabularInline):
    model = ContactCompanyHistory
    extra = 0
    fields = ['company', 'designation', 'start_date', 'end_date', 'is_current']
    ordering = ['-is_current', '-start_date']

class LeadProductInline(admin.TabularInline):
    model = LeadProduct
    extra = 1
    fields = ['product', 'quantity', 'unit_price', 'total_price', 'custom_description']
    readonly_fields = ['total_price']
    autocomplete_fields = ['product']

class DocumentInline(admin.TabularInline):
    model = Document
    extra = 0
    fields = ['file', 'document_type', 'description']
    
class ActivityInline(admin.TabularInline):
    model = Activity
    extra = 0
    fields = ['activity_type', 'subject', 'scheduled_date', 'status', 'assigned_to']
    readonly_fields = ['status']

# ============== ADMIN CLASSES FOR CHOICE MODELS ==============

@admin.register(ContactStatus)
class ContactStatusAdmin(admin.ModelAdmin):
    list_display = ['name', 'color_display', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    ordering = ['order']
    search_fields = ['name']  
    
    def color_display(self, obj):
        return format_html(
            '<div style="background-color: {}; width: 50px; height: 20px; border-radius: 3px;"></div>',
            obj.color
        )
    color_display.short_description = 'Color'

@admin.register(Designation)
class DesignationAdmin(admin.ModelAdmin):
    list_display = ['name', 'department', 'level', 'is_active']
    list_filter = ['department', 'is_active']
    list_editable = ['level', 'is_active']
    search_fields = ['name', 'department']
    ordering = ['level', 'name']

@admin.register(Industry)
class IndustryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'is_active']
    list_editable = ['is_active']
    search_fields = ['name']
    ordering = ['name']

@admin.register(StakeholderType)
class StakeholderTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'color_display', 'description', 'is_active']
    list_editable = ['is_active']
    search_fields = ['name']
    
    def color_display(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 3px 10px; border-radius: 3px; color: white;">{}</span>',
            obj.color, obj.name
        )
    color_display.short_description = 'Preview'

@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active']
    list_editable = ['is_active']
    search_fields = ['name', 'code']
    ordering = ['name']

@admin.register(LeadSource)
class LeadSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'is_active']
    list_editable = ['is_active']
    search_fields = ['name']

@admin.register(LeadStatus)
class LeadStatusAdmin(admin.ModelAdmin):
    list_display = ['name', 'stage_order', 'color_display', 'is_won', 'is_lost', 'requires_approval', 'is_active']
    list_editable = ['stage_order', 'is_won', 'is_lost', 'requires_approval', 'is_active']
    ordering = ['stage_order']
    search_fields = ['name'] 
    
    def color_display(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 3px 10px; border-radius: 3px; color: white;">{}</span>',
            obj.color, obj.name
        )
    color_display.short_description = 'Status Display'

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'parent', 'is_active']
    list_filter = ['parent', 'is_active']
    list_editable = ['is_active']
    search_fields = ['name', 'code']
    ordering = ['parent__name', 'name']

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_mitsubishi', 'website', 'is_active']
    list_filter = ['is_mitsubishi', 'is_active']
    list_editable = ['is_mitsubishi', 'is_active']
    search_fields = ['name']

# ============== CORE MODEL ADMIN CLASSES ==============

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'industry', 'zone', 'company_size', 'contact_count', 'lead_count', 'created_at']
    list_filter = ['industry', 'zone', 'company_size', 'is_deleted']
    search_fields = ['name', 'email', 'phone']
    readonly_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'industry', 'website', 'phone', 'email')
        }),
        ('Address Information', {
            'fields': ('address', 'zone')
        }),
        ('Company Details', {
            'fields': ('company_size', 'annual_revenue', 'tax_id')
        }),
        ('Banking Information', {
            'fields': ('bank_name', 'bank_account', 'bank_branch'),
            'classes': ('collapse',)
        }),
        ('Additional', {
            'fields': ('notes',)
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            contact_count=Count('current_employees'),
            lead_count=Count('leads')
        )
    
    def contact_count(self, obj):
        return obj.contact_count
    contact_count.admin_order_field = 'contact_count'
    
    def lead_count(self, obj):
        return obj.lead_count
    lead_count.admin_order_field = 'lead_count'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'email', 'current_company', 'designation', 'status_badge', 'created_at']
    list_filter = ['status', 'contact_type', 'designation', 'product_interests', 'is_deleted']
    search_fields = ['name', 'phone', 'email', 'current_company__name']
    autocomplete_fields = ['current_company', 'designation', 'status']
    filter_horizontal = ['product_interests']
    readonly_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']
    inlines = [ContactCompanyHistoryInline, ActivityInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'phone', 'email', 'designation')
        }),
        ('Company & Type', {
            'fields': ('current_company', 'contact_type', 'status')
        }),
        ('Additional Information', {
            'fields': ('linkedin', 'address', 'product_interests', 'reference_source')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )
    
    def status_badge(self, obj):
        if obj.status:
            return format_html(
                '<span style="background-color: {}; padding: 3px 8px; border-radius: 3px; color: white;">{}</span>',
                obj.status.color, obj.status.name
            )
        return '-'
    status_badge.short_description = 'Status'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(Stakeholder)
class StakeholderAdmin(admin.ModelAdmin):
    list_display = ['contact_name', 'company_name', 'stakeholder_type', 'group_name', 'zone', 'created_at']
    list_filter = ['stakeholder_type', 'zone', 'is_deleted']
    search_fields = ['contact__name', 'company__name', 'group_name']
    autocomplete_fields = ['contact', 'company', 'stakeholder_type', 'zone']
    readonly_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']
    
    fieldsets = (
        ('Relationships', {
            'fields': ('contact', 'company', 'stakeholder_type', 'group_name')
        }),
        ('Contact Details', {
            'fields': ('zone', 'email', 'website', 'address')
        }),
        ('Banking', {
            'fields': ('bank_details',),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )
    
    def contact_name(self, obj):
        return obj.contact.name
    contact_name.admin_order_field = 'contact__name'
    
    def company_name(self, obj):
        return obj.company.name
    company_name.admin_order_field = 'company__name'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand', 'model', 'category', 'sku', 'price', 'stock_quantity', 'is_from_api', 'is_active']
    list_filter = ['brand', 'category', 'is_from_api', 'is_active', 'is_deleted']
    search_fields = ['name', 'model', 'sku', 'mitsubishi_api_id']
    autocomplete_fields = ['brand', 'category']
    readonly_fields = ['id', 'sku', 'created_at', 'updated_at', 'created_by', 'updated_by']
    
    fieldsets = (
        ('Product Information', {
            'fields': ('name', 'brand', 'model', 'capacity', 'category')
        }),
        ('Identification', {
            'fields': ('sku', 'mitsubishi_api_id', 'is_from_api')
        }),
        ('Details', {
            'fields': ('description', 'technical_specs')
        }),
        ('Pricing & Stock', {
            'fields': ('price', 'stock_quantity')
        }),
        ('Files', {
            'fields': ('image', 'datasheet')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['lead_number', 'title', 'contact', 'company', 'status_badge', 'value_display', 
                    'owner', 'approval_status', 'created_at']
    list_filter = ['status', 'source', 'rate_type', 'delivery_type', 'requires_approval', 
                   LeadValueFilter, 'owner', 'is_deleted']
    search_fields = ['lead_number', 'title', 'contact__name', 'company__name']
    autocomplete_fields = ['contact', 'company', 'stakeholder', 'status', 'source', 'owner']
    filter_horizontal = ['collaborators']
    readonly_fields = ['id', 'lead_number', 'weighted_value', 'approved_at', 'created_at', 
                       'updated_at', 'created_by', 'updated_by']
    inlines = [LeadProductInline, ActivityInline, DocumentInline]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Lead Information', {
            'fields': ('title', 'lead_number', 'contact', 'company', 'stakeholder')
        }),
        ('Status & Source', {
            'fields': ('source', 'status', 'rate_type')
        }),
        ('Value & Probability', {
            'fields': ('estimated_value', 'probability', 'weighted_value')
        }),
        ('Dates', {
            'fields': ('expected_close_date', 'actual_close_date')
        }),
        ('Assignment', {
            'fields': ('owner', 'collaborators')
        }),
        ('Delivery', {
            'fields': ('delivery_type', 'expected_delivery_date')
        }),
        ('Approval', {
            'fields': ('requires_approval', 'approved_by', 'approved_at', 'approval_notes'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['approve_leads', 'assign_to_me', 'mark_as_won', 'mark_as_lost']
    
    def status_badge(self, obj):
        if obj.status:
            return format_html(
                '<span style="background-color: {}; padding: 3px 8px; border-radius: 3px; color: white;">{}</span>',
                obj.status.color, obj.status.name
            )
        return '-'
    status_badge.short_description = 'Status'
    
    def value_display(self, obj):
        if obj.estimated_value:
            return f"৳ {obj.estimated_value:,.2f}"
        return '-'
    value_display.short_description = 'Est. Value'
    value_display.admin_order_field = 'estimated_value'
    
    def approval_status(self, obj):
        if not obj.requires_approval:
            return '-'
        if obj.approved_by:
            return format_html('<span style="color: green;">✓ Approved</span>')
        return format_html('<span style="color: orange;">⏳ Pending</span>')
    approval_status.short_description = 'Approval'
    
    def approve_leads(self, request, queryset):
        count = 0
        for lead in queryset.filter(requires_approval=True, approved_by__isnull=True):
            lead.approved_by = request.user
            lead.approved_at = timezone.now()
            lead.save()
            count += 1
        self.message_user(request, f"{count} lead(s) approved successfully.")
    approve_leads.short_description = "Approve selected leads"
    
    def assign_to_me(self, request, queryset):
        count = queryset.update(owner=request.user)
        self.message_user(request, f"{count} lead(s) assigned to you.")
    assign_to_me.short_description = "Assign to me"
    
    def mark_as_won(self, request, queryset):
        won_status = LeadStatus.objects.filter(is_won=True).first()
        if won_status:
            count = queryset.update(status=won_status, actual_close_date=timezone.now().date())
            self.message_user(request, f"{count} lead(s) marked as won.")
        else:
            self.message_user(request, "No 'Won' status configured. Please configure in Lead Status.", level='error')
    mark_as_won.short_description = "Mark as Won"
    
    def mark_as_lost(self, request, queryset):
        lost_status = LeadStatus.objects.filter(is_lost=True).first()
        if lost_status:
            count = queryset.update(status=lost_status, actual_close_date=timezone.now().date())
            self.message_user(request, f"{count} lead(s) marked as lost.")
        else:
            self.message_user(request, "No 'Lost' status configured. Please configure in Lead Status.", level='error')
    mark_as_lost.short_description = "Mark as Lost"
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Sales team can only see their own leads unless they have special permission
        if not request.user.has_perm('crm.can_view_all_leads') and not request.user.is_superuser:
            qs = qs.filter(Q(owner=request.user) | Q(collaborators=request.user)).distinct()
        return qs
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
            if not obj.owner:
                obj.owner = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['activity_type', 'subject', 'contact', 'lead', 'scheduled_date', 
                    'status_badge', 'priority_badge', 'assigned_to']
    list_filter = ['activity_type', 'status', 'priority', ActivityDueFilter, 'assigned_to']
    search_fields = ['subject', 'description', 'contact__name', 'lead__title']
    autocomplete_fields = ['contact', 'lead', 'assigned_to', 'completed_by']
    readonly_fields = ['id', 'completed_at', 'created_at', 'updated_at', 'created_by', 'updated_by']
    date_hierarchy = 'scheduled_date'
    
    fieldsets = (
        ('Activity Information', {
            'fields': ('activity_type', 'subject', 'description')
        }),
        ('Related To', {
            'fields': ('contact', 'lead')
        }),
        ('Schedule', {
            'fields': ('scheduled_date', 'duration', 'priority')
        }),
        ('Assignment & Status', {
            'fields': ('assigned_to', 'status')
        }),
        ('Completion', {
            'fields': ('completed_at', 'completed_by', 'outcome', 'next_action'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['mark_completed', 'assign_to_me']
    
    def status_badge(self, obj):
        colors = {
            'scheduled': '#3498db',
            'completed': '#27ae60',
            'cancelled': '#e74c3c',
            'rescheduled': '#f39c12'
        }
        return format_html(
            '<span style="background-color: {}; padding: 3px 8px; border-radius: 3px; color: white;">{}</span>',
            colors.get(obj.status, '#95a5a6'), obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def priority_badge(self, obj):
        colors = {
            'low': '#95a5a6',
            'medium': '#3498db',
            'high': '#f39c12',
            'urgent': '#e74c3c'
        }
        return format_html(
            '<span style="background-color: {}; padding: 3px 8px; border-radius: 3px; color: white;">{}</span>',
            colors.get(obj.priority, '#95a5a6'), obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'
    
    def mark_completed(self, request, queryset):
        from django.utils import timezone
        count = 0
        for activity in queryset.filter(status='scheduled'):
            activity.mark_complete(request.user)
            count += 1
        self.message_user(request, f"{count} activity(ies) marked as completed.")
    mark_completed.short_description = "Mark as completed"
    
    def assign_to_me(self, request, queryset):
        count = queryset.update(assigned_to=request.user)
        self.message_user(request, f"{count} activity(ies) assigned to you.")
    assign_to_me.short_description = "Assign to me"
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Filter based on user permissions
        if not request.user.is_superuser:
            qs = qs.filter(assigned_to=request.user)
        return qs
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
            if not obj.assigned_to:
                obj.assigned_to = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['change_type', 'model_name', 'object_id', 'field_name', 'changed_by', 'changed_at']
    list_filter = ['change_type', 'model_name', 'changed_at']
    search_fields = ['object_id', 'field_name', 'old_value', 'new_value']
    readonly_fields = ['id', 'model_name', 'object_id', 'field_name', 'old_value', 
                       'new_value', 'changed_by', 'changed_at', 'change_type', 'ip_address', 'user_agent']
    date_hierarchy = 'changed_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'document_type', 'file_type', 'file_size_display', 'get_related_object', 'created_at']
    list_filter = ['document_type', 'file_type', 'created_at']
    search_fields = ['file_name', 'description']
    readonly_fields = ['id', 'file_size', 'file_type', 'file_name', 'created_at', 'updated_at']
    
    fieldsets = (
        ('File Information', {
            'fields': ('file', 'file_name', 'file_type', 'file_size', 'document_type')
        }),
        ('Related To', {
            'fields': ('contact', 'company', 'lead', 'product')
        }),
        ('Description', {
            'fields': ('description',)
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def file_size_display(self, obj):
        if obj.file_size < 1024:
            return f"{obj.file_size} B"
        elif obj.file_size < 1024 * 1024:
            return f"{obj.file_size / 1024:.1f} KB"
        else:
            return f"{obj.file_size / (1024 * 1024):.1f} MB"
    file_size_display.short_description = 'Size'
    
    def get_related_object(self, obj):
        if obj.contact:
            return f"Contact: {obj.contact.name}"
        elif obj.company:
            return f"Company: {obj.company.name}"
        elif obj.lead:
            return f"Lead: {obj.lead.title}"
        elif obj.product:
            return f"Product: {obj.product.name}"
        return '-'
    get_related_object.short_description = 'Related To'

# ============== ADMIN SITE CUSTOMIZATION ==============

admin.site.site_header = "SISL CRM Administration"
admin.site.site_title = "SISL CRM"
admin.site.index_title = "Welcome to SISL CRM Management System"