# crm/apps.py - CRM Application Configuration

from django.apps import AppConfig


class CrmConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'crm'
    verbose_name = 'SISL CRM'
    
   # def ready(self):
        # Import signals when app is ready
    #    import crm.signals