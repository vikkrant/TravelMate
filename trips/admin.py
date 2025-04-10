from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User, Group
from .models import Trip

class TripInline(admin.TabularInline):
    model = Trip
    extra = 0
    readonly_fields = ('destination', 'start_date', 'end_date', 'created_at', 'updated_at')
    can_delete = False
    show_change_link = True
    verbose_name_plural = 'User Trips'
    fields = ('destination', 'start_date', 'end_date', 'created_at', 'updated_at')
    ordering = ('-created_at',)

    def has_add_permission(self, request, obj=None):
        return False

class CustomUserAdmin(UserAdmin):
    inlines = [TripInline]
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    
    # Reorganize the fieldsets to show trips right after personal info
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    def get_inline_instances(self, request, obj=None):
        # Get the inline instances
        inline_instances = super().get_inline_instances(request, obj)
        # Move the TripInline to the top of the list
        trip_inline = next((inline for inline in inline_instances if isinstance(inline, TripInline)), None)
        if trip_inline:
            inline_instances.remove(trip_inline)
            inline_instances.insert(0, trip_inline)
        return inline_instances

# Unregister the default User and Group admin
admin.site.unregister(User)
admin.site.unregister(Group)
admin.site.register(User, CustomUserAdmin)

@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('user', 'destination', 'start_date', 'end_date', 'created_at')
    list_filter = ('user', 'start_date', 'end_date')
    search_fields = ('user__username', 'destination')
    readonly_fields = ('created_at', 'updated_at') 