from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Product(models.Model):
    
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="نام کالا"
    )
    sell_price = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        verbose_name="قیمت فروش (تومان)"
    )
    stock = models.IntegerField(
        default=0,
        verbose_name="موجودی فعلی"
    )
    low_stock_threshold = models.IntegerField(
        default=5,
        verbose_name="آستانه هشدار موجودی کم"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="فعال"
    )

    class Meta:
        verbose_name = "کالا"
        verbose_name_plural = "کالاها"
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def is_low_stock(self):
        """آیا موجودی به آستانه هشدار رسیده است؟"""
        return self.stock <= self.low_stock_threshold

class Sale(models.Model):
    """
    مدل سفارش فروش (سربرگ فاکتور).
    هر بار که صندوق‌دار یک فروش را ثبت می‌کند، یک رکورد اینجا ساخته می‌شود.
    """
    cashier = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name="صندوق‌دار"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="زمان فروش"
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        verbose_name="مبلغ کل (تومان)"
    )
    is_voided = models.BooleanField(
        default=False,
        verbose_name="ابطال شده"
    )

    class Meta:
        verbose_name = "سفارش فروش"
        verbose_name_plural = "سفارش‌های فروش"
        ordering = ['-created_at']

    def __str__(self):
        return f"فاکتور {self.id} - {self.created_at:%Y-%m-%d %H:%M}"

class SaleItem(models.Model):
    """
    مدل جزئیات سفارش (هر ردیف فاکتور).
    قلب سیستم: قیمت واحد را در لحظه فروش ذخیره می‌کند تا
    تغییر قیمت‌های بعدی، گزارش‌های تاریخی را خراب نکند.
    """
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="فاکتور"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        verbose_name="کالا"
    )
    quantity = models.PositiveIntegerField(
        verbose_name="تعداد"
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        verbose_name="قیمت واحد در لحظه فروش (تومان)"
    )

    class Meta:
        verbose_name = "جزئیات سفارش"
        verbose_name_plural = "جزئیات سفارش‌ها"

    def __str__(self):
        return f"{self.product.name} × {self.quantity}"

    @property
    def line_total(self):
        """جمع این ردیف: تعداد × قیمت واحد"""
        if self.quantity is None or self.unit_price is None:
            return 0
        return self.quantity * self.unit_price