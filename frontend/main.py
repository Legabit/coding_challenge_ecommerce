from decimal import Decimal
import os
import sys
from pathlib import Path
import flet as ft

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from api_client import APIClient


def main(page: ft.Page):
    page.title = "Enterprise E-Commerce Suite"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.spacing = 0

    api = APIClient(base_url=os.environ.get("API_BASE_URL", "http://127.0.0.1:8000/api"))

    cart = {}

    def notify(msg, is_error=False):
        page.show_dialog(
            ft.SnackBar(
                content=ft.Text(msg, color=ft.Colors.WHITE),
                bgcolor=ft.Colors.RED_700 if is_error else ft.Colors.GREEN_700,
            )
        )

    categories_cache = []

    def refresh_categories():
        nonlocal categories_cache
        categories_cache = api.get_categories()

    refresh_categories()

    store_search_field = ft.TextField(
        hint_text="Search by product name, SKU, or keyword...",
        prefix_icon=ft.Icons.SEARCH,
        expand=True,
        dense=True,
        border_radius=8,
    )
    store_category_dropdown = ft.Dropdown(
        label="Category",
        width=180,
        dense=True,
        border_radius=8,
    )
    store_sort_dropdown = ft.Dropdown(
        label="Sort By",
        width=180,
        dense=True,
        border_radius=8,
        value="-created_at",
        options=[
            ft.dropdown.Option("-created_at", "Newest Arrivals"),
            ft.dropdown.Option("price", "Price: Low to High"),
            ft.dropdown.Option("-price", "Price: High to Low"),
            ft.dropdown.Option("name", "Name: A to Z"),
            ft.dropdown.Option("-stock", "Highest Stock"),
        ],
    )
    store_instock_checkbox = ft.Checkbox(label="In Stock Only", value=False)
    store_products_grid = ft.GridView(
        expand=True,
        runs_count=5,
        max_extent=320,
        child_aspect_ratio=0.85,
        spacing=16,
        run_spacing=16,
    )

    admin_search_field = ft.TextField(
        hint_text="Filter inventory by name, SKU...",
        prefix_icon=ft.Icons.SEARCH,
        expand=True,
        dense=True,
        border_radius=8,
    )
    admin_table_container = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

    cart_items_column = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=12)
    cart_subtotal_text = ft.Text("$0.00", size=22, weight=ft.FontWeight.BOLD)
    cart_weight_text = ft.Text("0.000 kg", size=16, color=ft.Colors.GREY_400)
    cart_customer_name = ft.TextField(label="Full Name", value="Jane Doe", dense=True, border_radius=8)
    cart_customer_email = ft.TextField(label="Email Address", value="jane.doe@example.com", dense=True, border_radius=8)
    cart_simulate_failure = ft.Checkbox(label="Simulate Payment Failure (Sandbox Test)", value=False)

    orders_list_column = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=12)

    import_text_field = ft.TextField(
        multiline=True,
        min_lines=10,
        max_lines=15,
        hint_text="Paste CSV contents here...",
        text_size=13,
        border_radius=8,
        expand=True,
    )
    import_results_column = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=8)

    cart_badge_text = ft.Text("0", size=11, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD)
    cart_badge_container = ft.Container(
        content=cart_badge_text,
        bgcolor=ft.Colors.BLUE_600,
        border_radius=10,
        padding=ft.Padding.symmetric(horizontal=6, vertical=2),
        visible=False,
    )

    def update_cart_badge():
        total_items = sum(item["quantity"] for item in cart.values())
        if total_items > 0:
            cart_badge_text.value = str(total_items)
            cart_badge_container.visible = True
        else:
            cart_badge_container.visible = False
        page.update()

    def add_to_cart(product, qty=1):
        pid = product["id"]
        avail_stock = product.get("stock", 0)
        current_in_cart = cart.get(pid, {}).get("quantity", 0)

        if current_in_cart + qty > avail_stock:
            notify(f"Cannot add more. Only {avail_stock} units available in stock.", is_error=True)
            return

        if pid in cart:
            cart[pid]["quantity"] += qty
        else:
            cart[pid] = {
                "product_id": pid,
                "product": product,
                "quantity": qty,
            }
        update_cart_badge()
        notify(f"Added '{product['name']}' to cart.")

    def render_store():
        refresh_categories()
        opts = [ft.dropdown.Option("", "All Categories")]
        for cat in categories_cache:
            opts.append(ft.dropdown.Option(str(cat["id"]), cat["name"]))
        store_category_dropdown.options = opts

        in_stock_val = "true" if store_instock_checkbox.value else ""
        resp = api.get_products(
            search=store_search_field.value or "",
            category=store_category_dropdown.value or "",
            in_stock=in_stock_val,
            ordering=store_sort_dropdown.value or "-created_at",
        )

        products = resp.get("results", [])
        store_products_grid.controls.clear()

        if not products:
            store_products_grid.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.SEARCH_OFF, size=64, color=ft.Colors.GREY_500),
                            ft.Text("No products found matching criteria.", size=18, color=ft.Colors.GREY_400),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    alignment=ft.Alignment.CENTER,
                    expand=True,
                )
            )
        else:
            for p in products:
                stock_count = p.get("stock", 0)
                in_stock = stock_count > 0
                stock_color = ft.Colors.GREEN_400 if stock_count > 10 else (ft.Colors.ORANGE_400 if stock_count > 0 else ft.Colors.RED_400)
                category_name = p.get("category", {}).get("name") if p.get("category") else "General"

                card = ft.Card(
                    elevation=3,
                    content=ft.Container(
                        padding=16,
                        border_radius=12,
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Container(
                                            content=ft.Text(category_name, size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_200),
                                            bgcolor=ft.Colors.BLUE_900,
                                            padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                                            border_radius=6,
                                        ),
                                        ft.Text(f"SKU: {p['sku']}", size=11, color=ft.Colors.GREY_400),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                                ft.Container(height=4),
                                ft.Text(p["name"], size=16, weight=ft.FontWeight.BOLD, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(
                                    p.get("description", "") or "No description provided.",
                                    size=12,
                                    color=ft.Colors.GREY_400,
                                    max_lines=2,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    expand=True,
                                ),
                                ft.Container(height=6),
                                ft.Row(
                                    [
                                        ft.Text(f"${Decimal(p['price']):.2f}", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_400),
                                        ft.Container(
                                            content=ft.Text(
                                                f"{stock_count} in stock" if in_stock else "Out of stock",
                                                size=11,
                                                color=stock_color,
                                                weight=ft.FontWeight.W_600,
                                            ),
                                            padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                            border=ft.Border.all(1, stock_color),
                                            border_radius=4,
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                ft.Row(
                                    [
                                        ft.Text(f"Weight: {Decimal(p.get('weight_kg', 0)):.3f} kg", size=11, color=ft.Colors.GREY_500),
                                        ft.FilledButton(
                                            content="Add to Cart",
                                            icon=ft.Icons.ADD_SHOPPING_CART,
                                            disabled=not in_stock,
                                            on_click=lambda e, prod=p: add_to_cart(prod),
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                            ],
                            spacing=6,
                        ),
                    ),
                )
                store_products_grid.controls.append(card)

        page.update()

    def open_product_modal(prod=None):
        is_edit = prod is not None
        title_text = "Edit Product" if is_edit else "Create New Product"

        name_f = ft.TextField(label="Product Name *", value=prod["name"] if is_edit else "", border_radius=8)
        sku_f = ft.TextField(label="SKU Code *", value=prod["sku"] if is_edit else "", disabled=is_edit, border_radius=8)
        desc_f = ft.TextField(label="Description", value=prod.get("description", "") if is_edit else "", multiline=True, min_lines=2, border_radius=8)
        cat_f = ft.TextField(
            label="Category Name",
            value=(prod.get("category", {}).get("name") if (is_edit and prod.get("category")) else ""),
            border_radius=8,
        )
        price_f = ft.TextField(label="Price ($) *", value=str(prod["price"]) if is_edit else "0.00", border_radius=8)
        stock_f = ft.TextField(label="Stock Inventory *", value=str(prod["stock"]) if is_edit else "0", border_radius=8)
        weight_f = ft.TextField(label="Weight (kg)", value=str(prod.get("weight_kg", "0.000")) if is_edit else "0.000", border_radius=8)

        def save_product(e):
            if not name_f.value or not sku_f.value:
                notify("Name and SKU are required.", is_error=True)
                return

            try:
                price = float(price_f.value)
                stock = int(stock_f.value)
                weight = float(weight_f.value or 0)
                if price < 0 or stock < 0 or weight < 0:
                    raise ValueError("Values must be non-negative.")
            except ValueError as val_err:
                notify(f"Validation error: {str(val_err)}", is_error=True)
                return

            payload = {
                "name": name_f.value.strip(),
                "sku": sku_f.value.strip(),
                "description": desc_f.value.strip(),
                "category_name": cat_f.value.strip(),
                "price": f"{price:.2f}",
                "stock": stock,
                "weight_kg": f"{weight:.3f}",
            }

            if is_edit:
                res = api.update_product(prod["id"], payload)
            else:
                res = api.create_product(payload)

            if res.get("status_code") in (200, 201):
                page.pop_dialog()
                notify(f"Product '{name_f.value}' successfully saved!")
                render_admin()
                render_store()
            else:
                err_detail = str(res.get("data", {}))
                notify(f"Error saving product: {err_detail}", is_error=True)

        modal = ft.AlertDialog(
            modal=True,
            title=ft.Text(title_text, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                width=450,
                content=ft.Column(
                    [
                        name_f,
                        sku_f,
                        ft.Row([price_f, stock_f]),
                        ft.Row([weight_f, cat_f]),
                        desc_f,
                    ],
                    spacing=12,
                    tight=True,
                ),
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: page.pop_dialog()),
                ft.FilledButton("Save Product", on_click=save_product),
            ],
        )
        page.show_dialog(modal)

    def confirm_delete_product(prod):
        def do_delete(e):
            res = api.delete_product(prod["id"])
            page.pop_dialog()
            if res.get("success"):
                notify(f"Product '{prod['name']}' deleted.")
                render_admin()
                render_store()
            else:
                notify(f"Failed to delete: {res.get('error')}", is_error=True)

        confirm_modal = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Deletion"),
            content=ft.Text(f"Are you sure you want to permanently delete '{prod['name']}' (SKU: {prod['sku']})?"),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: page.pop_dialog()),
                ft.FilledButton("Delete", bgcolor=ft.Colors.RED_600, on_click=do_delete),
            ],
        )
        page.show_dialog(confirm_modal)

    def render_admin():
        resp = api.get_products(search=admin_search_field.value or "", ordering="-created_at")
        products = resp.get("results", [])

        rows = []
        for p in products:
            cat_name = p.get("category", {}).get("name") if p.get("category") else "None"
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(p["sku"], weight=ft.FontWeight.W_600)),
                        ft.DataCell(ft.Text(p["name"])),
                        ft.DataCell(ft.Text(cat_name)),
                        ft.DataCell(ft.Text(f"${Decimal(p['price']):.2f}")),
                        ft.DataCell(ft.Text(str(p["stock"]))),
                        ft.DataCell(ft.Text(f"{Decimal(p.get('weight_kg', 0)):.3f} kg")),
                        ft.DataCell(
                            ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.Icons.EDIT,
                                        icon_color=ft.Colors.BLUE_400,
                                        tooltip="Edit",
                                        on_click=lambda e, pr=p: open_product_modal(pr),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        icon_color=ft.Colors.RED_400,
                                        tooltip="Delete",
                                        on_click=lambda e, pr=p: confirm_delete_product(pr),
                                    ),
                                ],
                                spacing=4,
                            )
                        ),
                    ]
                )
            )

        data_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("SKU", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Name", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Category", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Price", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Stock", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Weight", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Actions", weight=ft.FontWeight.BOLD)),
            ],
            rows=rows,
            border=ft.Border.all(1, ft.Colors.GREY_800),
            vertical_lines=ft.BorderSide(1, ft.Colors.GREY_800),
            horizontal_lines=ft.BorderSide(1, ft.Colors.GREY_800),
        )

        admin_table_container.controls = [
            ft.Row([data_table], scroll=ft.ScrollMode.ALWAYS),
        ]
        page.update()

    def render_cart():
        cart_items_column.controls.clear()

        if not cart:
            cart_items_column.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.SHOPPING_BAG_OUTLINED, size=64, color=ft.Colors.GREY_500),
                            ft.Text("Your shopping cart is empty.", size=18, color=ft.Colors.GREY_400),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=40,
                )
            )
            cart_subtotal_text.value = "$0.00"
            cart_weight_text.value = "0.000 kg"
            page.update()
            return

        subtotal = Decimal("0.00")
        total_weight = Decimal("0.000")

        for pid, item in list(cart.items()):
            p = item["product"]
            qty = item["quantity"]
            item_price = Decimal(str(p["price"]))
            item_weight = Decimal(str(p.get("weight_kg", "0.000")))
            line_total = item_price * qty
            line_weight = item_weight * qty

            subtotal += line_total
            total_weight += line_weight

            def change_qty(e, product_id=pid, delta=1):
                if product_id in cart:
                    cur = cart[product_id]["quantity"]
                    max_st = cart[product_id]["product"].get("stock", 0)
                    new_q = cur + delta
                    if new_q > max_st:
                        notify(f"Only {max_st} in stock.", is_error=True)
                        return
                    if new_q <= 0:
                        del cart[product_id]
                    else:
                        cart[product_id]["quantity"] = new_q
                    update_cart_badge()
                    render_cart()

            def remove_item(e, product_id=pid):
                if product_id in cart:
                    del cart[product_id]
                    update_cart_badge()
                    render_cart()

            item_card = ft.Card(
                elevation=2,
                content=ft.Container(
                    padding=12,
                    border_radius=8,
                    content=ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(p["name"], size=16, weight=ft.FontWeight.BOLD),
                                    ft.Text(f"SKU: {p['sku']} | ${item_price:.2f} each | {item_weight:.3f} kg", size=12, color=ft.Colors.GREY_400),
                                ],
                                expand=True,
                            ),
                            ft.Row(
                                [
                                    ft.IconButton(icon=ft.Icons.REMOVE_CIRCLE_OUTLINE, on_click=lambda e, pr_id=pid: change_qty(e, pr_id, -1)),
                                    ft.Text(str(qty), size=16, weight=ft.FontWeight.BOLD),
                                    ft.IconButton(icon=ft.Icons.ADD_CIRCLE_OUTLINE, on_click=lambda e, pr_id=pid: change_qty(e, pr_id, 1)),
                                ],
                                spacing=4,
                            ),
                            ft.Container(
                                width=110,
                                content=ft.Column(
                                    [
                                        ft.Text(f"${line_total:.2f}", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_400),
                                        ft.Text(f"{line_weight:.3f} kg", size=12, color=ft.Colors.GREY_400),
                                    ],
                                    horizontal_alignment=ft.CrossAxisAlignment.END,
                                ),
                            ),
                            ft.IconButton(icon=ft.Icons.DELETE_FOREVER, icon_color=ft.Colors.RED_400, on_click=lambda e, pr_id=pid: remove_item(e, pr_id)),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
            )
            cart_items_column.controls.append(item_card)

        cart_subtotal_text.value = f"${subtotal:.2f}"
        cart_weight_text.value = f"{total_weight:.3f} kg"
        page.update()

    def handle_checkout(e):
        if not cart:
            notify("Cart is empty.", is_error=True)
            return

        items_payload = [{"product_id": item["product_id"], "quantity": item["quantity"]} for item in cart.values()]
        name = cart_customer_name.value or "Guest Customer"
        email = cart_customer_email.value or "guest@example.com"
        simulate_fail = cart_simulate_failure.value

        res = api.checkout(
            items=items_payload,
            customer_name=name,
            customer_email=email,
            simulate_failure=simulate_fail,
        )

        status_code = res.get("status_code")
        data = res.get("data", {})

        if status_code == 201:
            cart.clear()
            update_cart_badge()
            render_cart()
            render_store()
            render_admin()
            render_orders()

            success_dialog = ft.AlertDialog(
                title=ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_400), ft.Text("Payment Successful!")]),
                content=ft.Column(
                    [
                        ft.Text("Your purchase was processed successfully.", weight=ft.FontWeight.BOLD),
                        ft.Container(height=8),
                        ft.Text(f"Order Number: {data.get('order_number')}"),
                        ft.Text(f"Transaction ID: {data.get('payment_transaction_id')}"),
                        ft.Text(f"Total Amount: ${Decimal(data.get('total_amount', 0)):.2f}"),
                        ft.Text(f"Total Weight: {Decimal(data.get('total_weight_kg', 0)):.3f} kg"),
                        ft.Text(f"Status: {data.get('payment_status')}"),
                    ],
                    tight=True,
                ),
                actions=[ft.FilledButton("Done", on_click=lambda ev: page.pop_dialog())],
            )
            page.show_dialog(success_dialog)

        elif status_code == 402:
            error_dialog = ft.AlertDialog(
                title=ft.Row([ft.Icon(ft.Icons.ERROR, color=ft.Colors.RED_400), ft.Text("Payment Simulation Failed")]),
                content=ft.Column(
                    [
                        ft.Text(data.get("detail", "Transaction was declined by simulated gateway.")),
                        ft.Text(f"Error code: {data.get('error_code', 'PAYMENT_FAILED')}"),
                        ft.Text("No inventory was deducted and no charges were made.", color=ft.Colors.GREY_400),
                    ],
                    tight=True,
                ),
                actions=[ft.FilledButton("Close", on_click=lambda ev: page.pop_dialog())],
            )
            page.show_dialog(error_dialog)

        else:
            detail = data.get("detail") or "Checkout encountered an error."
            errors = data.get("errors") or []
            error_lines = "\n".join(errors) if errors else ""
            notify(f"{detail} {error_lines}", is_error=True)

    def render_orders():
        orders_list_column.controls.clear()
        res = api.get_orders()
        orders = res.get("results", [])

        if not orders:
            orders_list_column.controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.RECEIPT_LONG, size=64, color=ft.Colors.GREY_500),
                            ft.Text("No transactions or orders recorded yet.", size=18, color=ft.Colors.GREY_400),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    alignment=ft.Alignment.CENTER,
                    padding=40,
                )
            )
            page.update()
            return

        for ord_data in orders:
            items = ord_data.get("items", [])
            items_controls = []
            for itm in items:
                items_controls.append(
                    ft.Row(
                        [
                            ft.Text(f"• {itm['quantity']}x {itm['product_name']} ({itm['product_sku']})", size=13),
                            ft.Text(f"${Decimal(itm['subtotal']):.2f}", size=13, weight=ft.FontWeight.W_600),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    )
                )

            order_card = ft.Card(
                elevation=2,
                content=ft.Container(
                    padding=16,
                    border_radius=8,
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Row(
                                        [
                                            ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_400, size=20),
                                            ft.Text(ord_data["order_number"], size=16, weight=ft.FontWeight.BOLD),
                                        ],
                                        spacing=8,
                                    ),
                                    ft.Text(f"${Decimal(ord_data['total_amount']):.2f}", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_400),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Row(
                                [
                                    ft.Text(f"Customer: {ord_data.get('customer_name')} ({ord_data.get('customer_email')})", size=12, color=ft.Colors.GREY_400),
                                    ft.Text(f"Weight: {Decimal(ord_data.get('total_weight_kg', 0)):.3f} kg", size=12, color=ft.Colors.GREY_400),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Text(f"Txn: {ord_data.get('payment_transaction_id')}", size=11, color=ft.Colors.GREY_500),
                            ft.Divider(height=8),
                            ft.Column(items_controls, spacing=4),
                        ],
                        spacing=6,
                    ),
                ),
            )
            orders_list_column.controls.append(order_card)

        page.update()

    def handle_csv_import(e):
        csv_text = import_text_field.value
        if not csv_text or not csv_text.strip():
            notify("Please paste CSV contents first.", is_error=True)
            return

        res = api.import_csv(csv_text=csv_text)
        data = res.get("data", {})

        import_results_column.controls.clear()

        if res.get("status_code") == 200 and data.get("success"):
            import_results_column.controls.append(
                ft.Container(
                    bgcolor=ft.Colors.GREEN_900,
                    padding=12,
                    border_radius=8,
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_300),
                            ft.Text(
                                f"Import Complete! Total: {data.get('total')} | Created: {data.get('created')} | Updated: {data.get('updated')}",
                                color=ft.Colors.WHITE,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ],
                        spacing=8,
                    ),
                )
            )
            notify("CSV imported successfully!")
            render_store()
            render_admin()
        else:
            errors = data.get("errors", [])
            err_items = [
                ft.Container(
                    bgcolor=ft.Colors.RED_900,
                    padding=12,
                    border_radius=8,
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.ERROR, color=ft.Colors.RED_300),
                            ft.Text(
                                f"Import Failed: {data.get('failed', 0)} invalid rows detected.",
                                color=ft.Colors.WHITE,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ],
                        spacing=8,
                    ),
                )
            ]
            for err in errors:
                err_items.append(
                    ft.Text(f"• Row {err.get('row')}: {err.get('error')} (SKU: {err.get('sku', 'N/A')})", size=13, color=ft.Colors.RED_300)
                )
            import_results_column.controls.extend(err_items)
            notify("CSV import encountered errors.", is_error=True)

        page.update()

    def load_example_csv(e):
        try:
            with open("sample_products.csv", "r", encoding="utf-8") as f:
                import_text_field.value = f.read()
        except Exception:
            import_text_field.value = (
                "name,sku,description,category,price,stock,weight_kg\n"
                "Sample Wireless Mouse,SAMP-MS-01,Ergonomic mouse,Peripherals,29.99,50,0.120\n"
                "Sample Mechanical Keyboard,SAMP-KB-02,RGB tactile switches,Peripherals,89.99,30,0.850\n"
            )
        page.update()
        notify("Sample CSV template loaded into editor.")

    file_picker = ft.FilePicker()
    page.overlay.append(file_picker)

    def on_file_picked(e):
        if e.files and len(e.files) > 0:
            picked = e.files[0]
            try:
                with open(picked.path, "r", encoding="utf-8-sig") as f:
                    import_text_field.value = f.read()
                notify(f"Loaded file '{picked.name}' into editor.")
                page.update()
            except Exception as err:
                notify(f"Could not read local file: {str(err)}", is_error=True)

    file_picker.on_result = on_file_picked

    store_search_field.on_submit = lambda e: render_store()
    store_category_dropdown.on_change = lambda e: render_store()
    store_sort_dropdown.on_change = lambda e: render_store()
    store_instock_checkbox.on_change = lambda e: render_store()
    admin_search_field.on_submit = lambda e: render_admin()

    store_view = ft.Container(
        expand=True,
        padding=24,
        content=ft.Column(
            [
                ft.Row(
                    [
                        store_search_field,
                        ft.IconButton(icon=ft.Icons.SEARCH, tooltip="Search", on_click=lambda e: render_store()),
                        store_category_dropdown,
                        store_sort_dropdown,
                        store_instock_checkbox,
                        ft.IconButton(icon=ft.Icons.REFRESH, tooltip="Refresh", on_click=lambda e: render_store()),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Divider(height=16),
                store_products_grid,
            ],
            expand=True,
            spacing=8,
        ),
    )

    admin_view = ft.Container(
        expand=True,
        padding=24,
        content=ft.Column(
            [
                ft.Row(
                    [
                        admin_search_field,
                        ft.IconButton(icon=ft.Icons.SEARCH, tooltip="Search", on_click=lambda e: render_admin()),
                        ft.FilledButton(
                            content="Add Product",
                            icon=ft.Icons.ADD,
                            on_click=lambda e: open_product_modal(),
                        ),
                        ft.IconButton(icon=ft.Icons.REFRESH, tooltip="Refresh", on_click=lambda e: render_admin()),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Divider(height=16),
                admin_table_container,
            ],
            expand=True,
            spacing=8,
        ),
    )

    cart_view = ft.Container(
        expand=True,
        padding=24,
        content=ft.Row(
            [
                ft.Container(
                    expand=3,
                    content=ft.Column(
                        [
                            ft.Text("Shopping Cart Items", size=20, weight=ft.FontWeight.BOLD),
                            ft.Divider(height=8),
                            cart_items_column,
                        ],
                        expand=True,
                        spacing=8,
                    ),
                ),
                ft.VerticalDivider(width=24),
                ft.Container(
                    expand=2,
                    content=ft.Card(
                        elevation=3,
                        content=ft.Container(
                            padding=20,
                            content=ft.Column(
                                [
                                    ft.Text("Order Summary", size=20, weight=ft.FontWeight.BOLD),
                                    ft.Divider(height=12),
                                    ft.Row([ft.Text("Total Weight:", size=15), cart_weight_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                    ft.Row([ft.Text("Estimated Total:", size=18, weight=ft.FontWeight.BOLD), cart_subtotal_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                    ft.Divider(height=16),
                                    ft.Text("Customer Information", size=15, weight=ft.FontWeight.W_600),
                                    cart_customer_name,
                                    cart_customer_email,
                                    cart_simulate_failure,
                                    ft.Container(height=12),
                                    ft.FilledButton(
                                        content="Place Order (Simulated Payment)",
                                        icon=ft.Icons.PAYMENT,
                                        width=350,
                                        height=48,
                                        on_click=handle_checkout,
                                    ),
                                ],
                                spacing=10,
                                tight=True,
                            ),
                        ),
                    ),
                ),
            ],
            expand=True,
        ),
    )

    import_view = ft.Container(
        expand=True,
        padding=24,
        content=ft.Column(
            [
                ft.Text("Bulk Product CSV Importer", size=22, weight=ft.FontWeight.BOLD),
                ft.Text(
                    "Import or update products via CSV. Required columns: name, sku, price. Optional: description, category, stock, weight_kg.",
                    color=ft.Colors.GREY_400,
                ),
                ft.Divider(height=12),
                ft.Row(
                    [
                        ft.FilledButton(
                            content="Choose CSV File",
                            icon=ft.Icons.UPLOAD_FILE,
                            on_click=lambda e: file_picker.pick_files(allowed_extensions=["csv"]),
                        ),
                        ft.OutlinedButton(
                            content="Load Sample CSV Template",
                            icon=ft.Icons.DESCRIPTION,
                            on_click=load_example_csv,
                        ),
                        ft.FilledButton(
                            content="Run CSV Import",
                            icon=ft.Icons.PLAY_ARROW,
                            bgcolor=ft.Colors.GREEN_700,
                            on_click=handle_csv_import,
                        ),
                    ],
                    spacing=12,
                ),
                ft.Container(height=8),
                import_text_field,
                ft.Divider(height=12),
                ft.Text("Import Diagnostics & Feedback", size=16, weight=ft.FontWeight.BOLD),
                import_results_column,
            ],
            expand=True,
            spacing=8,
            scroll=ft.ScrollMode.AUTO,
        ),
    )

    orders_view = ft.Container(
        expand=True,
        padding=24,
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("Completed Orders & Transactions", size=22, weight=ft.FontWeight.BOLD),
                        ft.IconButton(icon=ft.Icons.REFRESH, tooltip="Refresh Orders", on_click=lambda e: render_orders()),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Divider(height=12),
                orders_list_column,
            ],
            expand=True,
            spacing=8,
        ),
    )

    views = [store_view, admin_view, cart_view, import_view, orders_view]
    content_area = ft.Container(content=store_view, expand=True)

    def on_nav_change(e):
        idx = e.control.selected_index
        content_area.content = views[idx]
        if idx == 0:
            render_store()
        elif idx == 1:
            render_admin()
        elif idx == 2:
            render_cart()
        elif idx == 3:
            pass
        elif idx == 4:
            render_orders()
        page.update()

    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        min_extended_width=160,
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.STOREFRONT_OUTLINED,
                selected_icon=ft.Icons.STOREFRONT,
                label="Storefront",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.INVENTORY_2_OUTLINED,
                selected_icon=ft.Icons.INVENTORY_2,
                label="Inventory",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SHOPPING_CART_OUTLINED,
                selected_icon=ft.Icons.SHOPPING_CART,
                label="Cart",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.UPLOAD_FILE_OUTLINED,
                selected_icon=ft.Icons.UPLOAD_FILE,
                label="CSV Import",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.RECEIPT_LONG_OUTLINED,
                selected_icon=ft.Icons.RECEIPT_LONG,
                label="Orders",
            ),
        ],
        on_change=on_nav_change,
    )

    def toggle_theme(e):
        page.theme_mode = ft.ThemeMode.LIGHT if page.theme_mode == ft.ThemeMode.DARK else ft.ThemeMode.DARK
        theme_btn.icon = ft.Icons.DARK_MODE if page.theme_mode == ft.ThemeMode.LIGHT else ft.Icons.LIGHT_MODE
        page.update()

    theme_btn = ft.IconButton(
        icon=ft.Icons.LIGHT_MODE,
        tooltip="Toggle Dark/Light Theme",
        on_click=toggle_theme,
    )

    app_bar = ft.Container(
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        padding=ft.Padding.symmetric(horizontal=20, vertical=10),
        content=ft.Row(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.SHOPPING_BAG, color=ft.Colors.BLUE_400, size=28),
                        ft.Text("NEXUS COMMERCE", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_300),
                    ],
                    spacing=10,
                ),
                ft.Row(
                    [
                        theme_btn,
                        ft.Stack(
                            [
                                ft.IconButton(
                                    icon=ft.Icons.SHOPPING_CART,
                                    tooltip="View Cart",
                                    on_click=lambda e: (setattr(rail, "selected_index", 2), on_nav_change(type("Ev", (), {"control": rail})())),
                                ),
                                cart_badge_container,
                            ],
                            alignment=ft.Alignment.TOP_RIGHT,
                        ),
                    ],
                    spacing=12,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    page.add(
        ft.Column(
            [
                app_bar,
                ft.Row(
                    [
                        rail,
                        ft.VerticalDivider(width=1),
                        content_area,
                    ],
                    expand=True,
                    spacing=0,
                ),
            ],
            expand=True,
            spacing=0,
        )
    )

    render_store()


if __name__ == "__main__":
    web_port = int(os.environ.get("PORT", "8502"))
    ft.run(
        main,
        host="0.0.0.0",
        port=web_port,
        view=ft.AppView.WEB_BROWSER,
    )
