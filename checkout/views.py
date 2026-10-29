from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction, models
from decimal import Decimal

from .models import Product, Sale, SaleItem
from .forms import SaleItemForm

from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy

from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.db.models import Sum, Count
from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from functools import wraps
from django.core.exceptions import PermissionDenied

import csv
from django.http import HttpResponse

def manager_required(view_func):
    """فقط کاربران Staff (مدیر) اجازه دسترسی دارند؛ در غیر این صورت ۴۰۳."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped


@login_required
def checkout(request):
    products = Product.objects.filter(is_active=True).order_by('name')

    if request.method == 'POST':
        # دیکشنری product_id -> quantity از فرم POST
        # چون ۵ کالا داریم، فرم را ساده نگه می‌داریم: برای هر کالا یک فیلد quantity
        selected_items = []

        try:
            with transaction.atomic():
                total = Decimal('0')

                for product in products:
                    qty_str = request.POST.get(f'qty_{product.id}')
                    if not qty_str:
                        continue
                    qty = int(qty_str)
                    if qty <= 0:
                        continue

                    # قفل کردن ردیف کالا برای جلوگیری از همزمانی
                    locked = Product.objects.select_for_update().get(pk=product.pk)
                    if locked.stock < qty:
                        raise ValueError(
                            f"موجودی «{locked.name}» کافی نیست. "
                            f"موجودی فعلی: {locked.stock}"
                        )
                    selected_items.append((locked, qty))

                if not selected_items:
                    raise ValueError("هیچ کالایی انتخاب نشده است.")

                # ساخت فاکتور
                sale = Sale.objects.create(cashier=request.user, total_amount=0)

                for product, qty in selected_items:
                    SaleItem.objects.create(
                        sale=sale,
                        product=product,
                        quantity=qty,
                        unit_price=product.sell_price,
                    )
                    total += product.sell_price * qty

                    # کاهش موجودی
                    product.stock -= qty
                    product.save(update_fields=['stock'])

                sale.total_amount = total
                sale.save(update_fields=['total_amount'])

        except ValueError as e:
            messages.error(request, str(e))
        else:
            messages.success(
                request,
                f"فروش ثبت شد. شماره فاکتور: {sale.id} — مبلغ کل: {total:,} تومان"
            )
            return redirect('checkout')

    return render(request, 'checkout/checkout.html', {
        'products': products,
    })

class CashierLoginView(LoginView):
    template_name = 'checkout/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('checkout')

@manager_required
def report(request):
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    def sum_sales(qs):
        return qs.filter(is_voided=False).aggregate(total=Sum('total_amount'))['total'] or 0

    today_sales = sum_sales(Sale.objects.filter(created_at__gte=today_start))
    week_sales = sum_sales(Sale.objects.filter(created_at__gte=week_start))

    # پرفروش‌ترین کالاها در ۷ روز اخیر
    top_products = (
        SaleItem.objects
        .filter(sale__created_at__gte=week_start, sale__is_voided=False)
        .values('product__name')
        .annotate(qty=Sum('quantity'))
        .order_by('-qty')[:5]
    )

    # کالاهای کم‌موجود
    low_stock = Product.objects.filter(is_active=True, stock__lte=models.F('low_stock_threshold'))

    # تعداد فاکتورهای امروز
    today_count = Sale.objects.filter(created_at__gte=today_start, is_voided=False).count()

    return render(request, 'checkout/report.html', {
        'today_sales': today_sales,
        'week_sales': week_sales,
        'today_count': today_count,
        'top_products': top_products,
        'low_stock': low_stock,
    })

@manager_required
@require_POST
def void_sale(request, sale_id):
    sale = get_object_or_404(Sale, pk=sale_id)

    if sale.is_voided:
        messages.error(request, "این فاکتور قبلاً ابطال شده است.")
        return redirect('sale_list')

    try:
        with transaction.atomic():
            # برگرداندن موجودی هر قلم
            for item in sale.items.select_related('product'):
                product = Product.objects.select_for_update().get(pk=item.product.pk)
                product.stock += item.quantity
                product.save(update_fields=['stock'])

            sale.is_voided = True
            sale.save(update_fields=['is_voided'])
    except Exception as e:
        messages.error(request, f"خطا در ابطال فاکتور: {e}")
    else:
        messages.success(request, f"فاکتور شماره {sale.id} ابطال شد و موجودی برگشت.")

    return redirect('sale_list')

@manager_required
def sale_list(request):
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # پیش‌فرض: امروز. اگر پارامتر ?all=1 بود، همه
    show_all = request.GET.get('all') == '1'
    if show_all:
        sales = Sale.objects.select_related('cashier').order_by('-created_at')[:100]
    else:
        sales = Sale.objects.select_related('cashier').filter(
            created_at__gte=today_start
        ).order_by('-created_at')

    return render(request, 'checkout/sale_list.html', {
        'sales': sales,
        'show_all': show_all,
    })

@manager_required
def report_csv(request):
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    # پارامتر ?range=today یا ?range=week
    rng = request.GET.get('range', 'today')
    if rng == 'week':
        start = week_start
        label = "هفته"
    else:
        start = today_start
        label = "امروز"

    sales = Sale.objects.select_related('cashier').filter(
        created_at__gte=start
    ).order_by('-created_at')

    # پاسخ CSV با BOM برای نمایش درست فارسی در اکسل
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="report_{rng}.csv"'
    response.write('\ufeff')  # BOM برای اکسل

    writer = csv.writer(response)
    writer.writerow(['شماره فاکتور', 'زمان', 'صندوق‌دار', 'مبلغ کل (تومان)', 'وضعیت', 'اقلام'])

    for sale in sales:
        items_str = ' | '.join(
            f"{item.product.name} × {item.quantity}"
            for item in sale.items.select_related('product')
        )
        writer.writerow([
            sale.id,
            sale.created_at.strftime('%Y-%m-%d %H:%M'),
            sale.cashier.username,
            int(sale.total_amount),
            'ابطال شده' if sale.is_voided else 'فعال',
            items_str,
        ])

    # ردیف جمع کل در انتها
    total = sum(int(s.total_amount) for s in sales if not s.is_voided)
    writer.writerow([])
    writer.writerow(['', '', '', total, f'جمع ({label})', ''])

    return response

def custom_403(request, exception=None):
    return render(request, 'checkout/403.html', status=403)

def custom_404(request, exception=None):
    return render(request, 'checkout/404.html', status=404)