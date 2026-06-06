#!/usr/bin/env python3
"""
Shop REST API Server
A complete REST API for e-commerce with products, shopping cart, and orders
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import logging
from datetime import datetime
import sqlite3
import os
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("shop_api.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

DB_FILE = "shop.db"


@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()


def init_database():
    """Initialize the SQLite database with tables"""
    with get_db() as conn:
        cursor = conn.cursor()

        # Products table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                stock INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

        # Shopping cart table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cart (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
            """)

        # Orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                customer_email TEXT,
                total_amount REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

        # Order items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
            """)

        logger.info("Database initialized successfully")


class ShopAPIHandler(BaseHTTPRequestHandler):
    """REST API handler for shop operations"""

    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.info(f"{self.client_address[0]} - {format % args}")

    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)

        logger.info(f"GET {path}")

        # Route handling
        if path == "/":
            self.send_html_response(self.get_home_page())

        elif path == "/api/products":
            self.get_products()

        elif path.startswith("/api/products/"):
            product_id = path.split("/")[-1]
            if product_id.isdigit():
                self.get_product(int(product_id))
            else:
                self.send_json_error("Invalid product ID", 400)

        elif path == "/api/cart":
            self.get_cart()

        elif path == "/api/orders":
            self.get_orders()

        elif path.startswith("/api/orders/"):
            order_id = path.split("/")[-1]
            if order_id.isdigit():
                self.get_order(int(order_id))
            else:
                self.send_json_error("Invalid order ID", 400)

        else:
            self.send_json_error(f"Endpoint {path} not found", 404)

    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        logger.info(f"POST {path}")

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self.send_json_error("Invalid JSON", 400)
            return

        # Route handling
        if path == "/api/products":
            self.create_product(data)

        elif path == "/api/cart":
            self.add_to_cart(data)

        elif path == "/api/orders":
            self.create_order(data)

        else:
            self.send_json_error(f"POST endpoint {path} not found", 404)

    def do_PUT(self):
        """Handle PUT requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        logger.info(f"PUT {path}")

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self.send_json_error("Invalid JSON", 400)
            return

        if path.startswith("/api/products/"):
            product_id = path.split("/")[-1]
            if product_id.isdigit():
                self.update_product(int(product_id), data)
            else:
                self.send_json_error("Invalid product ID", 400)

        elif path.startswith("/api/cart/"):
            item_id = path.split("/")[-1]
            if item_id.isdigit():
                self.update_cart_item(int(item_id), data)
            else:
                self.send_json_error("Invalid cart item ID", 400)

        else:
            self.send_json_error(f"PUT endpoint {path} not found", 404)

    def do_DELETE(self):
        """Handle DELETE requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        logger.info(f"DELETE {path}")

        if path.startswith("/api/products/"):
            product_id = path.split("/")[-1]
            if product_id.isdigit():
                self.delete_product(int(product_id))
            else:
                self.send_json_error("Invalid product ID", 400)

        elif path.startswith("/api/cart/"):
            item_id = path.split("/")[-1]
            if item_id.isdigit():
                self.delete_cart_item(int(item_id))
            else:
                self.send_json_error("Invalid cart item ID", 400)

        else:
            self.send_json_error(f"DELETE endpoint {path} not found", 404)

    # Product endpoints
    def get_products(self):
        """GET /api/products - List all products"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products")
            products = [dict(row) for row in cursor.fetchall()]
            self.send_json_response({"products": products, "count": len(products)})

    def get_product(self, product_id):
        """GET /api/products/<id> - Get single product"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
            product = cursor.fetchone()
            if product:
                self.send_json_response({"product": dict(product)})
            else:
                self.send_json_error("Product not found", 404)

    def create_product(self, data):
        """POST /api/products - Create new product"""
        required = ["name", "price"]
        if not all(k in data for k in required):
            self.send_json_error(f"Missing required fields: {required}", 400)
            return

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO products (name, description, price, stock)
                VALUES (?, ?, ?, ?)
                """,
                (
                    data.get("name"),
                    data.get("description", ""),
                    data.get("price"),
                    data.get("stock", 0),
                ),
            )
            product_id = cursor.lastrowid
            self.send_json_response(
                {
                    "id": product_id,
                    "name": data.get("name"),
                    "price": data.get("price"),
                    "message": "Product created",
                },
                201,
            )
            logger.info(f"Created product: {product_id}")

    def update_product(self, product_id, data):
        """PUT /api/products/<id> - Update product"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
            if not cursor.fetchone():
                self.send_json_error("Product not found", 404)
                return

            updates = []
            params = []
            for key in ["name", "description", "price", "stock"]:
                if key in data:
                    updates.append(f"{key} = ?")
                    params.append(data[key])

            if not updates:
                self.send_json_error("No fields to update", 400)
                return

            params.append(product_id)
            cursor.execute(
                f"UPDATE products SET {', '.join(updates)} WHERE id = ?", params
            )
            self.send_json_response({"id": product_id, "message": "Product updated"})
            logger.info(f"Updated product: {product_id}")

    def delete_product(self, product_id):
        """DELETE /api/products/<id> - Delete product"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
            if not cursor.fetchone():
                self.send_json_error("Product not found", 404)
                return

            cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
            self.send_json_response({"id": product_id, "message": "Product deleted"})
            logger.info(f"Deleted product: {product_id}")

    # Cart endpoints
    def get_cart(self):
        """GET /api/cart - Get shopping cart"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.id, c.product_id, c.quantity, p.name, p.price,
                       (c.quantity * p.price) as subtotal
                FROM cart c
                JOIN products p ON c.product_id = p.id
                """)
            items = [dict(row) for row in cursor.fetchall()]
            total = sum(item["subtotal"] for item in items)
            self.send_json_response(
                {"items": items, "total": total, "count": len(items)}
            )

    def add_to_cart(self, data):
        """POST /api/cart - Add item to cart"""
        if "product_id" not in data or "quantity" not in data:
            self.send_json_error("Missing product_id or quantity", 400)
            return

        with get_db() as conn:
            cursor = conn.cursor()

            # Check product exists
            cursor.execute(
                "SELECT stock FROM products WHERE id = ?", (data["product_id"],)
            )
            product = cursor.fetchone()
            if not product:
                self.send_json_error("Product not found", 404)
                return

            if product["stock"] < data["quantity"]:
                self.send_json_error("Insufficient stock", 400)
                return

            # Add to cart
            cursor.execute(
                "INSERT INTO cart (product_id, quantity) VALUES (?, ?)",
                (data["product_id"], data["quantity"]),
            )
            cart_id = cursor.lastrowid
            self.send_json_response(
                {
                    "id": cart_id,
                    "product_id": data["product_id"],
                    "quantity": data["quantity"],
                },
                201,
            )
            logger.info(
                f"Added to cart: product {data['product_id']}, qty {data['quantity']}"
            )

    def update_cart_item(self, item_id, data):
        """PUT /api/cart/<id> - Update cart item quantity"""
        if "quantity" not in data:
            self.send_json_error("Missing quantity", 400)
            return

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT product_id FROM cart WHERE id = ?", (item_id,))
            cart_item = cursor.fetchone()
            if not cart_item:
                self.send_json_error("Cart item not found", 404)
                return

            cursor.execute(
                "UPDATE cart SET quantity = ? WHERE id = ?", (data["quantity"], item_id)
            )
            self.send_json_response({"id": item_id, "quantity": data["quantity"]})
            logger.info(f"Updated cart item {item_id}")

    def delete_cart_item(self, item_id):
        """DELETE /api/cart/<id> - Remove from cart"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cart WHERE id = ?", (item_id,))
            if not cursor.fetchone():
                self.send_json_error("Cart item not found", 404)
                return

            cursor.execute("DELETE FROM cart WHERE id = ?", (item_id,))
            self.send_json_response({"id": item_id, "message": "Removed from cart"})
            logger.info(f"Removed from cart: {item_id}")

    # Order endpoints
    def get_orders(self):
        """GET /api/orders - List all orders"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM orders")
            orders = [dict(row) for row in cursor.fetchall()]
            self.send_json_response({"orders": orders, "count": len(orders)})

    def get_order(self, order_id):
        """GET /api/orders/<id> - Get order details"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
            order = cursor.fetchone()
            if not order:
                self.send_json_error("Order not found", 404)
                return

            cursor.execute(
                """
                SELECT oi.id, oi.product_id, oi.quantity, oi.price,
                       p.name, (oi.quantity * oi.price) as subtotal
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = ?
                """,
                (order_id,),
            )
            items = [dict(row) for row in cursor.fetchall()]
            response = dict(order)
            response["items"] = items
            self.send_json_response({"order": response})

    def create_order(self, data):
        """POST /api/orders - Create order from cart"""
        required = ["customer_name"]
        if not all(k in data for k in required):
            self.send_json_error(f"Missing required fields: {required}", 400)
            return

        with get_db() as conn:
            cursor = conn.cursor()

            # Get cart items
            cursor.execute("""
                SELECT c.id, c.product_id, c.quantity, p.price, p.stock
                FROM cart c
                JOIN products p ON c.product_id = p.id
                """)
            cart_items = cursor.fetchall()

            if not cart_items:
                self.send_json_error("Cart is empty", 400)
                return

            # Check stock for all items
            for item in cart_items:
                if item["stock"] < item["quantity"]:
                    self.send_json_error(
                        f"Insufficient stock for product {item['product_id']}", 400
                    )
                    return

            # Calculate total
            total = sum(item["quantity"] * item["price"] for item in cart_items)

            # Create order
            cursor.execute(
                """
                INSERT INTO orders (customer_name, customer_email, total_amount, status)
                VALUES (?, ?, ?, 'completed')
                """,
                (data.get("customer_name"), data.get("customer_email", ""), total),
            )
            order_id = cursor.lastrowid

            # Add order items and update stock
            for item in cart_items:
                cursor.execute(
                    """
                    INSERT INTO order_items (order_id, product_id, quantity, price)
                    VALUES (?, ?, ?, ?)
                    """,
                    (order_id, item["product_id"], item["quantity"], item["price"]),
                )

                # Update product stock
                cursor.execute(
                    "UPDATE products SET stock = stock - ? WHERE id = ?",
                    (item["quantity"], item["product_id"]),
                )

            # Clear cart
            cursor.execute("DELETE FROM cart")

            self.send_json_response(
                {
                    "order_id": order_id,
                    "customer_name": data.get("customer_name"),
                    "total_amount": total,
                    "status": "completed",
                    "items_count": len(cart_items),
                    "message": "Order created successfully",
                },
                201,
            )
            logger.info(f"Created order: {order_id} for {data.get('customer_name')}")

    # Helper methods
    def send_json_response(self, data, status_code=200):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def send_json_error(self, message, status_code=400):
        """Send JSON error response"""
        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": message}).encode())

    def send_html_response(self, html, status_code=200):
        """Send HTML response"""
        self.send_response(status_code)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def get_home_page(self):
        """Generate home page with API documentation"""
        # return a index.html content
        fopen = open("index.html", "r")
        return fopen.read()


def run_server(host="localhost", port=8000):
    """Start the shop API server"""
    # Initialize database
    if not os.path.exists(DB_FILE):
        init_database()
    else:
        logger.info("Using existing database")

    server_address = (host, port)
    httpd = HTTPServer(server_address, ShopAPIHandler)
    logger.info(f"Shop API server started on http://{host}:{port}")
    print(f"Shop API running on http://{host}:{port}")
    print("Press Ctrl+C to stop")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped")
        print("\nServer stopped")
        httpd.server_close()
