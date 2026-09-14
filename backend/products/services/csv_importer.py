from decimal import Decimal, InvalidOperation
import csv
import io
from django.db import transaction
from products.models import Category, Product


class CSVImporter:
    REQUIRED_COLUMNS = {"name", "sku", "price"}

    @classmethod
    def import_from_stream(cls, file_stream, encoding="utf-8-sig"):
        if isinstance(file_stream, bytes):
            decoded_file = file_stream.decode(encoding)
        elif hasattr(file_stream, "read"):
            content = file_stream.read()
            if isinstance(content, bytes):
                decoded_file = content.decode(encoding)
            else:
                decoded_file = str(content)
        else:
            decoded_file = str(file_stream)

        reader = csv.DictReader(io.StringIO(decoded_file))
        if not reader.fieldnames:
            return {
                "success": False,
                "total": 0,
                "created": 0,
                "updated": 0,
                "errors": [{"row": 0, "error": "CSV file has no headers or is empty"}],
            }

        fieldnames_normalized = {col.strip().lower(): col for col in reader.fieldnames if col}
        missing = [req for req in cls.REQUIRED_COLUMNS if req not in fieldnames_normalized]
        if missing:
            return {
                "success": False,
                "total": 0,
                "created": 0,
                "updated": 0,
                "errors": [{"row": 0, "error": f"Missing required columns: {', '.join(missing)}"}],
            }

        results = {
            "success": True,
            "total": 0,
            "created": 0,
            "updated": 0,
            "failed": 0,
            "errors": [],
        }

        category_cache = {}

        for row_index, row in enumerate(reader, start=2):
            results["total"] += 1
            row_data = {k.strip().lower(): v.strip() if v else "" for k, v in row.items() if k}

            sku = row_data.get("sku", "").strip()
            name = row_data.get("name", "").strip()
            raw_price = row_data.get("price", "").strip()
            raw_stock = row_data.get("stock", "0").strip()
            raw_weight = row_data.get("weight_kg", "0").strip()
            description = row_data.get("description", "").strip()
            category_name = row_data.get("category", "").strip()

            if not sku:
                results["failed"] += 1
                results["errors"].append({"row": row_index, "sku": "", "error": "SKU cannot be empty"})
                continue

            if not name:
                results["failed"] += 1
                results["errors"].append({"row": row_index, "sku": sku, "error": "Name cannot be empty"})
                continue

            try:
                price = Decimal(raw_price)
                if price < 0:
                    raise ValueError("Price must be positive")
            except (InvalidOperation, ValueError):
                results["failed"] += 1
                results["errors"].append({"row": row_index, "sku": sku, "error": f"Invalid price value: '{raw_price}'"})
                continue

            try:
                stock = int(raw_stock) if raw_stock else 0
                if stock < 0:
                    raise ValueError("Stock must be >= 0")
            except ValueError:
                results["failed"] += 1
                results["errors"].append({"row": row_index, "sku": sku, "error": f"Invalid stock value: '{raw_stock}'"})
                continue

            try:
                weight_kg = Decimal(raw_weight) if raw_weight else Decimal("0.000")
                if weight_kg < 0:
                    raise ValueError("Weight must be >= 0")
            except (InvalidOperation, ValueError):
                results["failed"] += 1
                results["errors"].append({"row": row_index, "sku": sku, "error": f"Invalid weight value: '{raw_weight}'"})
                continue

            category = None
            if category_name:
                cat_key = category_name.lower()
                if cat_key in category_cache:
                    category = category_cache[cat_key]
                else:
                    category, _ = Category.objects.get_or_create(name=category_name)
                    category_cache[cat_key] = category

            with transaction.atomic():
                product, created = Product.objects.update_or_create(
                    sku=sku,
                    defaults={
                        "name": name,
                        "description": description,
                        "category": category,
                        "price": price,
                        "stock": stock,
                        "weight_kg": weight_kg,
                    },
                )
                if created:
                    results["created"] += 1
                else:
                    results["updated"] += 1

        results["success"] = len(results["errors"]) == 0
        return results
