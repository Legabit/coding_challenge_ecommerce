import uuid
from decimal import Decimal
from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from orders.models import Order, OrderItem
from orders.serializers import CheckoutSerializer, OrderSerializer
from products.models import Product


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Order.objects.prefetch_related("items").all().order_by("-created_at")
    serializer_class = OrderSerializer

    @action(detail=False, methods=["post"], url_path="checkout")
    def checkout(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data
        items_data = validated_data["items"]
        customer_name = validated_data["customer_name"]
        customer_email = validated_data["customer_email"]
        simulate_failure = validated_data.get("simulate_failure", False)

        product_quantities = {}
        for item in items_data:
            pid = item["product_id"]
            qty = item["quantity"]
            product_quantities[pid] = product_quantities.get(pid, 0) + qty

        product_ids = list(product_quantities.keys())

        try:
            with transaction.atomic():
                locked_products = Product.objects.select_for_update().filter(id__in=product_ids)
                product_map = {p.id: p for p in locked_products}

                missing_ids = set(product_ids) - set(product_map.keys())
                if missing_ids:
                    return Response(
                        {"detail": f"Products with IDs {list(missing_ids)} do not exist."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                insufficient_stock_errors = []
                for pid, requested_qty in product_quantities.items():
                    product = product_map[pid]
                    if product.stock < requested_qty:
                        insufficient_stock_errors.append(
                            f"Product '{product.name}' (SKU: {product.sku}) has only {product.stock} left (requested: {requested_qty})."
                        )

                if insufficient_stock_errors:
                    return Response(
                        {"detail": "Stock validation failed.", "errors": insufficient_stock_errors},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                if simulate_failure:
                    return Response(
                        {
                            "detail": "Payment simulation declined the transaction.",
                            "status": Order.STATUS_FAILED,
                            "error_code": "CARD_DECLINED_SIMULATED"
                        },
                        status=status.HTTP_402_PAYMENT_REQUIRED
                    )

                total_amount = Decimal("0.00")
                total_weight_kg = Decimal("0.000")
                order_items_to_create = []

                for pid, requested_qty in product_quantities.items():
                    product = product_map[pid]
                    product.stock -= requested_qty
                    product.save(update_fields=["stock", "updated_at"])

                    item_subtotal = (product.price * requested_qty).quantize(Decimal("0.01"))
                    total_amount += item_subtotal
                    total_weight_kg += (product.weight_kg * requested_qty).quantize(Decimal("0.001"))

                    order_items_to_create.append({
                        "product": product,
                        "product_name": product.name,
                        "product_sku": product.sku,
                        "quantity": requested_qty,
                        "unit_price": product.price,
                        "subtotal": item_subtotal,
                    })

                order = Order.objects.create(
                    customer_name=customer_name,
                    customer_email=customer_email,
                    total_amount=total_amount,
                    total_weight_kg=total_weight_kg,
                    payment_status=Order.STATUS_SUCCESS,
                    payment_transaction_id=f"TXN-SIM-{uuid.uuid4().hex[:12].upper()}"
                )

                for item_dict in order_items_to_create:
                    OrderItem.objects.create(order=order, **item_dict)

                return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"detail": f"An error occurred during checkout: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
