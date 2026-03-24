from django.urls import path
from .views import PaymentDetailView,PaymentVerifyView,PaymentInitiateView

app_name = 'payments'
urlpatterns = [
    path('initiate/<uuid:order_id>/',PaymentInitiateView.as_view(),name='payment-initiate'),
    path('verify/',PaymentVerifyView.as_view(),name='payment-verify'),
    path('<uuid:order_id>/',PaymentDetailView.as_view(),name='payment-details'),
]
