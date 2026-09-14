from decimal import Decimal, InvalidOperation
import csv
import io
import re
from django.db import transaction
from products.models import Category, Product


class CSVImporter:
    REQUIRED_COLUMNS = {"sku"}

    @classmethod
    def import_from_stream(cls, file_stream, encoding="utf-8-sig"):
        if isinstance(file_stream, bytes):
            decoded_file = file_stream.decode(encoding, errors="replace")
        elif hasattr(file_stream, "read"):
            content = file_stream.read()
            if isinstance(content, bytes):
                decoded_file = content.decode(encoding, errors="replace")
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
                "failed": 0,
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
                "failed": 0,
                "errors": [{"row": 0, "error": f"Missing required column: {', '.join(missing)}"}],
            }

        results = {
            "success": True,
            "total": 0,
            "created": 0,
            "updated": 0,
            "failed": 0,
            "skipped_empty": 0,
            "errors": [],
        }

        category_cache = {}

        for row_index, row in enumerate(reader, start=2):
            row_data = {k.strip().lower(): v.strip() if v else "" for k, v in row.items() if k}

            if not any(row_data.values()):
                results["skipped_empty"] += 1
                continue

            results["total"] += 1

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
                name = description[:60].strip() if description else f"Product {sku}"

            cleaned_price_str = raw_price.replace("$", "").replace("€", "").replace("£", "").replace(",", "").strip()
            if cleaned_price_str.lower() in ("free", "zero", "$0", ""):
                price = Decimal("0.00")
            else:
                try:
                    price = Decimal(cleaned_price_str)
                    if price < Decimal("0.00"):
                        price = Decimal("0.00")
                except (InvalidOperation, ValueError):
                    results["failed"] += 1
                    results["errors"].append({"row": row_index, "sku": sku, "error": f"Invalid price value: '{raw_price}'"})
                    continue

            try:
                stock = max(0, int(float(raw_stock))) if raw_stock else 0
            except (ValueError, TypeError):
                results["failed"] += 1
                results["errors"].append({"row": row_index, "sku": sku, "error": f"Invalid stock value: '{raw_stock}'"})
                continue

            cleaned_weight_str = raw_weight.replace("kg", "").replace("g", "").replace(",", "").strip()
            if not cleaned_weight_str:
                weight_kg = Decimal("0.000")
            else:
                try:
                    weight_kg = max(Decimal("0.000"), Decimal(cleaned_weight_str))
                except (InvalidOperation, ValueError):
                    results["failed"] += 1
                    results["errors"].append({"row": row_index, "sku": sku, "error": f"Invalid weight value: '{raw_weight}'"})
                    continue

            if not category_name:
                category_name = "General"

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
