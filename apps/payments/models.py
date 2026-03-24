import uuid 
from django.db import models 
from django.conf import settings
from apps.orders.models import Order
from django.utils.translation import gettext_lazy as _


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING' ,'Pending'
        SUCCESS = 'SUCCESS' ,'Success',
        FAILED  = 'FAILED' , 'Failed',
        REFUNDED = 'REFUNDED' , 'Refunded'

    id = models.UUIDField(_("paymentId"),primary_key=True,default=uuid.uuid4,editable=False)
    order = models.OneToOneField(Order,verbose_name=_('Order'),on_delete=models.PROTECT,related_name='payment')
    user = models.ForeignKey(settings.AUTH_USER_MODEL,verbose_name=_('User'),on_delete=models.PROTECT,related_name='payments')


    '''we are using RAZORPAY  payment service
    razorpay order_id - we'll create
    razorpay payment_id - returned by razorpay after payment done
    razorpay signature - use to verify the payment
       '''
    
    razorpay_order_id =  models.CharField(_("Razorpay OrderId"), max_length=100,unique=True)
    razorpay_payment_id = models.CharField(_('Razorpay Payment Id'),max_length=100,blank=True)
    razorpay_signature = models.CharField(_('Razorpay Signature'),max_length=250,blank=True)

    amount  =  models.DecimalField(_('Amount'),max_digits=8,decimal_places=2)
    status  = models.CharField(_("Payment Status"), max_length=15,choices=Status.choices,default=Status.PENDING,db_index=True)
    # this helps with debugging if payment failed(razorpay returns an error code for failure)
    failure_reason = models.TextField(_("Failure Reason"))

    created_at = models.DateTimeField(_('CreatedAt'),auto_now_add=True)
    updated_at = models.DateTimeField(_('UpdatedAt'),auto_now=True)

    class Meta:
        ordering  = ['-created_at']

    def __str__(self):
        return f"Payment {self.razorpay_order_id} - {self.status}"    






