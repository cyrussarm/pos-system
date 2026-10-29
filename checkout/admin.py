from django.contrib import admin
from .models import Product, Sale, SaleItem


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sell_price', 'stock', 'low_stock_threshold', 'is_active', 'is_low_stock')
    list_filter = ('is_active',)
    search_fields = ('name',)
    list_editable = ('sell_price', 'stock', 'low_stock_threshold', 'is_active')

    @admin.display(boolean=True, description="موجودی کم؟")
    def is_low_stock(self, obj):
        return obj.is_low_stock


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ('unit_price', 'line_total')

    @admin.display(description="جمع ردیف")
    def line_total(self, obj):
        return obj.line_total


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'cashier', 'created_at', 'total_amount', 'is_voided')
    list_filter = ('is_voided', 'cashier', 'created_at')
    search_fields = ('id', 'cashier__username')
    readonly_fields = ('created_at',)
    inlines = [SaleItemInline]
