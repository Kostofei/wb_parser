from django.contrib import admin

from parser.models import Item


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    pass
