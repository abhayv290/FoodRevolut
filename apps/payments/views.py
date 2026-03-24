import razorpay 
from django.conf import settings 
from django.db import transaction 
from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from core.permissions import IsCustomer
from apps.orders.models import Order,OrderStatusHistory
from .models import Payment 
from .serializers import PaymentSerializer,PaymentInitiateSerializer,PaymentVerifySerializer, PaymentInitiateResponseSerializer



#Creating Razorpay Client 
razorpay_client =  razorpay.Client(auth=(
    settings.RAZORPAY_KEY_ID,settings.RAZORPAY_KEY_SECRET
))



@extend_schema(tags=['Payments'],request=PaymentInitiateSerializer,responses=PaymentInitiateResponseSerializer)
class PaymentInitiateView(APIView):
    '''
    POST - payments/initiate/<uuid:order_id>
    Step-1- get the order_id from client, Creates razorpay order,
    send back razorpay_order_id  ,this id use by client to 
    open razorpay payment modal 

    Razorpay requirement 
    amount in paise 
    currency INR
    receipt -> internal order id for reference

    '''
    permission_classes  = [IsAuthenticated,IsCustomer]

    def post(self,request,order_id):
        serializer = PaymentInitiateSerializer(
            data=request.data,
            context = {'request':request,'order_id':order_id}
        )
        serializer.is_valid(raise_exception=True)
        order = serializer.context['order']

        try:
            razorpay_order = razorpay_client.order.create({ #type:ignore
                'amount' : int(order.total_amount*100),
                'currency' : 'INR', 
                'notes' : {
                    'order_id':str(order.id),
                    'customer_id' : str(request.user.id)
                }
            })
        except Exception as e:
            return Response({
                'error' : 'Payment Gateway Error , Please try again'
            },status=status.HTTP_502_BAD_GATEWAY)
        
        #Store Payment Record 
        payment =Payment.objects.create(
            order = order,
            user = request.user,
            razorpay_order_id  = razorpay_order['id'],
            amount = order.total_amount,
            status = Payment.Status.PENDING  
        )
        # this response needed to open razorpay modal 
        return Response({
            'razorpay_order_id' : razorpay_order['id'],
            'razorpay_key_id' : settings.RAZORPAY_KEY_ID,
            'amount' : razorpay_order['amount'],
            'currency' : 'INR',
            'order_id' : str(order.id),
            'name' : 'request.user.name',
            'description' : f"Order from {order.restaurant.name}"
        },status=status.HTTP_201_CREATED)
    


@extend_schema(tags=['Payments'], request=PaymentVerifySerializer , responses=PaymentSerializer)
class PaymentVerifyView(APIView):
    '''
    POST /payment/verify/
    body = {razorpay_order_id,razorpay_payment_id,razorpay_signature}
    
    Step-2 after getting razorpay_order from server ,client opens  the modal to pay
    once payment done , client send these three back, 
    we verify the signature , if verification success - mark payment as paid
    else send an failed error

    '''
    permission_classes = [IsAuthenticated,IsCustomer]

    def post(self,request):
        serializer =  PaymentVerifySerializer(
            data=request.data,
            context= {'request':request}
        )
        serializer.is_valid(raise_exception=True)
        payment = serializer.context['payment']

        #mark payment success and order paid atomically
        with transaction.atomic():
            payment.razorpay_payment_id = request.data['razorpay_payment_id']
            payment.razorpay_signature = request.data['razorpay_signature']
            payment.status = Payment.Status.SUCCESS
            
            payment.save(update_fields=['razorpay_payment_id',
                        'razorpay_signature','status','updated_at'])

            order = payment.order
            order.is_paid = True
            order.save(update_fields=['is_paid'])

            #record in status history 
            OrderStatusHistory.objects.create(
                order=order,
                status=order.status,
                changed_by = request.user,
                note=f'Payment Confirmed,Razorpay Id:{payment.razorpay_payment_id}'
            )

        return Response({
            'message' : 'Payment Successful',
            'order_id' : str(order.id),
            'payment' : PaymentSerializer(payment).data
        },status=status.HTTP_202_ACCEPTED)
    
@extend_schema(tags=['Payments'],responses=PaymentSerializer)
class PaymentDetailView(APIView):
    '''
    GET payment/order_id
    get the full info of payment of an order'''

    permission_classes = [IsAuthenticated,IsCustomer]

    def get(self,request,order_id):
        try:
            payment = Payment.objects.get(user=request.user,order__id=order_id)
        except Payment.DoesNotExist:
            return Response({
                'error':'Payment Record not Found',
            },status=status.HTTP_404_NOT_FOUND)

        return Response(PaymentSerializer(payment).data)

#TODO
class RazorpayWebhookView(APIView):
    '''
    POST - payment/webhook/
    we'll add  event based verification using razorpay webhook 
    this runs on razorpay server (call by razorpay), 
    this tackles the problem of, payment initiated and paid , but 
    somehow browser/app crashed due to network error or user forced back button
    and payment didn't registered because in this case client never called 
    payment/verify/ 
    
    Implementation
    1- Verify webhook signature using RAZORPAY_WEBHOOK_SECRET
    2- Check event.type  - 'payment.captured' means success
    3- find payment record by razorpay_payment_id 
    4- if still pending mark success(idempotency check)
    '''
    
    permission_classes=[AllowAny]


    def post(self,request):
        return Response({'message':'Payment Success'},status=status.HTTP_200_OK)
    



