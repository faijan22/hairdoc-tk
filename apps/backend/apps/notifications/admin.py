from django.contrib import admin

from .models import EmailDelivery, Notification, PushDelivery, PushDevice


@admin.register(PushDevice)
class PushDeviceAdmin(admin.ModelAdmin):
    list_display = ("user", "platform", "active", "last_seen_at")
    readonly_fields = tuple(field.name for field in PushDevice._meta.fields)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "kind", "read_at", "created_at")
    readonly_fields = tuple(field.name for field in Notification._meta.fields)


@admin.register(PushDelivery)
class PushDeliveryAdmin(admin.ModelAdmin):
    list_display = ("notification", "device", "status", "attempt_count", "last_attempt_at")
    readonly_fields = tuple(field.name for field in PushDelivery._meta.fields)


@admin.register(EmailDelivery)
class EmailDeliveryAdmin(admin.ModelAdmin):
    list_display = ("notification", "status", "attempt_count", "sent_at")
    readonly_fields = tuple(field.name for field in EmailDelivery._meta.fields)
