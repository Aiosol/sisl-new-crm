# models.py - SISL CRM Django Models
# Industrial Automation CRM System with Mitsubishi Integration

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.utils import timezone
import uuid
from django.core.exceptions import ValidationError

# ============== ABSTRACT BASE MODELS ==============

class TimestampedModel(models.Model):
    """Abstract model for tracking creation and updates"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, 
        related_name='%(class)s_created',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    updated_by = models.ForeignKey(
        User,
        related_name='%(class)s_updated',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    class Meta:
        abstract = True

class SoftDeleteModel(models.Model):
    """Abstract model for soft delete functionality"""
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        User,
        related_name='%(class)s_deleted',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    def soft_delete(self, user=None):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save()
    
    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save()
    
    class Meta:
        abstract = True

# ============== CHOICE FIELDS (Admin Managed) ==============

class ContactStatus(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=20, default='gray')
    order = models.IntegerField(default=0, help_text="Order for display in dropdowns")  # <-- add this
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Designation(models.Model):
    """Admin-managed designations"""
    name = models.CharField(max_length=100, unique=True)
    department = models.CharField(max_length=100, blank=True)
    level = models.IntegerField(default=0, help_text='Seniority level')
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['level', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.department})" if self.department else self.name

class Industry(models.Model):
    """Admin-managed industries"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = 'Industries'
        ordering = ['name']
    
    def __str__(self):
        return self.name

class StakeholderType(models.Model):
    """Admin-managed stakeholder types"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#000000')
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Zone(models.Model):
    """Admin-managed zones/regions"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"

class LeadSource(models.Model):
    """Admin-managed lead sources"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name

class LeadStatus(models.Model):
    """Admin-managed lead statuses with pipeline order"""
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, default='#000000')
    stage_order = models.IntegerField(default=0, help_text='Order in pipeline')
    is_won = models.BooleanField(default=False)
    is_lost = models.BooleanField(default=False)
    requires_approval = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['stage_order']
        verbose_name_plural = 'Lead Statuses'
    
    def __str__(self):
        return self.name

class ProductCategory(models.Model):
    """Admin-managed product categories"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = 'Product Categories'
        ordering = ['name']
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

# ============== CORE BUSINESS MODELS ==============

class Company(TimestampedModel, SoftDeleteModel):
    """Company/Organization model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    industry = models.ForeignKey(Industry, on_delete=models.SET_NULL, null=True, blank=True)
    website = models.URLField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    zone = models.ForeignKey(Zone, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Additional Information
    company_size = models.CharField(max_length=50, blank=True, choices=[
        ('1-10', '1-10 employees'),
        ('11-50', '11-50 employees'),
        ('51-200', '51-200 employees'),
        ('201-500', '201-500 employees'),
        ('500+', '500+ employees'),
    ])
    annual_revenue = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    
    # Banking Information
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account = models.CharField(max_length=50, blank=True)
    bank_branch = models.CharField(max_length=100, blank=True)
    
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = 'Companies'
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Contact(TimestampedModel, SoftDeleteModel):
    """Individual contact model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic Information
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, db_index=True)
    email = models.EmailField(blank=True, db_index=True)
    designation = models.ForeignKey(Designation, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Company Relationship (Current)
    current_company = models.ForeignKey(
        Company, 
        related_name='current_employees',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Contact Type & Status
    contact_type = models.CharField(max_length=50, choices=[
        ('head_office', 'Head Office'),
        ('factory', 'Factory'),
        ('branch', 'Branch Office'),
    ], default='head_office')
    
    status = models.ForeignKey(ContactStatus, on_delete=models.SET_NULL, null=True)
    
    # Additional Information
    linkedin = models.URLField(blank=True)
    address = models.TextField(blank=True)
    
    # Product Interest (Multiple Selection)
    product_interests = models.ManyToManyField(ProductCategory, blank=True)
    
    # Reference/Source
    reference_source = models.CharField(max_length=255, blank=True)
    
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['phone']),
            models.Index(fields=['email']),
            models.Index(fields=['current_company', 'name']),
        ]
    
    def __str__(self):
        if self.current_company:
            return f"{self.name} ({self.current_company.name})"
        return self.name
    
    def get_full_designation(self):
        if self.designation and self.current_company:
            return f"{self.designation} at {self.current_company}"
        return self.designation or "N/A"

class ContactCompanyHistory(TimestampedModel):
    """Track contact's company history"""
    contact = models.ForeignKey(Contact, related_name='company_history', on_delete=models.CASCADE)
    company = models.ForeignKey(Company, related_name='employee_history', on_delete=models.CASCADE)
    designation = models.ForeignKey(Designation, on_delete=models.SET_NULL, null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = 'Contact Company Histories'
        ordering = ['-is_current', '-start_date']
    
    def __str__(self):
        return f"{self.contact.name} at {self.company.name}"

class Stakeholder(TimestampedModel, SoftDeleteModel):
    """Stakeholder linking contacts to companies with specific roles"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Links
    contact = models.ForeignKey(Contact, related_name='stakeholder_roles', on_delete=models.CASCADE)
    company = models.ForeignKey(Company, related_name='stakeholders', on_delete=models.CASCADE)
    
    # Stakeholder Information
    stakeholder_type = models.ForeignKey(StakeholderType, on_delete=models.SET_NULL, null=True)
    group_name = models.CharField(max_length=255, blank=True, help_text='e.g., ACI Ltd.')
    
    # Contact Details (stakeholder-specific)
    zone = models.ForeignKey(Zone, on_delete=models.SET_NULL, null=True, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    address = models.TextField(blank=True)
    
    # Banking (stakeholder-specific)
    bank_details = models.TextField(blank=True)
    
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['contact', 'company', 'stakeholder_type']
        ordering = ['company', 'stakeholder_type']
    
    def __str__(self):
        return f"{self.contact.name} - {self.stakeholder_type} at {self.company.name}"

# ============== PRODUCT MODELS ==============

class Brand(TimestampedModel):
    """Product brands"""
    name = models.CharField(max_length=100, unique=True)
    is_mitsubishi = models.BooleanField(default=False)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-is_mitsubishi', 'name']
    
    def __str__(self):
        return self.name

class Product(TimestampedModel, SoftDeleteModel):
    """Product master - both Mitsubishi (API) and Others (manual)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Product Information
    name = models.CharField(max_length=255)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    model = models.CharField(max_length=100, blank=True)
    capacity = models.CharField(max_length=100, blank=True)
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, blank=True)
    
    # SKU and API Reference
    sku = models.CharField(max_length=100, unique=True, null=True, blank=True)
    mitsubishi_api_id = models.CharField(max_length=100, blank=True, db_index=True, 
                                          help_text='ID from Mitsubishi API')
    
    # Specifications
    technical_specs = models.JSONField(default=dict, blank=True)
    description = models.TextField(blank=True)
    
    # Pricing and Stock
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    stock_quantity = models.IntegerField(default=0)
    
    # Files
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    datasheet = models.FileField(upload_to='products/datasheets/', blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_from_api = models.BooleanField(default=False, help_text='Fetched from Mitsubishi API')
    
    class Meta:
        ordering = ['brand', 'name']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['mitsubishi_api_id']),
        ]
    
    def __str__(self):
        return f"{self.brand.name} - {self.name} ({self.model})" if self.model else f"{self.brand.name} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.sku and not self.is_from_api:
            # Generate SKU for manually added products
            self.sku = f"{self.brand.name[:3].upper()}-{self.model or 'XXX'}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

# ============== LEAD MANAGEMENT ==============

class Lead(TimestampedModel, SoftDeleteModel):
    """Lead/Opportunity model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic Information
    title = models.CharField(max_length=255, help_text='e.g., PLC System for Textile Mill')
    lead_number = models.CharField(max_length=50, unique=True, editable=False)
    
    # Relationships
    contact = models.ForeignKey(Contact, related_name='leads', on_delete=models.CASCADE)
    company = models.ForeignKey(Company, related_name='leads', on_delete=models.SET_NULL, null=True, blank=True)
    stakeholder = models.ForeignKey(Stakeholder, related_name='leads', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Lead Information
    source = models.ForeignKey(LeadSource, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.ForeignKey(LeadStatus, on_delete=models.SET_NULL, null=True)
    
    # Value and Probability
    estimated_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    probability = models.IntegerField(default=0, help_text='Probability percentage (0-100)')
    weighted_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, editable=False)
    
    # Dates
    expected_close_date = models.DateField(null=True, blank=True)
    actual_close_date = models.DateField(null=True, blank=True)
    
    # Assignment and Collaboration
    owner = models.ForeignKey(User, related_name='owned_leads', on_delete=models.SET_NULL, null=True)
    collaborators = models.ManyToManyField(User, related_name='collaborated_leads', blank=True)
    
    # Rate Type
    rate_type = models.CharField(max_length=20, choices=[
        ('proposed', 'Proposed'),
        ('final', 'Final'),
    ], default='proposed')
    
    # Delivery Information
    delivery_type = models.CharField(max_length=50, choices=[
        ('installation', 'Installation & Commissioning'),
        ('delivery_only', 'Product Delivery Only'),
        ('with_training', 'With Training'),
    ], blank=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    
    # Approval
    requires_approval = models.BooleanField(default=False)
    approved_by = models.ForeignKey(User, related_name='approved_leads', on_delete=models.SET_NULL, null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_notes = models.TextField(blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['lead_number']),
            models.Index(fields=['status', 'owner']),
            models.Index(fields=['expected_close_date']),
        ]
        permissions = [
            ('can_approve_leads', 'Can approve leads'),
            ('can_view_all_leads', 'Can view all leads'),
        ]
    
    def __str__(self):
        return f"{self.lead_number} - {self.title}"
    
    def save(self, *args, **kwargs):
        if not self.lead_number:
            # Generate lead number: LEAD-YYYYMM-XXXX
            today = timezone.now()
            prefix = f"LEAD-{today.strftime('%Y%m')}"
            last_lead = Lead.objects.filter(lead_number__startswith=prefix).order_by('-lead_number').first()
            if last_lead:
                last_number = int(last_lead.lead_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            self.lead_number = f"{prefix}-{new_number:04d}"
        
        # Calculate weighted value
        if self.estimated_value and self.probability:
            self.weighted_value = self.estimated_value * (self.probability / 100)
        
        # Check if approval required based on status
        if self.status and self.status.requires_approval:
            self.requires_approval = True
        
        super().save(*args, **kwargs)

class LeadProduct(TimestampedModel):
    """Products associated with a lead (many-to-many with extra fields)"""
    lead = models.ForeignKey(Lead, related_name='lead_products', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='lead_items', on_delete=models.CASCADE)
    
    # Quantity and Pricing
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, editable=False)
    
    # For non-catalog products
    custom_description = models.TextField(blank=True, help_text='For products not in catalog')
    
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['lead', 'product']
        ordering = ['product__name']
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity} for {self.lead.title}"
    
    def save(self, *args, **kwargs):
        if self.unit_price and self.quantity:
            self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)

# ============== ACTIVITY TRACKING ==============

class Activity(TimestampedModel):
    """Activity/Task tracking for leads and contacts"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Activity Type
    activity_type = models.CharField(max_length=50, choices=[
        ('call', 'Phone Call'),
        ('email', 'Email'),
        ('meeting', 'Meeting'),
        ('site_visit', 'Site Visit'),
        ('demo', 'Product Demo'),
        ('follow_up', 'Follow Up'),
        ('quotation', 'Quotation Sent'),
        ('negotiation', 'Negotiation'),
        ('other', 'Other'),
    ])
    
    # Subject and Description
    subject = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Relationships
    contact = models.ForeignKey(Contact, related_name='activities', on_delete=models.CASCADE, null=True, blank=True)
    lead = models.ForeignKey(Lead, related_name='activities', on_delete=models.CASCADE, null=True, blank=True)
    
    # Scheduling
    scheduled_date = models.DateTimeField()
    duration = models.IntegerField(default=30, help_text='Duration in minutes')
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rescheduled', 'Rescheduled'),
    ], default='scheduled')
    
    # Assignment
    assigned_to = models.ForeignKey(User, related_name='assigned_activities', on_delete=models.SET_NULL, null=True)
    
    # Outcome
    outcome = models.TextField(blank=True, help_text='Result of the activity')
    next_action = models.TextField(blank=True, help_text='Recommended next steps')
    
    # Priority
    priority = models.CharField(max_length=20, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], default='medium')
    
    # Completion
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(User, related_name='completed_activities', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name_plural = 'Activities'
        ordering = ['-scheduled_date']
        indexes = [
            models.Index(fields=['status', 'assigned_to']),
            models.Index(fields=['scheduled_date']),
        ]
    
    def __str__(self):
        return f"{self.activity_type} - {self.subject}"
    
    def mark_complete(self, user, outcome=''):
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.completed_by = user
        if outcome:
            self.outcome = outcome
        self.save()

# ============== AUDIT LOG ==============

class AuditLog(models.Model):
    """Track all changes to important models"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # What changed
    model_name = models.CharField(max_length=50)
    object_id = models.CharField(max_length=50)
    field_name = models.CharField(max_length=50)
    
    # Change details
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    
    # Who and When
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    
    # Change type
    change_type = models.CharField(max_length=20, choices=[
        ('create', 'Created'),
        ('update', 'Updated'),
        ('delete', 'Deleted'),
        ('restore', 'Restored'),
    ])
    
    # Additional context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['changed_at']),
        ]
    
    def __str__(self):
        return f"{self.change_type} {self.model_name} {self.object_id} by {self.changed_by}"

# ============== DOCUMENT ATTACHMENTS ==============

class Document(TimestampedModel):
    """File attachments for any model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # File Information
    file = models.FileField(upload_to='documents/%Y/%m/')
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    file_size = models.IntegerField(help_text='Size in bytes')
    
    # Relationships (Generic - can be attached to any model)
    contact = models.ForeignKey(Contact, related_name='documents', on_delete=models.CASCADE, null=True, blank=True)
    company = models.ForeignKey(Company, related_name='documents', on_delete=models.CASCADE, null=True, blank=True)
    lead = models.ForeignKey(Lead, related_name='documents', on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey(Product, related_name='documents', on_delete=models.CASCADE, null=True, blank=True)
    
    # Document Type
    document_type = models.CharField(max_length=50, choices=[
        ('quotation', 'Quotation'),
        ('invoice', 'Invoice'),
        ('po', 'Purchase Order'),
        ('contract', 'Contract'),
        ('technical', 'Technical Document'),
        ('presentation', 'Presentation'),
        ('other', 'Other'),
    ], default='other')
    
    description = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.file_name
    
    def save(self, *args, **kwargs):
        if self.file:
            self.file_name = self.file.name
            self.file_size = self.file.size
            self.file_type = self.file.name.split('.')[-1].upper()
        super().save(*args, **kwargs)