from django.db import models

# Create your models here.
class Backup(models.Model):
    name = models.CharField(max_length=100)
    was_automated = models.BooleanField(default=False)
    backup_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Backup '{self.name}' at {self.backup_date}"