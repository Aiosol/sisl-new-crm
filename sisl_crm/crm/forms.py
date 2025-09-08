# forms.py - SISL CRM Django Forms
# Form classes with validation for CRM data entry


from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.contrib.auth.models import User
from .models import (
    Contact, Company, Stakeholder, Lead, LeadProduct, 
    Product, Activity, Document, ContactStatus, LeadStatus
)

# ============== CUSTOM WIDGETS ==============

class Select2Widget(forms.Select):
    """Custom widget for select2 dropdowns"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs['class'] = 'select2-dropdown'
        self.attrs['data-placeholder'] = 'Select an option'

class Select2MultipleWidget(forms.SelectMultiple):
    """Custom widget for select2 multiple selection"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs['class'] = 'select2-multiple'
        self.attrs['data-placeholder'] = 'Select options'

# ============== CONTACT FORMS ==============

class ContactForm(forms.ModelForm):
    """Form for creating/editing contacts"""
    
    class Meta:
        model = Contact
        fields = [
            'name', 'phone', 'email', 'designation', 'current_company',
            'contact_type', 'status', 'linkedin', 'address',
            'product_interests', 'reference_source', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter full name',
                'required': True
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+880...',
                'required': True
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@example.com'
            }),
            'designation': Select2Widget(),
            'current_company': Select2Widget(),
            'contact_type': forms.Select(attrs={'class': 'form-control'}),
            'status': Select2Widget(),
            'linkedin': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://linkedin.com/in/...'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter address'
            }),
            'product_interests': Select2MultipleWidget(),
            'reference_source': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'How did they hear about SISL?'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Additional notes...'
            })
        }
    
    def clean_phone(self):
        """Validate phone number"""
        phone = self.cleaned_data.get('phone')
        if phone:
            # Remove spaces and dashes
            phone = phone.replace(' ', '').replace('-', '')
            # Check if it's a valid BD number (optional)
            if not phone.startswith('+'):
                phone = '+880' + phone.lstrip('0')
        return phone
    
    def clean_email(self):
        """Validate email uniqueness if needed"""
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower()
        return email
    
    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        phone = cleaned_data.get('phone')
        email = cleaned_data.get('email')
        
        # At least phone or email should be provided
        if not phone and not email:
            raise ValidationError('Please provide at least phone number or email address.')
        
        return cleaned_data

class ContactQuickAddForm(forms.ModelForm):
    """Simplified form for quick contact addition"""
    
    class Meta:
        model = Contact
        fields = ['name', 'phone', 'email', 'current_company', 'designation']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Name',
                'required': True
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Phone',
                'required': True
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Email'
            }),
            'current_company': Select2Widget(attrs={'class': 'form-control form-control-sm'}),
            'designation': Select2Widget(attrs={'class': 'form-control form-control-sm'})
        }

# ============== COMPANY FORMS ==============

class CompanyForm(forms.ModelForm):
    """Form for creating/editing companies"""
    
    class Meta:
        model = Company
        fields = [
            'name', 'industry', 'website', 'phone', 'email', 'address',
            'zone', 'company_size', 'annual_revenue', 'tax_id',
            'bank_name', 'bank_account', 'bank_branch', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Company name',
                'required': True
            }),
            'industry': Select2Widget(),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://...'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Company phone'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'info@company.com'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'zone': Select2Widget(),
            'company_size': forms.Select(attrs={'class': 'form-control'}),
            'annual_revenue': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Annual revenue in BDT'
            }),
            'tax_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tax ID/TIN'
            }),
            'bank_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Bank name'
            }),
            'bank_account': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Account number'
            }),
            'bank_branch': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Branch name'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4
            })
        }

# ============== STAKEHOLDER FORMS ==============

class StakeholderForm(forms.ModelForm):
    """Form for creating/editing stakeholders"""
    
    class Meta:
        model = Stakeholder
        fields = [
            'contact', 'company', 'stakeholder_type', 'group_name',
            'zone', 'email', 'website', 'address', 'bank_details', 'notes'
        ]
        widgets = {
            'contact': Select2Widget(attrs={'required': True}),
            'company': Select2Widget(attrs={'required': True}),
            'stakeholder_type': Select2Widget(attrs={'required': True}),
            'group_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., ACI Ltd.'
            }),
            'zone': Select2Widget(),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'stakeholder@email.com'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://...'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'bank_details': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Bank account details'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4
            })
        }
    
    def clean(self):
        """Validate stakeholder uniqueness"""
        cleaned_data = super().clean()
        contact = cleaned_data.get('contact')
        company = cleaned_data.get('company')
        stakeholder_type = cleaned_data.get('stakeholder_type')
        
        if contact and company and stakeholder_type:
            # Check for duplicate stakeholder
            existing = Stakeholder.objects.filter(
                contact=contact,
                company=company,
                stakeholder_type=stakeholder_type
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing.exists():
                raise ValidationError(
                    f'{contact} already exists as {stakeholder_type} for {company}'
                )
        
        return cleaned_data

# ============== LEAD FORMS ==============

class LeadForm(forms.ModelForm):
    """Form for creating/editing leads"""
    
    class Meta:
        model = Lead
        fields = [
            'title', 'contact', 'company', 'stakeholder', 'source', 'status',
            'estimated_value', 'probability', 'expected_close_date',
            'owner', 'collaborators', 'rate_type', 'delivery_type',
            'expected_delivery_date', 'notes'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., PLC System for Textile Mill',
                'required': True
            }),
            'contact': Select2Widget(attrs={'required': True}),
            'company': Select2Widget(),
            'stakeholder': Select2Widget(),
            'source': Select2Widget(),
            'status': Select2Widget(attrs={'required': True}),
            'estimated_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Estimated value in BDT'
            }),
            'probability': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0-100',
                'min': 0,
                'max': 100
            }),
            'expected_close_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'owner': Select2Widget(),
            'collaborators': Select2MultipleWidget(),
            'rate_type': forms.Select(attrs={'class': 'form-control'}),
            'delivery_type': forms.Select(attrs={'class': 'form-control'}),
            'expected_delivery_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set default owner to current user
        if self.user and not self.instance.pk:
            self.fields['owner'].initial = self.user
    
    def clean_probability(self):
        """Validate probability range"""
        probability = self.cleaned_data.get('probability')
        if probability is not None:
            if probability < 0 or probability > 100:
                raise ValidationError('Probability must be between 0 and 100')
        return probability
    
    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        expected_close = cleaned_data.get('expected_close_date')
        expected_delivery = cleaned_data.get('expected_delivery_date')
        
        # Delivery date should be after close date
        if expected_close and expected_delivery:
            if expected_delivery < expected_close:
                raise ValidationError(
                    'Expected delivery date cannot be before expected close date'
                )
        
        return cleaned_data

# ============== LEAD PRODUCT FORMSET ==============

class LeadProductForm(forms.ModelForm):
    """Form for adding products to lead"""
    
    # For fetching Mitsubishi products via API
    fetch_from_api = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Fetch from Mitsubishi API'
    )
    
    class Meta:
        model = LeadProduct
        fields = ['product', 'quantity', 'unit_price', 'custom_description', 'notes']
        widgets = {
            'product': Select2Widget(attrs={'class': 'product-select'}),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'value': 1
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Unit price'
            }),
            'custom_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'For custom/non-catalog products'
            }),
            'notes': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Notes'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter products based on availability
        self.fields['product'].queryset = Product.objects.filter(
            is_active=True,
            is_deleted=False
        )

LeadProductFormSet = forms.inlineformset_factory(
    Lead, LeadProduct,
    form=LeadProductForm,
    extra=1,
    can_delete=True
)

# ============== PRODUCT FORMS ==============

class ProductForm(forms.ModelForm):
    """Form for manually adding products (non-Mitsubishi)"""
    
    class Meta:
        model = Product
        fields = [
            'name', 'brand', 'model', 'capacity', 'category',
            'description', 'technical_specs', 'price', 'stock_quantity',
            'image', 'datasheet', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Product name',
                'required': True
            }),
            'brand': Select2Widget(attrs={'required': True}),
            'model': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Model number'
            }),
            'capacity': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Capacity/Specifications'
            }),
            'category': Select2Widget(),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4
            }),
            'technical_specs': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'JSON format technical specifications'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Price in BDT'
            }),
            'stock_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'value': 0
            }),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'datasheet': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
    
    def clean_technical_specs(self):
        """Validate JSON format for technical specs"""
        specs = self.cleaned_data.get('technical_specs')
        if specs:
            import json
            try:
                # Try to parse as JSON
                if isinstance(specs, str):
                    json.loads(specs)
            except json.JSONDecodeError:
                raise ValidationError('Technical specs must be valid JSON format')
        return specs

class OtherBrandProductForm(forms.Form):
    """Form for adding multiple products from other brands"""
    
    brand_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Brand name'
        })
    )
    
    # Dynamic fields for 3 products
    product_1_name = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Product 1 name'
        })
    )
    product_1_model = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Model/Capacity'
        })
    )
    product_1_quantity = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Quantity',
            'min': 0
        })
    )
    
    product_2_name = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Product 2 name'
        })
    )
    product_2_model = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Model/Capacity'
        })
    )
    product_2_quantity = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Quantity',
            'min': 0
        })
    )
    
    product_3_name = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Product 3 name'
        })
    )
    product_3_model = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Model/Capacity'
        })
    )
    product_3_quantity = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Quantity',
            'min': 0
        })
    )
    
    def clean(self):
        """Ensure at least one product is entered"""
        cleaned_data = super().clean()
        
        # Check if at least one product is provided
        has_product = False
        for i in range(1, 4):
            if cleaned_data.get(f'product_{i}_name'):
                has_product = True
                break
        
        if not has_product:
            raise ValidationError('Please enter at least one product')
        
        return cleaned_data

# ============== ACTIVITY FORMS ==============

class ActivityForm(forms.ModelForm):
    """Form for creating/editing activities"""
    
    class Meta:
        model = Activity
        fields = [
            'activity_type', 'subject', 'description', 'contact', 'lead',
            'scheduled_date', 'duration', 'priority', 'assigned_to', 'status'
        ]
        widgets = {
            'activity_type': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Activity subject',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4
            }),
            'contact': Select2Widget(),
            'lead': Select2Widget(),
            'scheduled_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
                'required': True
            }),
            'duration': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 15,
                'step': 15,
                'value': 30
            }),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'assigned_to': Select2Widget(),
            'status': forms.Select(attrs={'class': 'form-control'})
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set default assigned_to to current user
        if self.user and not self.instance.pk:
            self.fields['assigned_to'].initial = self.user
    
    def clean(self):
        """Validate activity relationships"""
        cleaned_data = super().clean()
        contact = cleaned_data.get('contact')
        lead = cleaned_data.get('lead')
        
        # At least one of contact or lead should be selected
        if not contact and not lead:
            raise ValidationError('Please select either a contact or a lead for this activity')
        
        return cleaned_data

# ============== DOCUMENT FORM ==============

class DocumentUploadForm(forms.ModelForm):
    """Form for uploading documents"""
    
    class Meta:
        model = Document
        fields = ['file', 'document_type', 'description']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'required': True
            }),
            'document_type': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Document description'
            })
        }
    
    def clean_file(self):
        """Validate file size and type"""
        file = self.cleaned_data.get('file')
        if file:
            # Check file size (limit to 10MB)
            if file.size > 10 * 1024 * 1024:
                raise ValidationError('File size cannot exceed 10MB')
            
            # Check file extension
            allowed_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.png', '.jpg', '.jpeg']
            file_ext = file.name.lower().split('.')[-1]
            if f'.{file_ext}' not in allowed_extensions:
                raise ValidationError(f'File type .{file_ext} is not allowed. Allowed types: {", ".join(allowed_extensions)}')
        
        return file

# ============== SEARCH/FILTER FORMS ==============

class ContactSearchForm(forms.Form):
    """Form for searching/filtering contacts"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, phone, email...'
        })
    )
    company = forms.ModelChoiceField(
        queryset=Company.objects.filter(is_deleted=False),
        required=False,
        widget=Select2Widget(attrs={'class': 'form-control'}),
        empty_label='All Companies'
    )
    status = forms.ModelChoiceField(
        queryset=ContactStatus.objects.filter(is_active=True),
        required=False,
        widget=Select2Widget(attrs={'class': 'form-control'}),
        empty_label='All Statuses'
    )

class LeadSearchForm(forms.Form):
    """Form for searching/filtering leads"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search leads...'
        })
    )
    status = forms.ModelChoiceField(
        queryset=LeadStatus.objects.filter(is_active=True),
        required=False,
        widget=Select2Widget(attrs={'class': 'form-control'}),
        empty_label='All Statuses'
    )
    owner = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        widget=Select2Widget(attrs={'class': 'form-control'}),
        empty_label='All Owners'
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )