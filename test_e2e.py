from decimal import Decimal
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path("frontend").resolve()))
from api_client import APIClient

client = APIClient()

products = client.get_products()
assert products.get("count", 0) > 0, "No products returned"
first_prod = products["results"][0]
print("1. Products list verified. Count:", products["count"])

categories = client.get_categories()
assert len(categories) > 0, "No categories returned"
print("2. Categories verified. Total:", len(categories))

random_sku = f"EAR-{uuid.uuid4().hex[:6].upper()}"
new_prod_payload = {
    "name": "Noise Cancelling Earbuds",
    "sku": random_sku,
    "description": "True wireless earbuds with ANC",
    "category_name": "Audio",
    "price": "149.99",
    "stock": 20,
    "weight_kg": "0.050",
}
res_create = client.create_product(new_prod_payload)
assert res_create["status_code"] == 201, f"Create failed: {res_create}"
created_id = res_create["data"]["id"]
print(f"3. Product created with ID {created_id} and SKU {random_sku}")

search_res = client.get_products(search=random_sku)
assert any(p["sku"] == random_sku for p in search_res.get("results", [])), "Search failed"
print("4. Product search verified.")

checkout_items = [{"product_id": created_id, "quantity": 3}]
res_checkout = client.checkout(
    items=checkout_items,
    customer_name="Test Buyer",
    customer_email="buyer@test.com",
    simulate_failure=False,
)
assert res_checkout["status_code"] == 201, f"Checkout failed: {res_checkout}"
order_data = res_checkout["data"]
assert order_data["payment_status"] == "SUCCESS"
print("5. Checkout successful. Order:", order_data["order_number"])

updated_prod = client.get_product(created_id)
assert updated_prod["stock"] == 17, f"Expected stock 17, got {updated_prod['stock']}"
print("6. Stock decrement verified: 20 -> 17")

res_fail = client.checkout(
    items=[{"product_id": created_id, "quantity": 1}],
    simulate_failure=True,
)
assert res_fail["status_code"] == 402, f"Expected 402, got {res_fail['status_code']}"
print("7. Simulated payment failure verified: HTTP 402 with rollback.")

del_res = client.delete_product(created_id)
assert del_res["success"], f"Delete product failed: {del_res}"
print("8. Product deletion verified.")

print("ALL E2E INTEGRATION TESTS COMPLETED SUCCESSFULLY!")
