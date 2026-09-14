#!/bin/bash
set -e

python backend/manage.py migrate --noinput
python backend/manage.py shell -c '
from products.models import Product
from products.services.csv_importer import CSVImporter
if Product.objects.count() == 0:
    try:
        with open("sample_products.csv", "r", encoding="utf-8") as f:
            CSVImporter.import_from_stream(f)
    except Exception:
        pass
'

python -m gunicorn --bind 0.0.0.0:8000 --chdir backend ecommerce_core.wsgi:application &
BACKEND_PID=$!

export API_BASE_URL="http://127.0.0.1:8000/api"
export PORT=8502
python frontend/main.py &
FRONTEND_PID=$!

wait -n $BACKEND_PID $FRONTEND_PID
