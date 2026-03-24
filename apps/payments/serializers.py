from .models import Payment 
from apps.orders.models import Order
from rest_framework.serializers import ModelSerializer,Serializer,ValidationError
from rest_framework import serializers
from django.conf import settings
import hmac
import hashlib


class PaymentInitiateSerializer(Serializer):
    '''
    Step-1 - This helps client to get razorpay_order_id and open razorpay payment modal
     client sends order_id and then it'll get back razorpay_order_id to open payment modal '''

    def validate(self,attrs):
        order_id = self.context['order_id']
        user = self.context['request'].user
        try:
            order = Order.objects.get(pk=order_id,customer=user)
        except Order.DoesNotExist:
            raise ValidationError('Order not Found')

        if order.is_paid:
            raise ValidationError('This Order is Already Paid')
        
        #COD orders dont need online payment for now
        #later I'll add similar feature like zomato/swiggy 
        #customer can pay online on delivery also known Pay on delivery 
        # only need a trigger from delivery agent
        if order.payment_method == Order.PaymentMethod.COD:
            raise ValidationError('COD  order don\'t need online payment')
        
        #cancelled order 
        if order.status == Order.Status.CANCELLED:
            raise ValidationError('Order is Cancelled,cannot be paid')
        
        self.context['order'] = order 
        return attrs

class PaymentInitiateResponseSerializer(Serializer):
    razorpay_order_id= serializers.CharField()
    razorpay_key_id = serializers.CharField()
    amount =  serializers.IntegerField()
    currency = serializers.CharField()
    order_id =  serializers.UUIDField()
    name = serializers.CharField()
    description =  serializers.CharField()   



class PaymentVerifySerializer(Serializer):
   '''
   Step-2 Verify the signature sent by client 
   '''
   razorpay_order_id = serializers.CharField()
   razorpay_payment_id = serializers.CharField()
   razorpay_signature =serializers.CharField()

   def validate(self,attrs):
       #fetch the payment records
        try:
           payment = Payment.objects.select_related('order').get(razorpay_order_id=attrs['razorpay_order_id'])
        except Payment.DoesNotExist:
           raise ValidationError('Payment Record not found')

        if payment.user!=self.context['request'].user:
            raise ValidationError('Payment Record not found')
        
        #check if already verify
        if payment.status == Payment.Status.SUCCESS:
            raise ValidationError('Payment Already Completed')
        
        #Signature Verification 
        #verify using razorpay Secret Key 
        msg  = f"{attrs['razorpay_order_id']}|{attrs['razorpay_payment_id']}"
        signature = hmac.new(
            key=settings.RAZORPAY_KEY_SECRET.encode(),
            msg= msg.encode(),
            digestmod=hashlib.sha256,
        ).hexdigest()

        if signature != attrs['razorpay_signature']:
            #mark payment as failed
            payment.status = Payment.Status.FAILED
            payment.failure_reason = 'Signature Verification Failed'
            payment.save(update_fields=['status','failure_reason'])
            raise ValidationError('Payment Verification Failed')
        
        self.context['payment']=payment
        return attrs



class PaymentSerializer(ModelSerializer):
    class Meta:
        model = Payment
        fields = ('id','razorpay_payment_id','razorpay_order_id',
                  'amount','status','created_at')
                  