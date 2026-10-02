from django.contrib import admin
from .models import Company, Storage, Supplier, Product, Supply, SupplyProduct, Sale, ProductSale

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


class ProductSaleInline(admin.TabularInline):
    model = ProductSale
    extra = 1

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    inlines = [ProductSaleInline]
    list_display = ['id', 'buyer_name', 'company', 'sale_date']
