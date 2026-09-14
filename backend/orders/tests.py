from decimal import Decimal
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from orders.models import Order
from products.models import Category, Product


class CheckoutAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name="Tech")
        self.product1 = Product.objects.create(
            name="Laptop",
            sku="LAP-001",
            price=Decimal("1200.00"),
            stock=5,
            weight_kg=Decimal("1.800"),
            category=self.category
        )
        self.product2 = Product.objects.create(
            name="Wireless Mouse",
            sku="MOU-002",
            price=Decimal("25.00"),
            stock=10,
            weight_kg=Decimal("0.120"),
            category=self.category
        )

    def test_successful_checkout(self):
        payload = {
            "customer_name": "Alice Developer",
            "customer_email": "alice@example.com",
            "items": [
                {"product_id": self.product1.id, "quantity": 2},
                {"product_id": self.product2.id, "quantity": 1}
            ]
        }
        response = self.client.post("/api/orders/checkout/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()

        self.assertEqual(data["payment_status"], Order.STATUS_SUCCESS)
        self.assertEqual(Decimal(data["total_amount"]), Decimal("2425.00"))
        self.assertEqual(Decimal(data["total_weight_kg"]), Decimal("3.720"))
        self.assertEqual(len(data["items"]), 2)

        self.product1.refresh_from_db()
        self.product2.refresh_from_db()
        self.assertEqual(self.product1.stock, 3)
        self.assertEqual(self.product2.stock, 9)

    def test_insufficient_stock_rollback(self):
        payload = {
            "customer_name": "Bob Developer",
            "customer_email": "bob@example.com",
            "items": [
                {"product_id": self.product1.id, "quantity": 10}
            ]
        }
        response = self.client.post("/api/orders/checkout/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, 5)
        self.assertEqual(Order.objects.count(), 0)

    def test_simulated_payment_failure(self):
        payload = {
            "customer_name": "Charlie",
            "customer_email": "charlie@example.com",
            "items": [
                {"product_id": self.product1.id, "quantity": 1}
            ],
            "simulate_failure": True
        }
        response = self.client.post("/api/orders/checkout/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)

        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, 5)
        self.assertEqual(Order.objects.count(), 0)
