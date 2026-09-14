from decimal import Decimal
import io
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from products.models import Category, Product
from products.services.csv_importer import CSVImporter


class ProductModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Electronics")
        self.product = Product.objects.create(
            name="Mechanical Keyboard",
            sku="KB-001",
            description="RGB mechanical keyboard",
            category=self.category,
            price=Decimal("99.99"),
            stock=15,
            weight_kg=Decimal("1.250")
        )

    def test_product_creation(self):
        self.assertEqual(self.product.name, "Mechanical Keyboard")
        self.assertEqual(self.product.sku, "KB-001")
        self.assertEqual(self.product.category.name, "Electronics")
        self.assertEqual(self.product.category.slug, "electronics")
        self.assertEqual(self.product.price, Decimal("99.99"))
        self.assertEqual(self.product.stock, 15)
        self.assertEqual(self.product.weight_kg, Decimal("1.250"))


class ProductAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name="Audio")
        self.product1 = Product.objects.create(
            name="Wireless Headphones",
            sku="WH-100",
            description="Noise-cancelling over-ear headphones",
            category=self.category,
            price=Decimal("199.99"),
            stock=10,
            weight_kg=Decimal("0.550")
        )
        self.product2 = Product.objects.create(
            name="Studio Microphone",
            sku="MIC-200",
            description="Cardioid condenser microphone for streaming",
            category=self.category,
            price=Decimal("89.50"),
            stock=0,
            weight_kg=Decimal("0.800")
        )

    def test_list_products(self):
        response = self.client.get("/api/products/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 2)

    def test_retrieve_product(self):
        response = self.client.get(f"/api/products/{self.product1.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["sku"], "WH-100")

    def test_create_product(self):
        payload = {
            "name": "USB-C Hub",
            "sku": "HUB-300",
            "description": "Multiport adapter",
            "category_name": "Accessories",
            "price": "39.99",
            "stock": 50,
            "weight_kg": "0.150"
        }
        response = self.client.post("/api/products/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Product.objects.filter(sku="HUB-300").exists())
        self.assertTrue(Category.objects.filter(name="Accessories").exists())

    def test_update_product(self):
        payload = {
            "name": "Wireless Headphones Pro",
            "sku": "WH-100",
            "price": "229.99",
            "stock": 8,
            "weight_kg": "0.580"
        }
        response = self.client.patch(f"/api/products/{self.product1.id}/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.name, "Wireless Headphones Pro")
        self.assertEqual(self.product1.price, Decimal("229.99"))

    def test_delete_product(self):
        response = self.client.delete(f"/api/products/{self.product2.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Product.objects.filter(id=self.product2.id).exists())

    def test_search_products(self):
        response = self.client.get("/api/products/?search=Microphone")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["sku"], "MIC-200")

    def test_filter_in_stock(self):
        response = self.client.get("/api/products/?in_stock=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["sku"], "WH-100")


class CSVImporterTests(TestCase):
    def test_valid_csv_import(self):
        csv_data = (
            "name,sku,description,category,price,stock,weight_kg\n"
            "Gaming Mouse,GM-01,Ergonomic mouse,Peripherals,49.99,30,0.200\n"
            "Mechanical Keyboard,KB-01,Blue switches,Peripherals,89.99,15,0.950\n"
        )
        stream = io.StringIO(csv_data)
        result = CSVImporter.import_from_stream(stream)
        self.assertTrue(result["success"])
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["created"], 2)
        self.assertEqual(Product.objects.count(), 2)

    def test_csv_upsert(self):
        csv_data_initial = (
            "name,sku,description,category,price,stock,weight_kg\n"
            "Monitor,MON-01,24 inch 1080p,Displays,120.00,10,3.500\n"
        )
        CSVImporter.import_from_stream(io.StringIO(csv_data_initial))

        csv_data_update = (
            "name,sku,description,category,price,stock,weight_kg\n"
            "Monitor 24-inch,MON-01,Updated 144Hz,Displays,135.00,25,3.600\n"
        )
        result = CSVImporter.import_from_stream(io.StringIO(csv_data_update))
        self.assertTrue(result["success"])
        self.assertEqual(result["updated"], 1)
        product = Product.objects.get(sku="MON-01")
        self.assertEqual(product.name, "Monitor 24-inch")
        self.assertEqual(product.price, Decimal("135.00"))
        self.assertEqual(product.stock, 25)

    def test_csv_validation_errors(self):
        csv_data = (
            "name,sku,description,category,price,stock,weight_kg\n"
            ",BAD-01,Missing name,Test,10.00,5,1.0\n"
            "Invalid Price,BAD-02,Bad price,Test,not_a_number,5,1.0\n"
            "Negative Stock,BAD-03,Bad stock,Test,10.00,-3,1.0\n"
        )
        result = CSVImporter.import_from_stream(io.StringIO(csv_data))
        self.assertFalse(result["success"])
        self.assertEqual(result["failed"], 3)
        self.assertEqual(len(result["errors"]), 3)
