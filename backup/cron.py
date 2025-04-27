import os
import time

from django.core import management
from backup.models import Backup

def run_backup():
    backup_name = f'backup_{time.time()}'
    backup = Backup(name=backup_name, was_automated=True)
    backup.save()

    management.call_command("dbbackup", "-o", backup_name)
