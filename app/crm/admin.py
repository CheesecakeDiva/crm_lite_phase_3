from django.contrib import admin
from .models import Company, Storage, Supplier, Product, Supply, SupplyProduct

class SupplyProductInline(admin.TabularInline):
    model = SupplyProduct
    extra = 1

@admin.register(Supply)
class SupplyAdmin(admin.ModelAdmin):
    inlines = [SupplyProductInline]

admin.site.register(Company)
admin.site.register(Storage)
admin.site.register(Supplier)
admin.site.register(Product)
