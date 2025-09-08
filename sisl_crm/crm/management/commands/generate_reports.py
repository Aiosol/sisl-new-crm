# crm/management/commands/generate_reports.py
# Django management command to generate monthly reports

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg
from datetime import datetime, timedelta
import csv
import os
from crm.models import Lead, Activity, Contact, Company, LeadStatus
from crm.utils import get_fiscal_year_dates, format_currency

class Command(BaseCommand):
    help = 'Generate monthly CRM reports'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--month',
            type=int,
            help='Month number (1-12)'
        )
        parser.add_argument(
            '--year',
            type=int,
            help='Year (e.g., 2024)'
        )
        parser.add_argument(
            '--type',
            type=str,
            choices=['summary', 'leads', 'activities', 'products', 'all'],
            default='all',
            help='Type of report to generate'
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default='reports',
            help='Output directory for reports'
        )
    
    def handle(self, *args, **options):
        # Determine report period
        now = timezone.now()
        month = options.get('month') or now.month
        year = options.get('year') or now.year
        report_type = options.get('type')
        output_dir = options.get('output_dir')
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate report date range
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)
        
        self.stdout.write(f"Generating reports for {start_date.strftime('%B %Y')}...")
        
        # Generate requested reports
        if report_type in ['summary', 'all']:
            self.generate_summary_report(start_date, end_date, output_dir)
        
        if report_type in ['leads', 'all']:
            self.generate_leads_report(start_date, end_date, output_dir)
        
        if report_type in ['activities', 'all']:
            self.generate_activities_report(start_date, end_date, output_dir)
        
        if report_type in ['products', 'all']:
            self.generate_products_report(start_date, end_date, output_dir)
        
        self.stdout.write(self.style.SUCCESS(f"Reports generated successfully in {output_dir}/"))
    
    def generate_summary_report(self, start_date, end_date, output_dir):
        """Generate executive summary report"""
        self.stdout.write("Generating summary report...")
        
        # Gather metrics
        leads_qs = Lead.objects.filter(
            created_at__gte=start_date,
            created_at__lt=end_date,
            is_deleted=False
        )
        
        total_leads = leads_qs.count()
        won_leads = leads_qs.filter(status__is_won=True).count()
        lost_leads = leads_qs.filter(status__is_lost=True).count()
        
        total_value = leads_qs.aggregate(Sum('estimated_value'))['estimated_value__sum'] or 0
        won_value = leads_qs.filter(status__is_won=True).aggregate(
            Sum('estimated_value'))['estimated_value__sum'] or 0
        
        # Conversion rate
        conversion_rate = (won_leads / total_leads * 100) if total_leads > 0 else 0
        
        # Activities
        activities = Activity.objects.filter(
            scheduled_date__gte=start_date,
            scheduled_date__lt=end_date
        )
        
        total_activities = activities.count()
        completed_activities = activities.filter(status='completed').count()
        
        # Write summary
        summary_file = os.path.join(output_dir, f"summary_{start_date.strftime('%Y-%m')}.txt")
        with open(summary_file, 'w') as f:
            f.write(f"SISL CRM Monthly Summary Report\n")
            f.write(f"Period: {start_date.strftime('%B %Y')}\n")
            f.write(f"Generated: {timezone.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write("=" * 50 + "\n\n")
            
            f.write("LEAD METRICS\n")
            f.write("-" * 20 + "\n")
            f.write(f"Total Leads: {total_leads}\n")
            f.write(f"Won Leads: {won_leads}\n")
            f.write(f"Lost Leads: {lost_leads}\n")
            f.write(f"Conversion Rate: {conversion_rate:.1f}%\n")
            f.write(f"Total Pipeline Value: {format_currency(total_value)}\n")
            f.write(f"Won Value: {format_currency(won_value)}\n\n")
            
            f.write("ACTIVITY METRICS\n")
            f.write("-" * 20 + "\n")
            f.write(f"Total Activities: {total_activities}\n")
            f.write(f"Completed: {completed_activities}\n")
            f.write(f"Completion Rate: {(completed_activities/total_activities*100) if total_activities else 0:.1f}%\n\n")
            
            # Lead sources
            f.write("TOP LEAD SOURCES\n")
            f.write("-" * 20 + "\n")
            sources = leads_qs.values('source__name').annotate(
                count=Count('id')
            ).order_by('-count')[:5]
            
            for source in sources:
                f.write(f"{source['source__name'] or 'Unknown'}: {source['count']}\n")
    
    def generate_leads_report(self, start_date, end_date, output_dir):
        """Generate detailed leads report"""
        self.stdout.write("Generating leads report...")
        
        leads = Lead.objects.filter(
            created_at__gte=start_date,
            created_at__lt=end_date,
            is_deleted=False
        ).select_related('contact', 'company', 'status', 'owner', 'source')
        
        csv_file = os.path.join(output_dir, f"leads_{start_date.strftime('%Y-%m')}.csv")
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Lead Number', 'Title', 'Contact', 'Company', 'Status',
                'Source', 'Value', 'Probability', 'Weighted Value',
                'Owner', 'Created Date', 'Expected Close Date'
            ])
            
            for lead in leads:
                writer.writerow([
                    lead.lead_number,
                    lead.title,
                    lead.contact.name,
                    lead.company.name if lead.company else '',
                    lead.status.name if lead.status else '',
                    lead.source.name if lead.source else '',
                    lead.estimated_value or 0,
                    lead.probability,
                    lead.weighted_value or 0,
                    lead.owner.get_full_name() if lead.owner else '',
                    lead.created_at.strftime('%Y-%m-%d'),
                    lead.expected_close_date.strftime('%Y-%m-%d') if lead.expected_close_date else ''
                ])
    
    def generate_activities_report(self, start_date, end_date, output_dir):
        """Generate activities report"""
        self.stdout.write("Generating activities report...")
        
        activities = Activity.objects.filter(
            scheduled_date__gte=start_date,
            scheduled_date__lt=end_date
        ).select_related('contact', 'lead', 'assigned_to')
        
        # Group by type
        by_type = activities.values('activity_type').annotate(
            count=Count('id'),
            completed=Count('id', filter=Q(status='completed'))
        )
        
        csv_file = os.path.join(output_dir, f"activities_{start_date.strftime('%Y-%m')}.csv")
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Activity Type', 'Total', 'Completed', 'Completion Rate'])
            
            for type_data in by_type:
                completion_rate = (type_data['completed'] / type_data['count'] * 100) if type_data['count'] > 0 else 0
                writer.writerow([
                    type_data['activity_type'],
                    type_data['count'],
                    type_data['completed'],
                    f"{completion_rate:.1f}%"
                ])
    
    def generate_products_report(self, start_date, end_date, output_dir):
        """Generate products performance report"""
        self.stdout.write("Generating products report...")
        
        from crm.models import LeadProduct
        
        # Most requested products
        products = LeadProduct.objects.filter(
            lead__created_at__gte=start_date,
            lead__created_at__lt=end_date,
            lead__is_deleted=False
        ).values(
            'product__name', 'product__brand__name', 'product__sku'
        ).annotate(
            lead_count=Count('lead', distinct=True),
            total_quantity=Sum('quantity'),
            total_value=Sum('total_price')
        ).order_by('-lead_count')
        
        csv_file = os.path.join(output_dir, f"products_{start_date.strftime('%Y-%m')}.csv")
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Product', 'Brand', 'SKU', 'Leads', 'Total Quantity', 'Total Value'])
            
            for product in products:
                writer.writerow([
                    product['product__name'],
                    product['product__brand__name'],
                    product['product__sku'] or '-',
                    product['lead_count'],
                    product['total_quantity'] or 0,
                    product['total_value'] or 0
                ])