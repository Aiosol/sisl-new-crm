# crm/services/manager_api.py - Manager.io API Integration Service

import requests
import json
from django.conf import settings
from django.utils import timezone
from datetime import datetime
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class ManagerAPIClient:
    """Client for integrating with Manager.io API for inventory management"""
    
    def __init__(self):
        self.api_url = settings.MANAGER_API_URL  # https://esourcingbd.ap-southeast-1.manager.io/api2
        self.api_key = settings.MANAGER_API_KEY  # Your X-API-KEY
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _make_request(self, method, endpoint, params=None, data=None):
        """Make a request to the Manager.io API with error handling"""
        url = f"{self.api_url}/{endpoint}"
        
        try:
            logger.info(f"Making {method.upper()} request to: {url}")
            
            if method.lower() == 'get':
                response = self.session.get(url, params=params, timeout=30)
            elif method.lower() == 'post':
                response = self.session.post(url, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            logger.info(f"Response status: {response.status_code}")
            
            # Handle 401 Unauthorized
            if response.status_code == 401:
                logger.error("401 Unauthorized - Check your Manager.io API key")
                raise Exception("Manager.io API authentication failed")
            
            response.raise_for_status()
            
            if response.content:
                return response.json()
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Manager.io API request failed: {str(e)}")
            raise
    
    def test_connection(self):
        """Test the API connection and authentication"""
        try:
            logger.info("Testing Manager.io API connection...")
            
            # Try to fetch just 1 inventory item to test
            response = self._make_request('GET', 'inventory-items', params={'pageSize': 1, 'skip': 0})
            
            if response:
                logger.info("✅ Manager.io API connection successful!")
                return True
            return False
                
        except Exception as e:
            logger.error(f"❌ Manager.io API connection failed: {str(e)}")
            return False
    
    def _fetch_all_inventory_items(self):
        """Fetch all inventory items with pagination from Manager.io"""
        try:
            logger.info("=== FETCHING ALL INVENTORY ITEMS FROM MANAGER.IO ===")
            
            all_items = []
            page_size = 100
            skip = 0
            max_iterations = 50
            iterations = 0
            
            while iterations < max_iterations:
                logger.info(f"Fetching page: skip={skip}, pageSize={page_size}")
                
                params = {
                    'pageSize': page_size,
                    'skip': skip
                }
                
                response = self._make_request('GET', 'inventory-items', params=params)
                
                if not response:
                    logger.warning(f"Empty response on iteration {iterations}")
                    break
                
                # Extract items from response
                page_items = []
                if isinstance(response, dict) and 'inventoryItems' in response:
                    page_items = response['inventoryItems']
                elif isinstance(response, list):
                    page_items = response
                
                if not page_items:
                    logger.info(f"No items found on page {iterations}, stopping pagination")
                    break
                
                logger.info(f"Found {len(page_items)} items on page {iterations}")
                all_items.extend(page_items)
                
                # If we got fewer items than page_size, we've reached the end
                if len(page_items) < page_size:
                    logger.info(f"Got {len(page_items)} < {page_size}, reached end of data")
                    break
                
                # Move to next page
                skip += page_size
                iterations += 1
            
            logger.info(f"=== PAGINATION COMPLETE: Fetched {len(all_items)} total items ===")
            return all_items
            
        except Exception as e:
            logger.error(f"Error fetching inventory items: {str(e)}")
            raise
    
    def sync_products(self):
        """Sync products from Manager.io to local database"""
        from crm.models import Product, Brand, ProductCategory
        
        # Get or create Manager.io brand for non-Mitsubishi products
        manager_brand, _ = Brand.objects.get_or_create(
            name='Manager.io Import',
            defaults={
                'is_mitsubishi': False,
                'is_active': True
            }
        )
        
        # Get Mitsubishi brand
        mitsubishi_brand, _ = Brand.objects.get_or_create(
            name='Mitsubishi Electric',
            defaults={
                'is_mitsubishi': True,
                'website': 'https://www.mitsubishielectric.com',
                'is_active': True
            }
        )
        
        created_count = 0
        updated_count = 0
        
        try:
            # Fetch all items from Manager.io
            all_items = self._fetch_all_inventory_items()
            
            if not all_items:
                return {
                    'created': 0,
                    'updated': 0,
                    'timestamp': timezone.now(),
                    'message': 'No items found in Manager.io'
                }
            
            for item in all_items:
                try:
                    # Extract item details
                    manager_id = item.get('id') or item.get('Key')
                    item_code = item.get('ItemCode') or item.get('Code', '')
                    item_name = item.get('ItemName') or item.get('Name', '')
                    
                    if not manager_id or not item_code:
                        continue
                    
                    # Determine if it's a Mitsubishi product (you can adjust this logic)
                    is_mitsubishi = False
                    brand = manager_brand
                    
                    # Check if item code suggests it's a Mitsubishi product
                    if any(prefix in item_code.upper() for prefix in ['FX', 'MR', 'QY', 'QX', 'FR-']):
                        is_mitsubishi = True
                        brand = mitsubishi_brand
                    
                    # Extract other fields
                    unit = item.get('UnitName') or 'piece'
                    quantity = self._safe_decimal(item.get('qtyOnHand') or item.get('qty', 0))
                    sales_price = self._extract_sales_price(item)
                    
                    # Determine category based on code prefix or create a default
                    category = self._get_or_create_category(item_code, item_name)
                    
                    # Create or update product
                    product_data = {
                        'name': item_name,
                        'brand': brand,
                        'model': item_code,
                        'category': category,
                        'description': item.get('Description', ''),
                        'price': sales_price,
                        'stock_quantity': int(quantity),
                        'is_active': True,
                        'is_from_api': True,
                        'mitsubishi_api_id': manager_id  # Store Manager.io ID here
                    }
                    
                    # Use item code as unique identifier for now
                    product, created = Product.objects.update_or_create(
                        sku=item_code,
                        defaults=product_data
                    )
                    
                    if created:
                        created_count += 1
                        logger.info(f"Created product: {item_name} ({item_code})")
                    else:
                        updated_count += 1
                        logger.info(f"Updated product: {item_name} ({item_code})")
                
                except Exception as e:
                    logger.error(f"Error processing item {item.get('ItemCode', 'Unknown')}: {str(e)}")
                    continue
            
            logger.info(f"Product sync completed: {created_count} created, {updated_count} updated")
            
            return {
                'created': created_count,
                'updated': updated_count,
                'timestamp': timezone.now(),
                'total_items': len(all_items)
            }
            
        except Exception as e:
            logger.error(f"Sync failed: {str(e)}")
            raise
    
    def _safe_decimal(self, value, default=0):
        """Safely convert value to Decimal"""
        if value is None:
            return Decimal(str(default))
        
        try:
            return Decimal(str(value))
        except (ValueError, TypeError):
            return Decimal(str(default))
    
    def _extract_sales_price(self, item):
        """Extract sales price from Manager.io item format"""
        # Try nested salePrice object format
        if 'salePrice' in item and isinstance(item['salePrice'], dict):
            if 'value' in item['salePrice']:
                return self._safe_decimal(item['salePrice']['value'])
        
        # Try direct fields
        for field in ['DefaultSalesUnitPrice', 'salesPrice', 'SalesPrice']:
            if field in item and item[field]:
                return self._safe_decimal(item[field])
        
        return Decimal('0')
    
    def _get_or_create_category(self, item_code, item_name):
        """Determine or create product category based on code/name"""
        from crm.models import ProductCategory
        
        code_upper = item_code.upper()
        
        # Mitsubishi product categories
        if code_upper.startswith('FX') or code_upper.startswith('Q'):
            category, _ = ProductCategory.objects.get_or_create(
                code='PLC',
                defaults={'name': 'Programmable Logic Controllers', 'is_active': True}
            )
        elif code_upper.startswith('FR-'):
            category, _ = ProductCategory.objects.get_or_create(
                code='VFD',
                defaults={'name': 'Variable Frequency Drives', 'is_active': True}
            )
        elif code_upper.startswith('MR-') or 'SERVO' in code_upper:
            category, _ = ProductCategory.objects.get_or_create(
                code='SERVO',
                defaults={'name': 'Servo Systems', 'is_active': True}
            )
        elif code_upper.startswith('GOT') or 'HMI' in code_upper:
            category, _ = ProductCategory.objects.get_or_create(
                code='HMI',
                defaults={'name': 'HMI & SCADA', 'is_active': True}
            )
        else:
            # Default category
            category, _ = ProductCategory.objects.get_or_create(
                code='OTHER',
                defaults={'name': 'Other Products', 'is_active': True}
            )
        
        return category
    
    def search_products(self, query):
        """Search products in Manager.io inventory"""
        try:
            # Fetch all items (Manager.io doesn't have direct search)
            all_items = self._fetch_all_inventory_items()
            
            # Filter items based on query
            query_lower = query.lower()
            matching_items = []
            
            for item in all_items:
                item_code = (item.get('ItemCode') or '').lower()
                item_name = (item.get('ItemName') or '').lower()
                
                if query_lower in item_code or query_lower in item_name:
                    matching_items.append(item)
            
            return matching_items[:50]  # Return max 50 results
            
        except Exception as e:
            logger.error(f"Error searching products: {str(e)}")
            return []
    
    def check_product_availability(self, sku):
        """Check real-time availability of a product in Manager.io"""
        try:
            # Fetch all items and find the specific one
            all_items = self._fetch_all_inventory_items()
            
            for item in all_items:
                if item.get('ItemCode') == sku:
                    return {
                        'available': True,
                        'quantity': int(self._safe_decimal(item.get('qtyOnHand', 0))),
                        'last_updated': timezone.now()
                    }
            
            return {
                'available': False,
                'quantity': 0,
                'last_updated': timezone.now()
            }
            
        except Exception as e:
            logger.error(f"Error checking availability for {sku}: {str(e)}")
            return None
    
    def get_product_pricing(self, sku, quantity=1):
        """Get pricing information for a product from Manager.io"""
        try:
            # Fetch all items and find the specific one
            all_items = self._fetch_all_inventory_items()
            
            for item in all_items:
                if item.get('ItemCode') == sku:
                    unit_price = self._extract_sales_price(item)
                    return {
                        'unit_price': float(unit_price),
                        'total_price': float(unit_price * Decimal(str(quantity))),
                        'currency': 'BDT',
                        'available_quantity': int(self._safe_decimal(item.get('qtyOnHand', 0)))
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching pricing for {sku}: {str(e)}")
            return None


# Utility functions for scheduled tasks

def sync_manager_products_task():
    """Task to sync Manager.io products (can be called by Celery or cron)"""
    try:
        client = ManagerAPIClient()
        result = client.sync_products()
        
        # Log sync result
        from crm.models import AuditLog
        AuditLog.objects.create(
            model_name='Product',
            object_id='SYNC',
            change_type='update',
            field_name='manager_sync',
            new_value=json.dumps(result),
            changed_by=None  # System action
        )
        
        return result
    except Exception as e:
        logger.error(f"Product sync task failed: {str(e)}")
        raise