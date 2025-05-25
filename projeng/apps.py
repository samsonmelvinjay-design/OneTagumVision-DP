from django.apps import AppConfig

class ProjengConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'projeng'

    def ready(self):
        import projeng.signals 