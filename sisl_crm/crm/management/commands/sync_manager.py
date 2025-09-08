# crm/management/commands/sync_manager.py
# Django management command to sync products from Manager.io

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from crm.services.manager_api import ManagerAPIClient
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync products from Manager.io API'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--test',
            action='store_true',
            help='Test API connection without syncing'
        )
        parser.add_argument(
            '--update-availability',
            action='store_true',
            help='Only update availability for existing products'
        )
    
    def handle(self, *args, **options):
        test_only = options.get('test', False)
        update_availability = options.get('update_availability', False)
        
        try:
            client = ManagerAPIClient()
            
            # Test connection
            self.stdout.write("Testing Manager.io API connection...")
            if not client.test_connection():
                raise CommandError("Failed to connect to Manager.io API. Check your credentials.")
            
            self.stdout.write(self.style.SUCCESS("API connection successful!"))
            
            if test_only:
                # Just test product fetch
                self.stdout.write("\nFetching sample products...")
                try:
                    items = client._fetch_all_inventory_items()
                    self.stdout.write(f"Found {len(items)} products in Manager.io")
                    for item in items[:5]:
                        self.stdout.write(f"- {item.get('ItemName')} ({item.get('ItemCode')})")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to fetch items: {str(e)}"))
                return
            
            if update_availability:
                # Update availability only
                self.stdout.write("\nUpdating product availability from Manager.io...")
                from crm.models import Product
                
                items = client._fetch_all_inventory_items()
                updated = 0
                
                for item in items:
                    try:
                        sku = item.get('ItemCode')
                        if sku:
                            product = Product.objects.filter(sku=sku).first()
                            if product:
                                quantity = int(client._safe_decimal(item.get('qtyOnHand', 0)))
                                product.stock_quantity = quantity
                                product.save(update_fields=['stock_quantity', 'updated_at'])
                                updated += 1
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"Failed to update {sku}: {str(e)}"))
                
                self.stdout.write(
                    self.style.SUCCESS(f"Updated availability for {updated} products")
                )
                return
            
            # Full sync
            self.stdout.write("\nStarting product sync from Manager.io...")
            self.stdout.write("This may take several minutes depending on the number of products.")
            
            result = client.sync_products()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSync completed successfully!\n"
                    f"- Products created: {result['created']}\n"
                    f"- Products updated: {result['updated']}\n"
                    f"- Total items in Manager.io: {result['total_items']}\n"
                    f"- Completed at: {result['timestamp']}"
                )
            )
            
            # Log to audit trail
            from crm.models import AuditLog
            AuditLog.objects.create(
                model_name='Product',
                object_id='SYNC_COMMAND',
                change_type='update',
                field_name='sync_products',
                new_value=f"Created: {result['created']}, Updated: {result['updated']}",
                changed_by=None
            )
            
        except Exception as e:
            logger.error(f"Product sync failed: {str(e)}")
            raise CommandError(f"Sync failed: {str(e)}")