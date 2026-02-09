from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.contrib.contenttypes.models import ContentType

from .models import Order, OrderItem, RefundRequest
from .serializers import OrderSerializer, CreateOrderItemSerializer, RefundRequestSerializer
from product.models import ClothingProduct
from cart.models import Cart, CartItem


def calculate_loyalty_points(amount):
    try:
        pts = int(float(amount) // 10)
        return max(pts, 0)
    except (ValueError, TypeError):
        return 0


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def place_order(request):
    try:
        user = request.user
        use_cart = request.data.get('use_cart', True)
        shipping_address = request.data.get('shipping_address', '') or getattr(user, 'address', '')

        items_input = []

        if use_cart:
            cart, _ = Cart.objects.get_or_create(user=user)
            cart_items = cart.items.all()
            if not cart_items.exists():
                return Response(
                    {'error': 'Cart is empty. Add items before placing order.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            for ci in cart_items:
                try:
                    product = ci.product
                    if product:
                        items_input.append({
                            'product_id': product.id,
                            'quantity': ci.quantity
                        })
                except Exception:
                    pass

            if not items_input:
                return Response(
                    {'error': 'No valid products found in cart.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            items_input = request.data.get('items', [])
            if not items_input:
                return Response(
                    {'error': 'No items provided.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        validated_items = []
        for item_data in items_input:
            serializer = CreateOrderItemSerializer(data=item_data)
            if not serializer.is_valid():
                return Response(
                    {'error': 'Invalid item data', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )

            data = serializer.validated_data
            product_id = data['product_id']
            qty = data['quantity']

            try:
                product = ClothingProduct.objects.get(id=product_id)
            except ClothingProduct.DoesNotExist:
                return Response(
                    {'error': f'Product with id {product_id} not found'},
                    status=status.HTTP_404_NOT_FOUND
                )

            if product.stock < qty:
                return Response(
                    {'error': f'Not enough stock for {product.name}. Available: {product.stock}, Requested: {qty}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            validated_items.append((product, qty))

        order = Order.objects.create(
            user=user,
            shipping_address=shipping_address,
            status='pending'
        )

        total_amount = 0
        content_type = ContentType.objects.get_for_model(ClothingProduct)

        for product, qty in validated_items:
            order_item = OrderItem.objects.create(
                order=order,
                content_type=content_type,
                object_id=product.id,
                product_name=product.name,
                price_at_purchase=product.price,
                quantity=qty
            )
            subtotal = order_item.calculate_subtotal()
            total_amount += subtotal

            product.stock = max(0, product.stock - qty)
            product.save(update_fields=['stock'])

        order.total_amount = total_amount
        order.loyalty_points_earned = calculate_loyalty_points(total_amount)
        order.save(update_fields=['total_amount', 'loyalty_points_earned'])

        if use_cart:
            cart.items.all().delete()

        serializer = OrderSerializer(order, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response(
            {'error': 'Failed to place order', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([])
def view_order(request, order_id):
    try:
        order = get_object_or_404(Order, id=order_id)
        serializer = OrderSerializer(order, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': 'Failed to retrieve order', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_history(request):
    try:
        orders = Order.objects.filter(user=request.user).order_by('-order_date')
        serializer = OrderSerializer(orders, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': 'Failed to retrieve order history', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def cancel_order(request, order_id):
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)

        if order.status in ['cancelled', 'refunded', 'delivered', 'shipped']:
            return Response(
                {'error': f'Cannot cancel order in {order.status} status.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        for item in order.items.all():
            if item.product:
                product = item.product
                product.stock = product.stock + item.quantity
                product.save(update_fields=['stock'])

        order.status = 'cancelled'
        order.save(update_fields=['status'])

        return Response(
            {'message': 'Order cancelled successfully', 'order_id': order.id, 'status': order.status},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'error': 'Failed to cancel order', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def request_refund(request, order_id):
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)

        payment_status = (order.status or '').lower()
        is_payment_approved = payment_status in ['paid', 'processing', 'shipped', 'delivered']

        if not is_payment_approved:
            return Response(
                {'error': 'Only orders with paid/processing payment status can request refunds. Current status: ' + payment_status},
                status=status.HTTP_400_BAD_REQUEST
            )

        if order.status and order.status.lower() == 'refunded':
            return Response(
                {'error': 'This order has already been refunded.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('reason', '').strip() or 'Customer requested refund'

        refund = RefundRequest.objects.create(
            order=order,
            user=request.user,
            reason=reason,
            status='pending'
        )

        serializer = RefundRequestSerializer(refund)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response(
            {'error': 'Failed to create refund request', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def generate_invoice(request, order_id):
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        order.calculate_total()

        invoice = {
            'invoice_id': f'INV-{order.id}',
            'order_id': order.id,
            'date': order.order_date.isoformat() if order.order_date else None,
            'customer': {
                'id': request.user.id,
                'email': request.user.email,
                'username': request.user.username,
            },
            'shipping_address': order.shipping_address,
            'items': [
                {
                    'product_name': item.product_name,
                    'unit_price': float(item.price_at_purchase),
                    'quantity': item.quantity,
                    'subtotal': float(item.calculate_subtotal())
                }
                for item in order.items.all()
            ],
            'total': float(order.total_amount),
            'loyalty_points_earned': order.loyalty_points_earned,
            'order_status': order.status
        }

        return Response(invoice, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': 'Failed to generate invoice', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_list_orders(request):
    try:
        orders = Order.objects.all().order_by('-order_date')
        serializer = OrderSerializer(orders, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': 'Failed to retrieve orders', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAdminUser])
@transaction.atomic
def admin_update_order_status(request, order_id):
    try:
        order = get_object_or_404(Order, id=order_id)
        new_status = request.data.get('status', '').strip()

        if not new_status:
            return Response(
                {'error': 'status is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        valid_statuses = dict(Order.STATUS_CHOICES).keys()
        if new_status not in valid_statuses:
            return Response(
                {'error': f'Invalid status. Valid options: {", ".join(valid_statuses)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        old_status = order.status
        order.status = new_status
        order.save(update_fields=['status'])

        return Response(
            {
                'message': 'Order status updated successfully',
                'order_id': order.id,
                'old_status': old_status,
                'new_status': order.status
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'error': 'Failed to update order status', 'detail': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
