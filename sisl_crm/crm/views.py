# views.py - SISL CRM Django Views
# View classes for all CRM functionality

from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView,
    TemplateView, FormView, View
)
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count, Sum, Avg, F
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .models import (
    Contact, Company, Stakeholder, Lead, LeadProduct,
    Product, Activity, Document, AuditLog,
    ContactStatus, LeadStatus, Zone, Industry
)
from .forms import (
    ContactForm, CompanyForm, StakeholderForm, LeadForm,
    LeadProductFormSet, ProductForm, ActivityForm,
    ContactSearchForm, LeadSearchForm
)
from .utils import log_audit_trail
from .services.manager_api import ManagerAPIClient

# ============== DASHBOARD ==============

class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard view"""
    template_name = 'crm/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Basic counts
        context['total_contacts'] = Contact.objects.filter(is_deleted=False).count()
        context['total_companies'] = Company.objects.filter(is_deleted=False).count()
        context['total_products'] = Product.objects.filter(is_deleted=False, is_active=True).count()
        
        # Lead metrics
        leads_qs = Lead.objects.filter(is_deleted=False)
        if not user.has_perm('crm.can_view_all_leads'):
            leads_qs = leads_qs.filter(Q(owner=user) | Q(collaborators=user)).distinct()
        
        context['total_leads'] = leads_qs.count()
        context['open_leads'] = leads_qs.exclude(
            status__in=LeadStatus.objects.filter(Q(is_won=True) | Q(is_lost=True))
        ).count()
        
        # Pipeline value
        pipeline_value = leads_qs.exclude(
            status__in=LeadStatus.objects.filter(Q(is_won=True) | Q(is_lost=True))
        ).aggregate(
            total=Sum('estimated_value'),
            weighted=Sum('weighted_value')
        )
        context['pipeline_value'] = pipeline_value['total'] or 0
        context['weighted_pipeline_value'] = pipeline_value['weighted'] or 0
        
        # Activities
        today = timezone.now().date()
        activities_qs = Activity.objects.filter(status='scheduled')
        if not user.is_superuser:
            activities_qs = activities_qs.filter(assigned_to=user)
            
        context['activities_today'] = activities_qs.filter(
            scheduled_date__date=today
        ).count()
        context['activities_overdue'] = activities_qs.filter(
            scheduled_date__lt=timezone.now()
        ).count()
        
        # Recent activities
        context['recent_activities'] = activities_qs.order_by('scheduled_date')[:5]
        
        # Leads by stage for funnel chart
        lead_stages = []
        for status in LeadStatus.objects.filter(is_active=True).order_by('stage_order'):
            count = leads_qs.filter(status=status).count()
            value = leads_qs.filter(status=status).aggregate(
                total=Sum('estimated_value')
            )['total'] or 0
            lead_stages.append({
                'name': status.name,
                'count': count,
                'value': value,
                'color': status.color
            })
        context['lead_stages'] = json.dumps(lead_stages)
        
        # Top products (by lead count)
        top_products = LeadProduct.objects.filter(
            lead__in=leads_qs
        ).values(
            'product__name', 'product__brand__name'
        ).annotate(
            count=Count('id'),
            total_quantity=Sum('quantity')
        ).order_by('-count')[:5]
        context['top_products'] = top_products
        
        # Recent leads
        context['recent_leads'] = leads_qs.order_by('-created_at')[:5]
        
        # Approval pending leads (for managers)
        if user.has_perm('crm.can_approve_leads'):
            context['pending_approvals'] = leads_qs.filter(
                requires_approval=True,
                approved_by__isnull=True
            ).count()
        
        return context

# ============== CONTACT VIEWS ==============

class ContactListView(LoginRequiredMixin, ListView):
    """List all contacts with search and filters"""
    model = Contact
    template_name = 'crm/contacts/list.html'
    context_object_name = 'contacts'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = Contact.objects.filter(is_deleted=False).select_related(
            'current_company', 'status', 'designation'
        ).prefetch_related('product_interests')
        
        # Apply search/filters
        form = ContactSearchForm(self.request.GET)
        if form.is_valid():
            if form.cleaned_data.get('search'):
                search = form.cleaned_data['search']
                queryset = queryset.filter(
                    Q(name__icontains=search) |
                    Q(phone__icontains=search) |
                    Q(email__icontains=search) |
                    Q(current_company__name__icontains=search)
                )
            if form.cleaned_data.get('company'):
                queryset = queryset.filter(current_company=form.cleaned_data['company'])
            if form.cleaned_data.get('status'):
                queryset = queryset.filter(status=form.cleaned_data['status'])
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = ContactSearchForm(self.request.GET)
        context['total_count'] = self.get_queryset().count()
        return context

class ContactDetailView(LoginRequiredMixin, DetailView):
    """Contact detail view"""
    model = Contact
    template_name = 'crm/contacts/detail.html'
    context_object_name = 'contact'
    
    def get_queryset(self):
        return Contact.objects.filter(is_deleted=False)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contact = self.object
        
        # Related data
        context['company_history'] = contact.company_history.select_related(
            'company', 'designation'
        ).order_by('-is_current', '-start_date')
        
        context['stakeholder_roles'] = contact.stakeholder_roles.select_related(
            'company', 'stakeholder_type'
        ).filter(is_deleted=False)
        
        context['leads'] = contact.leads.select_related(
            'status', 'owner'
        ).filter(is_deleted=False).order_by('-created_at')[:10]
        
        context['activities'] = contact.activities.select_related(
            'assigned_to'
        ).order_by('-scheduled_date')[:10]
        
        context['documents'] = contact.documents.order_by('-created_at')
        
        return context

class ContactCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Create new contact"""
    model = Contact
    form_class = ContactForm
    template_name = 'crm/contacts/form.html'
    success_message = "Contact created successfully"
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        
        # Check for duplicates
        phone = form.cleaned_data.get('phone')
        email = form.cleaned_data.get('email')
        
        duplicates = Contact.objects.filter(is_deleted=False).filter(
            Q(phone=phone) | Q(email=email) if email else Q(phone=phone)
        )
        
        if duplicates.exists():
            messages.warning(
                self.request,
                f"Warning: Similar contacts found - {', '.join([str(d) for d in duplicates[:3]])}"
            )
        
        response = super().form_valid(form)
        
        # Log audit
        log_audit_trail(
            'Contact', str(form.instance.id), 'create',
            user=self.request.user, request=self.request
        )
        
        # Create company history if company selected
        if form.instance.current_company:
            from .models import ContactCompanyHistory
            ContactCompanyHistory.objects.create(
                contact=form.instance,
                company=form.instance.current_company,
                designation=form.instance.designation,
                is_current=True,
                start_date=timezone.now().date()
            )
        
        return response
    
    def get_success_url(self):
        return reverse('crm:contact_detail', kwargs={'pk': self.object.pk})

class ContactUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Update existing contact"""
    model = Contact
    form_class = ContactForm
    template_name = 'crm/contacts/form.html'
    success_message = "Contact updated successfully"
    
    def get_queryset(self):
        return Contact.objects.filter(is_deleted=False)
    
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        
        # Track company changes
        if 'current_company' in form.changed_data:
            old_company = Contact.objects.get(pk=self.object.pk).current_company
            new_company = form.cleaned_data['current_company']
            
            if old_company != new_company:
                from .models import ContactCompanyHistory
                # End current employment
                if old_company:
                    ContactCompanyHistory.objects.filter(
                        contact=self.object,
                        company=old_company,
                        is_current=True
                    ).update(
                        is_current=False,
                        end_date=timezone.now().date()
                    )
                
                # Start new employment
                if new_company:
                    ContactCompanyHistory.objects.create(
                        contact=self.object,
                        company=new_company,
                        designation=form.cleaned_data.get('designation'),
                        is_current=True,
                        start_date=timezone.now().date()
                    )
        
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('crm:contact_detail', kwargs={'pk': self.object.pk})

class ContactDeleteView(LoginRequiredMixin, DeleteView):
    """Soft delete contact"""
    model = Contact
    template_name = 'crm/contacts/delete_confirm.html'
    success_url = reverse_lazy('crm:contact_list')
    
    def get_queryset(self):
        return Contact.objects.filter(is_deleted=False)
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.soft_delete(user=request.user)
        messages.success(request, "Contact deleted successfully")
        return redirect(self.get_success_url())

# ============== COMPANY VIEWS ==============

class CompanyListView(LoginRequiredMixin, ListView):
    """List all companies"""
    model = Company
    template_name = 'crm/companies/list.html'
    context_object_name = 'companies'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = Company.objects.filter(is_deleted=False).select_related(
            'industry', 'zone'
        ).annotate(
            contact_count=Count('current_employees', filter=Q(current_employees__is_deleted=False)),
            lead_count=Count('leads', filter=Q(leads__is_deleted=False))
        )
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(phone__icontains=search) |
                Q(email__icontains=search)
            )
        
        # Filters
        industry = self.request.GET.get('industry')
        if industry:
            queryset = queryset.filter(industry_id=industry)
            
        zone = self.request.GET.get('zone')
        if zone:
            queryset = queryset.filter(zone_id=zone)
        
        return queryset.order_by('name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['industries'] = Industry.objects.filter(is_active=True)
        context['zones'] = Zone.objects.filter(is_active=True)
        context['total_count'] = self.get_queryset().count()
        return context

class CompanyDetailView(LoginRequiredMixin, DetailView):
    """Company detail view"""
    model = Company
    template_name = 'crm/companies/detail.html'
    context_object_name = 'company'
    
    def get_queryset(self):
        return Company.objects.filter(is_deleted=False)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = self.object
        
        # Employees
        context['current_employees'] = company.current_employees.filter(
            is_deleted=False
        ).select_related('designation', 'status')
        
        # Stakeholders
        context['stakeholders'] = company.stakeholders.filter(
            is_deleted=False
        ).select_related('contact', 'stakeholder_type')
        
        # Leads
        context['leads'] = company.leads.filter(
            is_deleted=False
        ).select_related('status', 'owner').order_by('-created_at')[:10]
        
        # Documents
        context['documents'] = company.documents.order_by('-created_at')
        
        return context

class CompanyCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Create new company"""
    model = Company
    form_class = CompanyForm
    template_name = 'crm/companies/form.html'
    success_message = "Company created successfully"
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('crm:company_detail', kwargs={'pk': self.object.pk})

class CompanyUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Update existing company"""
    model = Company
    form_class = CompanyForm
    template_name = 'crm/companies/form.html'
    success_message = "Company updated successfully"
    
    def get_queryset(self):
        return Company.objects.filter(is_deleted=False)
    
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('crm:company_detail', kwargs={'pk': self.object.pk})

# ============== LEAD VIEWS ==============

class LeadListView(LoginRequiredMixin, ListView):
    """List leads with filters"""
    model = Lead
    template_name = 'crm/leads/list.html'
    context_object_name = 'leads'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = Lead.objects.filter(is_deleted=False).select_related(
            'contact', 'company', 'status', 'owner', 'source'
        )
        
        # Permission check
        user = self.request.user
        if not user.has_perm('crm.can_view_all_leads') and not user.is_superuser:
            queryset = queryset.filter(
                Q(owner=user) | Q(collaborators=user)
            ).distinct()
        
        # Apply filters
        form = LeadSearchForm(self.request.GET)
        if form.is_valid():
            if form.cleaned_data.get('search'):
                search = form.cleaned_data['search']
                queryset = queryset.filter(
                    Q(title__icontains=search) |
                    Q(lead_number__icontains=search) |
                    Q(contact__name__icontains=search) |
                    Q(company__name__icontains=search)
                )
            if form.cleaned_data.get('status'):
                queryset = queryset.filter(status=form.cleaned_data['status'])
            if form.cleaned_data.get('owner'):
                queryset = queryset.filter(owner=form.cleaned_data['owner'])
            if form.cleaned_data.get('date_from'):
                queryset = queryset.filter(created_at__date__gte=form.cleaned_data['date_from'])
            if form.cleaned_data.get('date_to'):
                queryset = queryset.filter(created_at__date__lte=form.cleaned_data['date_to'])
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = LeadSearchForm(self.request.GET)
        context['total_count'] = self.get_queryset().count()
        
        # Summary stats
        queryset = self.get_queryset()
        context['total_value'] = queryset.aggregate(
            Sum('estimated_value')
        )['estimated_value__sum'] or 0
        context['weighted_value'] = queryset.aggregate(
            Sum('weighted_value')
        )['weighted_value__sum'] or 0
        
        return context

class LeadDetailView(LoginRequiredMixin, DetailView):
    """Lead detail view"""
    model = Lead
    template_name = 'crm/leads/detail.html'
    context_object_name = 'lead'
    
    def get_queryset(self):
        queryset = Lead.objects.filter(is_deleted=False)
        user = self.request.user
        if not user.has_perm('crm.can_view_all_leads') and not user.is_superuser:
            queryset = queryset.filter(
                Q(owner=user) | Q(collaborators=user)
            ).distinct()
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lead = self.object
        
        # Products
        context['products'] = lead.lead_products.select_related(
            'product__brand', 'product__category'
        )
        
        # Activities
        context['activities'] = lead.activities.select_related(
            'assigned_to'
        ).order_by('-scheduled_date')
        
        # Documents
        context['documents'] = lead.documents.order_by('-created_at')
        
        # Collaborators
        context['collaborators'] = lead.collaborators.all()
        
        # Can approve?
        context['can_approve'] = (
            self.request.user.has_perm('crm.can_approve_leads') and
            lead.requires_approval and
            not lead.approved_by
        )
        
        return context

class LeadCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Create new lead"""
    model = Lead
    form_class = LeadForm
    template_name = 'crm/leads/form.html'
    success_message = "Lead created successfully"
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['product_formset'] = LeadProductFormSet(self.request.POST)
        else:
            context['product_formset'] = LeadProductFormSet()
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        product_formset = context['product_formset']
        
        if product_formset.is_valid():
            form.instance.created_by = self.request.user
            form.instance.updated_by = self.request.user
            if not form.instance.owner:
                form.instance.owner = self.request.user
            
            self.object = form.save()
            product_formset.instance = self.object
            product_formset.save()
            
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)
    
    def get_success_url(self):
        return reverse('crm:lead_detail', kwargs={'pk': self.object.pk})

class LeadUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Update existing lead"""
    model = Lead
    form_class = LeadForm
    template_name = 'crm/leads/form.html'
    success_message = "Lead updated successfully"
    
    def get_queryset(self):
        queryset = Lead.objects.filter(is_deleted=False)
        user = self.request.user
        if not user.has_perm('crm.can_view_all_leads') and not user.is_superuser:
            queryset = queryset.filter(
                Q(owner=user) | Q(collaborators=user)
            ).distinct()
        return queryset
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['product_formset'] = LeadProductFormSet(
                self.request.POST,
                instance=self.object
            )
        else:
            context['product_formset'] = LeadProductFormSet(
                instance=self.object
            )
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        product_formset = context['product_formset']
        
        if product_formset.is_valid():
            form.instance.updated_by = self.request.user
            self.object = form.save()
            product_formset.instance = self.object
            product_formset.save()
            
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)
    
    def get_success_url(self):
        return reverse('crm:lead_detail', kwargs={'pk': self.object.pk})

class LeadPipelineView(LoginRequiredMixin, TemplateView):
    """Kanban-style pipeline view"""
    template_name = 'crm/leads/pipeline.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get leads based on permissions
        leads_qs = Lead.objects.filter(is_deleted=False)
        if not user.has_perm('crm.can_view_all_leads') and not user.is_superuser:
            leads_qs = leads_qs.filter(
                Q(owner=user) | Q(collaborators=user)
            ).distinct()
        
        # Group by status
        pipeline = []
        for status in LeadStatus.objects.filter(is_active=True).order_by('stage_order'):
            stage_leads = leads_qs.filter(status=status).select_related(
                'contact', 'company', 'owner'
            ).order_by('-created_at')
            
            pipeline.append({
                'status': status,
                'leads': stage_leads[:20],  # Limit for performance
                'count': stage_leads.count(),
                'value': stage_leads.aggregate(Sum('estimated_value'))['estimated_value__sum'] or 0
            })
        
        context['pipeline'] = pipeline
        return context

def lead_approve_view(request, pk):
    """Approve a lead (for managers)"""
    if not request.user.has_perm('crm.can_approve_leads'):
        messages.error(request, "You don't have permission to approve leads")
        return redirect('crm:lead_detail', pk=pk)
    
    lead = get_object_or_404(Lead, pk=pk, is_deleted=False)
    
    if request.method == 'POST':
        approval_notes = request.POST.get('approval_notes', '')
        lead.approved_by = request.user
        lead.approved_at = timezone.now()
        lead.approval_notes = approval_notes
        lead.save()
        
        messages.success(request, f"Lead {lead.lead_number} approved successfully")
        return redirect('crm:lead_detail', pk=pk)
    
    return render(request, 'crm/leads/approval.html', {'lead': lead})

# ============== PRODUCT VIEWS ==============

class ProductListView(LoginRequiredMixin, ListView):
    """List all products"""
    model = Product
    template_name = 'crm/products/list.html'
    context_object_name = 'products'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = Product.objects.filter(
            is_deleted=False,
            is_active=True
        ).select_related('brand', 'category')
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(model__icontains=search) |
                Q(sku__icontains=search) |
                Q(brand__name__icontains=search)
            )
        
        # Filters
        brand = self.request.GET.get('brand')
        if brand:
            queryset = queryset.filter(brand_id=brand)
            
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
            
        is_mitsubishi = self.request.GET.get('is_mitsubishi')
        if is_mitsubishi == '1':
            queryset = queryset.filter(is_from_api=True)
        elif is_mitsubishi == '0':
            queryset = queryset.filter(is_from_api=False)
        
        return queryset.order_by('brand__name', 'name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import Brand, ProductCategory
        context['brands'] = Brand.objects.filter(is_active=True)
        context['categories'] = ProductCategory.objects.filter(is_active=True)
        context['total_count'] = self.get_queryset().count()
        return context

class ProductDetailView(LoginRequiredMixin, DetailView):
    """Product detail view"""
    model = Product
    template_name = 'crm/products/detail.html'
    context_object_name = 'product'
    
    def get_queryset(self):
        return Product.objects.filter(is_deleted=False)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        
        # Lead usage
        context['lead_usage'] = LeadProduct.objects.filter(
            product=product,
            lead__is_deleted=False
        ).select_related('lead__contact', 'lead__company').order_by('-created_at')[:10]
        
        # Documents
        context['documents'] = product.documents.order_by('-created_at')
        
        return context

class ProductCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    """Create new product (manual)"""
    model = Product
    form_class = ProductForm
    template_name = 'crm/products/form.html'
    success_message = "Product created successfully"
    permission_required = 'crm.add_product'
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        form.instance.is_from_api = False
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('crm:product_detail', kwargs={'pk': self.object.pk})

def product_sync_mitsubishi(request):
    """Sync products from Manager.io API"""
    if not request.user.has_perm('crm.add_product'):
        messages.error(request, "Permission denied")
        return redirect('crm:product_list')
    
    if request.method == 'POST':
        try:
            client = ManagerAPIClient()
            result = client.sync_products()
            messages.success(
                request, 
                f"Sync completed: {result['created']} created, {result['updated']} updated"
            )
        except Exception as e:
            messages.error(request, f"Sync failed: {str(e)}")
    
    return redirect('crm:product_list')

# ============== ACTIVITY VIEWS ==============

class ActivityListView(LoginRequiredMixin, ListView):
    """List activities"""
    model = Activity
    template_name = 'crm/activities/list.html'
    context_object_name = 'activities'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = Activity.objects.select_related(
            'contact', 'lead', 'assigned_to'
        )
        
        # Filter by user unless superuser
        if not self.request.user.is_superuser:
            queryset = queryset.filter(assigned_to=self.request.user)
        
        # Status filter
        status = self.request.GET.get('status', 'scheduled')
        if status != 'all':
            queryset = queryset.filter(status=status)
        
        # Date filters
        date_filter = self.request.GET.get('date_filter')
        today = timezone.now().date()
        
        if date_filter == 'today':
            queryset = queryset.filter(scheduled_date__date=today)
        elif date_filter == 'tomorrow':
            queryset = queryset.filter(scheduled_date__date=today + timedelta(days=1))
        elif date_filter == 'week':
            queryset = queryset.filter(
                scheduled_date__date__gte=today,
                scheduled_date__date__lt=today + timedelta(days=7)
            )
        elif date_filter == 'overdue':
            queryset = queryset.filter(
                scheduled_date__lt=timezone.now(),
                status='scheduled'
            )
        
        return queryset.order_by('scheduled_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_filter'] = self.request.GET.get('status', 'scheduled')
        context['date_filter'] = self.request.GET.get('date_filter', 'all')
        return context

class ActivityCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Create new activity"""
    model = Activity
    form_class = ActivityForm
    template_name = 'crm/activities/form.html'
    success_message = "Activity created successfully"
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_initial(self):
        initial = super().get_initial()
        # Pre-populate contact/lead if passed in URL
        if 'contact' in self.request.GET:
            initial['contact'] = self.request.GET['contact']
        if 'lead' in self.request.GET:
            initial['lead'] = self.request.GET['lead']
        return initial
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        if not form.instance.assigned_to:
            form.instance.assigned_to = self.request.user
        return super().form_valid(form)
    
    def get_success_url(self):
        if self.object.lead:
            return reverse('crm:lead_detail', kwargs={'pk': self.object.lead.pk})
        elif self.object.contact:
            return reverse('crm:contact_detail', kwargs={'pk': self.object.contact.pk})
        else:
            return reverse('crm:activity_list')

class ActivityUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Update existing activity"""
    model = Activity
    form_class = ActivityForm
    template_name = 'crm/activities/form.html'
    success_message = "Activity updated successfully"
    
    def get_queryset(self):
        queryset = Activity.objects.all()
        if not self.request.user.is_superuser:
            queryset = queryset.filter(assigned_to=self.request.user)
        return queryset
    
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)
    
    def get_success_url(self):
        return self.request.GET.get('next', reverse('crm:activity_list'))

def activity_complete(request, pk):
    """Mark activity as complete"""
    activity = get_object_or_404(Activity, pk=pk)
    
    # Permission check
    if activity.assigned_to != request.user and not request.user.is_superuser:
        messages.error(request, "You can only complete activities assigned to you")
        return redirect('crm:activity_list')
    
    if request.method == 'POST':
        outcome = request.POST.get('outcome', '')
        next_action = request.POST.get('next_action', '')
        
        activity.mark_complete(request.user, outcome)
        if next_action:
            activity.next_action = next_action
            activity.save()
        
        messages.success(request, "Activity marked as complete")
        
        # Redirect based on context
        if activity.lead:
            return redirect('crm:lead_detail', pk=activity.lead.pk)
        elif activity.contact:
            return redirect('crm:contact_detail', pk=activity.contact.pk)
        else:
            return redirect('crm:activity_list')
    
    return render(request, 'crm/activities/complete.html', {'activity': activity})

class ActivityCalendarView(LoginRequiredMixin, TemplateView):
    """Calendar view of activities"""
    template_name = 'crm/activities/calendar.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get month from query params
        month = self.request.GET.get('month')
        year = self.request.GET.get('year')
        
        if month and year:
            try:
                current_date = datetime(int(year), int(month), 1)
            except:
                current_date = timezone.now()
        else:
            current_date = timezone.now()
        
        # Get activities for the month
        activities = Activity.objects.filter(
            scheduled_date__year=current_date.year,
            scheduled_date__month=current_date.month
        )
        
        if not self.request.user.is_superuser:
            activities = activities.filter(assigned_to=self.request.user)
        
        # Format for calendar
        calendar_data = []
        for activity in activities:
            calendar_data.append({
                'id': str(activity.id),
                'title': activity.subject,
                'start': activity.scheduled_date.isoformat(),
                'end': (activity.scheduled_date + timedelta(minutes=activity.duration)).isoformat(),
                'color': self._get_activity_color(activity),
                'url': reverse('crm:activity_update', kwargs={'pk': activity.pk})
            })
        
        context['calendar_data'] = json.dumps(calendar_data)
        context['current_date'] = current_date
        return context
    
    def _get_activity_color(self, activity):
        """Get color based on activity type and status"""
        if activity.status == 'completed':
            return '#28a745'
        elif activity.status == 'cancelled':
            return '#dc3545'
        
        colors = {
            'call': '#007bff',
            'email': '#17a2b8',
            'meeting': '#ffc107',
            'site_visit': '#fd7e14',
            'demo': '#6610f2',
            'follow_up': '#6c757d',
            'quotation': '#20c997',
            'negotiation': '#e83e8c',
            'other': '#6c757d'
        }
        return colors.get(activity.activity_type, '#6c757d')

# ============== STAKEHOLDER VIEWS ==============

class StakeholderListView(LoginRequiredMixin, ListView):
    """List all stakeholders"""
    model = Stakeholder
    template_name = 'crm/stakeholders/list.html'
    context_object_name = 'stakeholders'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = Stakeholder.objects.filter(is_deleted=False).select_related(
            'contact', 'company', 'stakeholder_type', 'zone'
        )
        
        # Filters
        stakeholder_type = self.request.GET.get('type')
        if stakeholder_type:
            queryset = queryset.filter(stakeholder_type_id=stakeholder_type)
            
        zone = self.request.GET.get('zone')
        if zone:
            queryset = queryset.filter(zone_id=zone)
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(contact__name__icontains=search) |
                Q(company__name__icontains=search) |
                Q(group_name__icontains=search)
            )
        
        return queryset.order_by('company__name', 'contact__name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stakeholder_types'] = StakeholderType.objects.filter(is_active=True)
        context['zones'] = Zone.objects.filter(is_active=True)
        context['total_count'] = self.get_queryset().count()
        return context

class StakeholderCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Create new stakeholder"""
    model = Stakeholder
    form_class = StakeholderForm
    template_name = 'crm/stakeholders/form.html'
    success_message = "Stakeholder created successfully"
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('crm:stakeholder_list')

# ============== API VIEWS ==============

class ProductSearchAPIView(LoginRequiredMixin, View):
    """API endpoint for product search"""
    
    def get(self, request):
        query = request.GET.get('q', '')
        products = Product.objects.filter(
            is_active=True,
            is_deleted=False
        ).filter(
            Q(name__icontains=query) |
            Q(model__icontains=query) |
            Q(sku__icontains=query)
        ).select_related('brand', 'category')[:20]
        
        data = []
        for product in products:
            data.append({
                'id': str(product.id),
                'text': str(product),
                'sku': product.sku,
                'price': float(product.price) if product.price else None,
                'stock': product.stock_quantity
            })
        
        return JsonResponse({'results': data})

class ContactDuplicateCheckAPIView(LoginRequiredMixin, View):
    """API endpoint to check for duplicate contacts"""
    
    def post(self, request):
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip().lower()
        exclude_id = request.POST.get('exclude_id')
        
        duplicates = Contact.objects.filter(is_deleted=False)
        
        if exclude_id:
            duplicates = duplicates.exclude(id=exclude_id)
        
        if phone:
            duplicates = duplicates.filter(phone=phone)
        elif email:
            duplicates = duplicates.filter(email=email)
        else:
            return JsonResponse({'duplicates': []})
        
        data = []
        for contact in duplicates[:5]:
            data.append({
                'id': str(contact.id),
                'name': contact.name,
                'company': str(contact.current_company) if contact.current_company else '',
                'phone': contact.phone,
                'email': contact.email
            })
        
        return JsonResponse({'duplicates': data})

class LeadPipelineStatusAPIView(LoginRequiredMixin, View):
    """API endpoint for pipeline status data"""
    
    def get(self, request):
        user = request.user
        
        # Get leads based on permissions
        leads_qs = Lead.objects.filter(is_deleted=False)
        if not user.has_perm('crm.can_view_all_leads') and not user.is_superuser:
            leads_qs = leads_qs.filter(
                Q(owner=user) | Q(collaborators=user)
            ).distinct()
        
        # Group by status
        data = []
        for status in LeadStatus.objects.filter(is_active=True).order_by('stage_order'):
            stage_leads = leads_qs.filter(status=status)
            data.append({
                'status': status.name,
                'color': status.color,
                'count': stage_leads.count(),
                'value': float(stage_leads.aggregate(
                    Sum('estimated_value')
                )['estimated_value__sum'] or 0)
            })
        
        return JsonResponse({'pipeline': data})

# ============== ERROR HANDLERS ==============

def handler404(request, exception):
    return render(request, '404.html', status=404)

def handler500(request):
    return render(request, '500.html', status=500)