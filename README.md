# Enterprise E-Commerce Challenge (Django + Flet)

A modern, enterprise-grade e-commerce application featuring a decoupled **Django REST Framework** backend, an interactive **Flet** frontend (Flutter-based web UI), atomic inventory checkout, full-text product search, CSV bulk ingestion, and Docker containerization.

---

## Example CSV Download Acknowledgment
- **Example CSV File**: `Code Challenge E-Commerce` (`sample_products.csv`)
- **Date Downloaded / Referenced**: **September 14, 2026**

---

## Architectural Decisions & Approach

### 1. Backend: Django & Django REST Framework (DRF)
- **Modularity**: Split into dedicated applications (`products` and `orders`) following domain-driven design principles.
- **Data Integrity & Normalization**:
  - `Category`: Normalized category model with auto-generated URL slugs.
  - `Product`: Unique indexed `sku`, `price` (Decimal), `stock` (Positive integer), and `weight_kg` (Decimal with milligram precision).
  - `Order` & `OrderItem`: Immutable transaction snapshot storing historical prices, weights, and items purchased.
- **Atomic Transactions & Concurrency Safety**:
  - The checkout pipeline executes inside a `transaction.atomic()` block utilizing `Product.objects.select_for_update()`.
  - Row-level database locks prevent race conditions and inventory overselling when concurrent checkout requests occur.
  - If payment simulation is flagged to fail or stock is depleted, transactions roll back atomically with zero inventory leakage.
- **Robust CSV Ingestion Engine**:
  - Encapsulated in `products/services/csv_importer.py`.
  - Handles BOM detection (`utf-8-sig`), missing headers, and malformed rows.
  - Performs atomic row upserts (`update_or_create`) and returns detailed error diagnostics (row number, SKU, and specific reason).

### 2. Frontend: Flet (Python Flutter Framework)
- **Clean Architecture**: Decoupled from Django models using a dedicated REST `APIClient`.
- **Material 3 Interface**:
  - **Storefront**: Real-time product search, category filtering, stock availability indicators, and interactive cart additions.
  - **Inventory (CRUD)**: Tabular management view with product creation, update dialogs, and deletion confirmations.
  - **Cart & Simulated Checkout**: Live weight accumulation (`weight_kg`), real-time subtotal computation, sandbox payment simulation failure toggle, and instant confirmation dialogues.
  - **CSV Importer**: File upload picker, direct CSV text editor, template auto-filler, and diagnostic error reports.
  - **Orders History**: Auditable ledger of completed purchases and transaction IDs.
  - **Theme Toggle**: One-click switching between dark mode and light mode.

---

## Alternatives Considered

| Alternative | Pros | Cons / Why Rejected |
| :--- | :--- | :--- |
| **FastAPI + React / Vite** | High raw asynchronous API throughput; large React component ecosystem. | Introduces two distinct language toolchains (Node/NPM and Python), increasing build complexity and container weight. Flet provides unified Python codebase with native Flutter UI fidelity. |
| **Django + HTMX** | Simple server-rendered templates without heavy client build step. | Lacks native desktop integration, rich client-side reactive state management, and unified cross-platform packaging that Flet delivers out of the box. |
| **PostgreSQL vs SQLite** | Postgres supports advanced clustering and distributed locks. | SQLite satisfies the "Must use a local DB" requirement with zero external installation friction while fully supporting ACID transactions and row-locking semantics for local testing. |

---

## Project Structure

```
coding-challenge/
├── backend/
│   ├── ecommerce_core/         # Django configuration (settings, urls, wsgi)
│   ├── products/               # Products catalog, Category model, CSV service
│   │   ├── migrations/
│   │   ├── services/
│   │   │   └── csv_importer.py # Bulk CSV parsing and validation engine
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── tests.py
│   ├── orders/                 # Order processing & atomic payment checkout
│   │   ├── migrations/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── tests.py
│   └── manage.py
├── frontend/
│   ├── api_client.py           # REST communication layer
│   └── main.py                 # Flet Material 3 application entry point
├── sample_products.csv         # Valid sample CSV matching exact required schema
├── test_e2e.py                 # Automated end-to-end integration test suite
├── Dockerfile                  # Unified production container specification
├── docker-compose.yml          # Compose orchestration file
├── start.sh                    # Container bootstrap & migration script
├── requirements.txt            # Locked Python dependencies
└── README.md
```

---

## CSV Structure Specification

| Column | Type | Description |
| :--- | :--- | :--- |
| `name` | String | Product display name (Required) |
| `sku` | String | Unique product identifier (Required) |
| `description` | String | Product summary (Optional) |
| `category` | String | Category name; auto-created if new (Optional) |
| `price` | Decimal | Unit price in USD (Required, >= 0.00) |
| `stock` | Integer | Available inventory count (Optional, defaults to 0) |
| `weight_kg` | Decimal | Weight in kilograms (Optional, defaults to 0.000) |

---

## How to Run Locally

### Prerequisites
- Python 3.11 or 3.12 installed
- Virtualenv (`python3 -m venv`)

### 1. Setup Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Initialize Database & Seed Sample Data
```bash
python backend/manage.py migrate
python backend/manage.py shell -c '
from products.services.csv_importer import CSVImporter
with open("sample_products.csv", "r", encoding="utf-8") as f:
    CSVImporter.import_from_stream(f)
'
```

### 3. Start Backend (Terminal 1)
```bash
python backend/manage.py runserver 127.0.0.1:8000
```
- API Base: `http://127.0.0.1:8000/api/`
- Health Check: `http://127.0.0.1:8000/api/health/`

### 4. Start Frontend (Terminal 2)
```bash
export API_BASE_URL="http://127.0.0.1:8000/api"
export PORT=8502
python frontend/main.py
```
- Open browser at: **`http://localhost:8502`**

---

## How to Run with Docker

### Method 1: Docker Compose (Recommended)
```bash
docker compose up --build
```
Access the application:
- **Web Frontend**: `http://localhost:8502`
- **Django REST API**: `http://localhost:8000/api/`

### Method 2: Docker CLI
```bash
docker build -t ecommerce-app:latest .
docker run -p 8000:8000 -p 8502:8502 ecommerce-app:latest
```

---

## Running Automated Tests

### 1. Backend Unit Tests
Executes model validation, CSV parser boundary cases, CRUD endpoints, and atomic transactions:
```bash
python backend/manage.py test products orders
```

### 2. End-to-End (E2E) Integration Tests
Simulates real API interaction across product lifecycle, searching, atomic checkout, stock reduction, and payment decline rollbacks:
```bash
python test_e2e.py
```
