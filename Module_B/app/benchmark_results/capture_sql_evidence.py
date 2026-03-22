"""
Capture SQL EXPLAIN and profiling evidence into concrete output files.

Outputs (in this folder):
- sql_capture_status.json
- sql_explain_before.json
- sql_explain_after.json
- sql_profiles_before.json
- sql_profiles_after.json

If MySQL is unavailable, files are still created with explicit error details.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pymysql
from pymysql.cursors import DictCursor

BASE_DIR = Path(__file__).resolve().parent

OUTPUT_FILES = {
    "status": BASE_DIR / "sql_capture_status.json",
    "explain_before": BASE_DIR / "sql_explain_before.json",
    "explain_after": BASE_DIR / "sql_explain_after.json",
    "profiles_before": BASE_DIR / "sql_profiles_before.json",
    "profiles_after": BASE_DIR / "sql_profiles_after.json",
}

DROP_INDEX_STATEMENTS = [
    "DROP INDEX ux_product_name ON Product",
    "DROP INDEX idx_product_category ON Product",
    "DROP INDEX idx_product_category_price ON Product",
    "DROP INDEX idx_product_stock_reorder ON Product",
    "DROP INDEX ux_category_name ON Category",
    "DROP INDEX ux_customer_email ON Customer",
    "DROP INDEX idx_customer_contact ON Customer",
    "DROP INDEX idx_customer_loyalty ON Customer",
    "DROP INDEX idx_sale_customer ON Sale",
    "DROP INDEX idx_sale_staff ON Sale",
    "DROP INDEX idx_sale_date ON Sale",
    "DROP INDEX idx_sale_customer_date ON Sale",
    "DROP INDEX idx_sale_staff_date ON Sale",
    "DROP INDEX idx_saleitem_sale ON SaleItem",
    "DROP INDEX idx_saleitem_product ON SaleItem",
    "DROP INDEX idx_saleitem_sale_product ON SaleItem",
    "DROP INDEX idx_payment_sale ON Payment",
    "DROP INDEX idx_payment_date ON Payment",
    "DROP INDEX idx_payment_method_date ON Payment",
    "DROP INDEX idx_purchaseorder_supplier_date ON PurchaseOrder",
    "DROP INDEX idx_poitem_poid_product ON PurchaseOrderItem",
]

CREATE_INDEX_STATEMENTS = [
    "CREATE UNIQUE INDEX ux_product_name ON Product(Name)",
    "CREATE INDEX idx_product_category ON Product(CategoryID)",
    "CREATE INDEX idx_product_category_price ON Product(CategoryID, Price)",
    "CREATE INDEX idx_product_stock_reorder ON Product(StockQuantity, ReorderLevel)",
    "CREATE UNIQUE INDEX ux_category_name ON Category(CategoryName)",
    "CREATE UNIQUE INDEX ux_customer_email ON Customer(Email)",
    "CREATE INDEX idx_customer_contact ON Customer(ContactNumber)",
    "CREATE INDEX idx_customer_loyalty ON Customer(LoyaltyPoints)",
    "CREATE INDEX idx_sale_customer ON Sale(CustomerID)",
    "CREATE INDEX idx_sale_staff ON Sale(StaffID)",
    "CREATE INDEX idx_sale_date ON Sale(SaleDate)",
    "CREATE INDEX idx_sale_customer_date ON Sale(CustomerID, SaleDate)",
    "CREATE INDEX idx_sale_staff_date ON Sale(StaffID, SaleDate)",
    "CREATE INDEX idx_saleitem_sale ON SaleItem(SaleID)",
    "CREATE INDEX idx_saleitem_product ON SaleItem(ProductID)",
    "CREATE INDEX idx_saleitem_sale_product ON SaleItem(SaleID, ProductID)",
    "CREATE INDEX idx_payment_sale ON Payment(SaleID)",
    "CREATE INDEX idx_payment_date ON Payment(PaymentDate)",
    "CREATE INDEX idx_payment_method_date ON Payment(PaymentMethod, PaymentDate)",
    "CREATE INDEX idx_purchaseorder_supplier_date ON PurchaseOrder(SupplierID, OrderDate)",
    "CREATE INDEX idx_poitem_poid_product ON PurchaseOrderItem(POID, ProductID)",
]

QUERY_SET = [
    {
        "name": "products_by_category_price",
        "explain": """
            EXPLAIN SELECT ProductID, Name, Price
            FROM Product
            WHERE CategoryID = 1
            ORDER BY Price DESC
        """,
        "query": """
            SELECT ProductID, Name, Price
            FROM Product
            WHERE CategoryID = 1
            ORDER BY Price DESC
        """,
    },
    {
        "name": "sales_by_customer_date",
        "explain": """
            EXPLAIN SELECT SaleID, CustomerID, StaffID, SaleDate, TotalAmount
            FROM Sale
            WHERE CustomerID = 1
              AND SaleDate BETWEEN '2025-02-01' AND '2025-06-30'
            ORDER BY SaleDate DESC
        """,
        "query": """
            SELECT SaleID, CustomerID, StaffID, SaleDate, TotalAmount
            FROM Sale
            WHERE CustomerID = 1
              AND SaleDate BETWEEN '2025-02-01' AND '2025-06-30'
            ORDER BY SaleDate DESC
        """,
    },
    {
        "name": "saleitem_join_product",
        "explain": """
            EXPLAIN SELECT si.SaleID, si.ProductID, p.Name, si.Quantity, si.UnitPrice
            FROM SaleItem si
            JOIN Product p ON p.ProductID = si.ProductID
            WHERE si.SaleID = 10
        """,
        "query": """
            SELECT si.SaleID, si.ProductID, p.Name, si.Quantity, si.UnitPrice
            FROM SaleItem si
            JOIN Product p ON p.ProductID = si.ProductID
            WHERE si.SaleID = 10
        """,
    },
    {
        "name": "customer_by_email",
        "explain": """
            EXPLAIN SELECT CustomerID, Name, ContactNumber, LoyaltyPoints
            FROM Customer
            WHERE Email = 'rahul.verma@example.com'
        """,
        "query": """
            SELECT CustomerID, Name, ContactNumber, LoyaltyPoints
            FROM Customer
            WHERE Email = 'rahul.verma@example.com'
        """,
    },
]


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True, default=str), encoding="utf-8")


def get_connection() -> pymysql.connections.Connection:
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "")
    database = os.getenv("MYSQL_DATABASE", "outlet_management")

    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        autocommit=True,
        cursorclass=DictCursor,
    )


def try_exec(cursor, sql: str) -> dict:
    sql_clean = " ".join(sql.strip().split())
    try:
        cursor.execute(sql)
        return {"sql": sql_clean, "ok": True}
    except Exception as exc:
        return {"sql": sql_clean, "ok": False, "error": str(exc)}


def capture_query_pack(cursor) -> tuple[list[dict], list[dict]]:
    explain_rows = []
    timed_rows = []

    for item in QUERY_SET:
        cursor.execute(item["explain"])
        explain_result = cursor.fetchall()

        start = time.perf_counter()
        cursor.execute(item["query"])
        data_result = cursor.fetchall()
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        explain_rows.append(
            {
                "query_name": item["name"],
                "explain_rows": explain_result,
            }
        )
        timed_rows.append(
            {
                "query_name": item["name"],
                "elapsed_ms": round(elapsed_ms, 3),
                "row_count": len(data_result),
            }
        )

    cursor.execute("SHOW PROFILES")
    profiles = cursor.fetchall()
    return explain_rows, {"timed_queries": timed_rows, "show_profiles": profiles}


def main() -> None:
    now = datetime.now(timezone.utc).isoformat()

    try:
        conn = get_connection()
    except Exception as exc:
        error_payload = {
            "captured_at": now,
            "status": "failed",
            "reason": "mysql_connection_error",
            "error": str(exc),
        }

        write_json(OUTPUT_FILES["status"], error_payload)
        write_json(
            OUTPUT_FILES["explain_before"],
            {
                "captured_at": now,
                "status": "failed",
                "phase": "before",
                "error": str(exc),
            },
        )
        write_json(
            OUTPUT_FILES["explain_after"],
            {
                "captured_at": now,
                "status": "failed",
                "phase": "after",
                "error": str(exc),
            },
        )
        write_json(
            OUTPUT_FILES["profiles_before"],
            {
                "captured_at": now,
                "status": "failed",
                "phase": "before",
                "error": str(exc),
            },
        )
        write_json(
            OUTPUT_FILES["profiles_after"],
            {
                "captured_at": now,
                "status": "failed",
                "phase": "after",
                "error": str(exc),
            },
        )
        print("MySQL connection failed. Wrote concrete failure evidence files.")
        return

    with conn:
        with conn.cursor() as cursor:
            cursor.execute("SET profiling = 1")

            drop_results = [try_exec(cursor, sql) for sql in DROP_INDEX_STATEMENTS]
            explain_before, profiles_before = capture_query_pack(cursor)

            create_results = [try_exec(cursor, sql) for sql in CREATE_INDEX_STATEMENTS]
            explain_after, profiles_after = capture_query_pack(cursor)

    write_json(
        OUTPUT_FILES["status"],
        {
            "captured_at": now,
            "status": "ok",
            "drop_index_results": drop_results,
            "create_index_results": create_results,
        },
    )
    write_json(
        OUTPUT_FILES["explain_before"],
        {
            "captured_at": now,
            "status": "ok",
            "phase": "before",
            "queries": explain_before,
        },
    )
    write_json(
        OUTPUT_FILES["explain_after"],
        {
            "captured_at": now,
            "status": "ok",
            "phase": "after",
            "queries": explain_after,
        },
    )
    write_json(
        OUTPUT_FILES["profiles_before"],
        {
            "captured_at": now,
            "status": "ok",
            "phase": "before",
            **profiles_before,
        },
    )
    write_json(
        OUTPUT_FILES["profiles_after"],
        {
            "captured_at": now,
            "status": "ok",
            "phase": "after",
            **profiles_after,
        },
    )

    print("SQL EXPLAIN/profile evidence captured successfully.")


if __name__ == "__main__":
    main()
