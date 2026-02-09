from rest_framework import serializers
from .models import Order, OrderItem, RefundRequest
from product.serializers import ClothingProductSerializer


class OrderItemSerializer(serializers.ModelSerializer):
    product = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'price_at_purchase', 'quantity']
        read_only_fields = ['product', 'product_name', 'price_at_purchase']

    def get_product(self, obj):
        return ClothingProductSerializer(obj.product, context=self.context).data


class CreateOrderItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    payment_verification_status = serializers.SerializerMethodField()
    track_order_status = serializers.SerializerMethodField()

    status = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id',
            'user',
            'order_date',
            'status',
            'payment_status',
            'total_amount',
            'shipping_address',
            'items',
            'loyalty_points_earned',
            'payment_verification_status',
            'track_order_status'
        ]
        read_only_fields = [
            'id',
            'user',
            'order_date',
            'status',
            'payment_status',
            'total_amount',
            'items',
            'loyalty_points_earned'
        ]

    def get_payment_verification_status(self, obj):
        if getattr(obj, 'track_order_status', '') == 'Order cancel and refunded':
            return '-'

        payment = getattr(obj, 'payment_record', None)
        if payment is None:
            return 'waiting'
        return getattr(payment, 'status', 'waiting')

    def get_track_order_status(self, obj):
        track = getattr(obj, 'track_order_status', '-')
        if track and track != '-':
            return track

        payment = getattr(obj, 'payment_record', None)
        if payment and getattr(payment, 'status', '').lower() == 'approved':
            return 'shipping'

        return track

    def get_status(self, obj):
        return getattr(obj, 'track_order_status', '-')

    def get_payment_status(self, obj):
        payment = getattr(obj, 'payment_record', None)
        if payment is None:
            return 'waiting'
        return getattr(payment, 'status', 'waiting')


class RefundRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefundRequest
        fields = ['id', 'order', 'user', 'reason', 'created_at', 'status', 'admin_note']
        read_only_fields = ['id', 'user', 'created_at', 'status', 'admin_note']
