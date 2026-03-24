from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display   = ("razorpay_order_id", "user", "order", "amount", "status", "created_at")
    list_filter    = ("status",)
    search_fields  = ("razorpay_order_id", "razorpay_payment_id", "user__email")
    ordering       = ("-created_at",)
    readonly_fields = (
        "id", "order", "user", "razorpay_payment_id", "razorpay_signature",
        "amount", "created_at", "updated_at",'razorpay_order_id'
    )
    fieldsets = (
        ("Order",    {"fields": ("id", "order", "user", "amount")}),
        ("Razorpay", {"fields": ("razorpay_order_id", "razorpay_payment_id")}),
        ("Status",   {"fields": ("status", "failure_reason")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
