from django import forms
from .models import Product


class SaleItemForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True),
        label="کالا",
        empty_label="--- انتخاب کالا ---"
    )
    quantity = forms.IntegerField(
        min_value=1,
        label="تعداد",
        widget=forms.NumberInput(attrs={'min': 1, 'value': 1})
    )