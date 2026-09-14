import os
import requests


class APIClient:
    def __init__(self, base_url=None):
        self.base_url = (base_url or os.environ.get("API_BASE_URL", "http://127.0.0.1:8000/api")).rstrip("/")

    def get_products(self, search="", category="", min_price="", max_price="", in_stock="", ordering="-created_at", page=1):
        params = {"ordering": ordering, "page": page}
        if search:
            params["search"] = search
        if category:
            params["category"] = category
        if min_price:
            params["min_price"] = min_price
        if max_price:
            params["max_price"] = max_price
        if in_stock != "":
            params["in_stock"] = in_stock

        try:
            res = requests.get(f"{self.base_url}/products/", params=params, timeout=10)
            res.raise_for_status()
            return res.json()
        except requests.RequestException as e:
            return {"error": str(e), "results": [], "count": 0}

    def get_categories(self):
        try:
            res = requests.get(f"{self.base_url}/categories/", timeout=10)
            res.raise_for_status()
            return res.json()
        except requests.RequestException as e:
            return []

    def get_product(self, product_id):
        try:
            res = requests.get(f"{self.base_url}/products/{product_id}/", timeout=10)
            res.raise_for_status()
            return res.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    def create_product(self, payload):
        try:
            res = requests.post(f"{self.base_url}/products/", json=payload, timeout=10)
            return {"status_code": res.status_code, "data": res.json()}
        except requests.RequestException as e:
            return {"status_code": 500, "data": {"detail": str(e)}}

    def update_product(self, product_id, payload):
        try:
            res = requests.patch(f"{self.base_url}/products/{product_id}/", json=payload, timeout=10)
            return {"status_code": res.status_code, "data": res.json()}
        except requests.RequestException as e:
            return {"status_code": 500, "data": {"detail": str(e)}}

    def delete_product(self, product_id):
        try:
            res = requests.delete(f"{self.base_url}/products/{product_id}/", timeout=10)
            return {"status_code": res.status_code, "success": res.status_code == 204}
        except requests.RequestException as e:
            return {"status_code": 500, "success": False, "error": str(e)}

    def import_csv(self, file_bytes=None, csv_text=None, filename="import.csv"):
        try:
            if file_bytes:
                files = {"file": (filename, file_bytes, "text/csv")}
                res = requests.post(f"{self.base_url}/products/import-csv/", files=files, timeout=30)
            else:
                res = requests.post(f"{self.base_url}/products/import-csv/", json={"csv_text": csv_text}, timeout=30)
            return {"status_code": res.status_code, "data": res.json()}
        except requests.RequestException as e:
            return {"status_code": 500, "data": {"detail": str(e), "success": False}}

    def checkout(self, items, customer_name="Guest Customer", customer_email="guest@example.com", simulate_failure=False):
        payload = {
            "items": items,
            "customer_name": customer_name,
            "customer_email": customer_email,
            "simulate_failure": simulate_failure,
        }
        try:
            res = requests.post(f"{self.base_url}/orders/checkout/", json=payload, timeout=15)
            return {"status_code": res.status_code, "data": res.json()}
        except requests.RequestException as e:
            return {"status_code": 500, "data": {"detail": str(e)}}

    def get_orders(self):
        try:
            res = requests.get(f"{self.base_url}/orders/", timeout=10)
            res.raise_for_status()
            return res.json()
        except requests.RequestException as e:
            return {"error": str(e), "results": []}
