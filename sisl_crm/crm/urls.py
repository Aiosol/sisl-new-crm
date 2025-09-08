# crm/urls.py - URL patterns for CRM app

from django.urls import path
from . import views

app_name = 'crm'

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Contacts
    path('contacts/', views.ContactListView.as_view(), name='contact_list'),
    path('contacts/create/', views.ContactCreateView.as_view(), name='contact_create'),
    path('contacts/<uuid:pk>/', views.ContactDetailView.as_view(), name='contact_detail'),
    path('contacts/<uuid:pk>/edit/', views.ContactUpdateView.as_view(), name='contact_update'),
    path('contacts/<uuid:pk>/delete/', views.ContactDeleteView.as_view(), name='contact_delete'),
    
    # Companies
    path('companies/', views.CompanyListView.as_view(), name='company_list'),
    path('companies/create/', views.CompanyCreateView.as_view(), name='company_create'),
    path('companies/<uuid:pk>/', views.CompanyDetailView.as_view(), name='company_detail'),
    path('companies/<uuid:pk>/edit/', views.CompanyUpdateView.as_view(), name='company_update'),
    
    # Stakeholders
    path('stakeholders/', views.StakeholderListView.as_view(), name='stakeholder_list'),
    path('stakeholders/create/', views.StakeholderCreateView.as_view(), name='stakeholder_create'),
    
    # Leads
    path('leads/', views.LeadListView.as_view(), name='lead_list'),
    path('leads/create/', views.LeadCreateView.as_view(), name='lead_create'),
    path('leads/pipeline/', views.LeadPipelineView.as_view(), name='lead_pipeline'),
    path('leads/<uuid:pk>/', views.LeadDetailView.as_view(), name='lead_detail'),
    path('leads/<uuid:pk>/edit/', views.LeadUpdateView.as_view(), name='lead_update'),
    path('leads/<uuid:pk>/approve/', views.lead_approve_view, name='lead_approve'),
    
    # Products
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/create/', views.ProductCreateView.as_view(), name='product_create'),
    path('products/sync-mitsubishi/', views.product_sync_mitsubishi, name='product_sync_mitsubishi'),
    path('products/<uuid:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    
    # Activities
    path('activities/', views.ActivityListView.as_view(), name='activity_list'),
    path('activities/create/', views.ActivityCreateView.as_view(), name='activity_create'),
    path('activities/calendar/', views.ActivityCalendarView.as_view(), name='activity_calendar'),
    path('activities/<uuid:pk>/edit/', views.ActivityUpdateView.as_view(), name='activity_update'),
    path('activities/<uuid:pk>/complete/', views.activity_complete, name='activity_complete'),
    
    # API endpoints
    path('api/products/search/', views.ProductSearchAPIView.as_view(), name='api_product_search'),
    path('api/contacts/check-duplicate/', views.ContactDuplicateCheckAPIView.as_view(), name='api_contact_duplicate'),
    path('api/leads/pipeline-status/', views.LeadPipelineStatusAPIView.as_view(), name='api_pipeline_status'),
]