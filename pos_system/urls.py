"""
URL configuration for pos_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""


from django.contrib import admin
from django.urls import path
from django.contrib.auth.views import LogoutView
from checkout import views as checkout_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', checkout_views.checkout, name='checkout'),
    path('login/', checkout_views.CashierLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('report/', checkout_views.report, name='report'),
    path('report/csv/', checkout_views.report_csv, name='report_csv'),
    path('sales/', checkout_views.sale_list, name='sale_list'),
    path('sales/<int:sale_id>/void/', checkout_views.void_sale, name='void_sale'),    
]


handler403 = 'checkout.views.custom_403'
handler404 = 'checkout.views.custom_404'