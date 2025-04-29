import os
import shutil
from django.contrib import admin

import subprocess

import os
from backup.models import Backup
from django.contrib import messages

@admin.action(description="Restore selected backup")
def restore_backup(modeladmin, request, queryset):
    if queryset.count() == 1:
        existing_backups = list(Backup.objects.all())

        backup = queryset.first()
        backup_path = os.path.join(os.environ['BACKUP_DIR'], backup.name)
        shutil.copy2(f"{backup_path}.sqlite3", os.environ['DB_PATH'])

        Backup.objects.all().delete()
        for backup in existing_backups:
            backup.save()
    elif queryset.count() > 1:
        messages.error(request, "Too many backups selected")
    else:
        messages.error(request, "No backups selected")

# Register your models here.
class BackupAdmin(admin.ModelAdmin):
    list_display = ["name", "was_automated", "backup_date"]
    list_filter = ["name", "backup_date"]
    actions = [restore_backup]

    def has_change_permission(self, request, obj=None):
        return False

    def add_view(self, request, form_url="", extra_context=None):
        self.exclude = ["was_automated"]
        return super().add_view(request, form_url, extra_context)

    def save_model(self, request, obj, form, change):
        backup_path = os.path.join(os.environ['BACKUP_DIR'], obj.name)
        # Create BACKUP_DIR if it doesn't exist
        os.makedirs(os.environ['BACKUP_DIR'], exist_ok=True)
        shutil.copy2(os.environ['DB_PATH'], f"{backup_path}.sqlite3")
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        backup_path = os.path.join(os.environ['BACKUP_DIR'], obj.name)
        os.remove(f"{backup_path}.sqlite3")
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for backup in queryset:
            backup_path = os.path.join(os.environ['BACKUP_DIR'], backup.name)
            os.remove(f"{backup_path}.sqlite3")

        super().delete_queryset(request, queryset)

admin.site.register(Backup, BackupAdmin)