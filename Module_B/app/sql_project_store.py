"""
MySQL-backed store for project-specific tables.
This layer powers API CRUD so SQL indexes and EXPLAIN plans are meaningful.
"""

import os
from typing import Any, Dict, List, Optional, Tuple

import pymysql
from pymysql.cursors import DictCursor


class SQLProjectStore:
    TABLE_CONFIG = {
        "members": {
            "table": "Member",
            "pk": "MemberID",
            "cols": ["Name", "Image", "Age", "Email", "ContactNumber", "Role", "CreatedAt"],
            "api_to_db": {
                "member_id": "MemberID",
                "name": "Name",
                "image": "Image",
                "age": "Age",
                "email": "Email",
                "contact_number": "ContactNumber",
                "role": "Role",
                "created_at": "CreatedAt",
            },
        },
        "products": {
            "table": "Product",
            "pk": "ProductID",
            "cols": ["Name", "Price", "StockQuantity", "ReorderLevel", "CategoryID"],
            "api_to_db": {
                "product_id": "ProductID",
                "name": "Name",
                "price": "Price",
                "stock_quantity": "StockQuantity",
                "reorder_level": "ReorderLevel",
                "category_id": "CategoryID",
            },
        },
        "categories": {
            "table": "Category",
            "pk": "CategoryID",
            "cols": ["CategoryName", "Description", "CreatedAt"],
            "api_to_db": {
                "category_id": "CategoryID",
                "category_name": "CategoryName",
                "description": "Description",
                "created_at": "CreatedAt",
            },
        },
        "customers": {
            "table": "Customer",
            "pk": "CustomerID",
            "cols": ["Name", "Email", "ContactNumber", "LoyaltyPoints", "CreatedAt"],
            "api_to_db": {
                "customer_id": "CustomerID",
                "name": "Name",
                "email": "Email",
                "contact_number": "ContactNumber",
                "loyalty_points": "LoyaltyPoints",
                "created_at": "CreatedAt",
            },
        },
        "staff": {
            "table": "Staff",
            "pk": "StaffID",
            "cols": ["Name", "Role", "Salary", "ContactNumber", "JoinDate", "MemberID"],
            "api_to_db": {
                "staff_id": "StaffID",
                "name": "Name",
                "role": "Role",
                "salary": "Salary",
                "contact_number": "ContactNumber",
                "join_date": "JoinDate",
                "member_id": "MemberID",
            },
        },
        "suppliers": {
            "table": "Supplier",
            "pk": "SupplierID",
            "cols": ["Name", "ContactNumber", "Email", "Address"],
            "api_to_db": {
                "supplier_id": "SupplierID",
                "name": "Name",
                "contact_number": "ContactNumber",
                "email": "Email",
                "address": "Address",
            },
        },
        "purchase_orders": {
            "table": "PurchaseOrder",
            "pk": "POID",
            "cols": ["SupplierID", "OrderDate", "TotalAmount", "Status"],
            "api_to_db": {
                "poid": "POID",
                "supplier_id": "SupplierID",
                "order_date": "OrderDate",
                "total_amount": "TotalAmount",
                "status": "Status",
            },
        },
        "purchase_order_items": {
            "table": "PurchaseOrderItem",
            "pk": "POItemID",
            "cols": ["POID", "ProductID", "Quantity", "CostPrice"],
            "api_to_db": {
                "po_item_id": "POItemID",
                "poid": "POID",
                "product_id": "ProductID",
                "quantity": "Quantity",
                "cost_price": "CostPrice",
            },
        },
        "sales": {
            "table": "Sale",
            "pk": "SaleID",
            "cols": ["CustomerID", "StaffID", "SaleDate", "TotalAmount"],
            "api_to_db": {
                "sale_id": "SaleID",
                "customer_id": "CustomerID",
                "staff_id": "StaffID",
                "sale_date": "SaleDate",
                "total_amount": "TotalAmount",
            },
        },
        "sale_items": {
            "table": "SaleItem",
            "pk": "SaleItemID",
            "cols": ["SaleID", "ProductID", "Quantity", "UnitPrice"],
            "api_to_db": {
                "sale_item_id": "SaleItemID",
                "sale_id": "SaleID",
                "product_id": "ProductID",
                "quantity": "Quantity",
                "unit_price": "UnitPrice",
            },
        },
        "payments": {
            "table": "Payment",
            "pk": "PaymentID",
            "cols": ["SaleID", "PaymentMethod", "Amount", "PaymentDate"],
            "api_to_db": {
                "payment_id": "PaymentID",
                "sale_id": "SaleID",
                "payment_method": "PaymentMethod",
                "amount": "Amount",
                "payment_date": "PaymentDate",
            },
        },
        "attendance": {
            "table": "Attendance",
            "pk": "AttendanceID",
            "cols": ["StaffID", "EntryTime", "ExitTime", "WorkDate"],
            "api_to_db": {
                "attendance_id": "AttendanceID",
                "staff_id": "StaffID",
                "entry_time": "EntryTime",
                "exit_time": "ExitTime",
                "work_date": "WorkDate",
            },
        },
    }

    def __init__(self):
        self.host = os.getenv("MYSQL_HOST", "127.0.0.1")
        self.port = int(os.getenv("MYSQL_PORT", "3306"))
        self.user = os.getenv("MYSQL_USER", "root")
        self.password = os.getenv("MYSQL_PASSWORD", "")
        self.database = os.getenv("MYSQL_DATABASE", "outlet_management")

    def _connect(self):
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            cursorclass=DictCursor,
            autocommit=True,
        )

    def ping(self) -> Tuple[bool, str]:
        try:
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1 AS ok")
                    cursor.fetchone()
            return True, "connected"
        except Exception as exc:
            return False, str(exc)

    def _cfg(self, table_name: str) -> Dict[str, Any]:
        if table_name not in self.TABLE_CONFIG:
            raise ValueError(f"Unsupported table '{table_name}'")
        return self.TABLE_CONFIG[table_name]

    def _db_to_api(self, table_name: str, row: Dict[str, Any]) -> Dict[str, Any]:
        cfg = self._cfg(table_name)
        reverse = {v: k for k, v in cfg["api_to_db"].items()}
        return {reverse.get(key, key): value for key, value in row.items()}

    def _to_db_payload(self, table_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        cfg = self._cfg(table_name)
        mapped = {}
        for key, value in payload.items():
            db_col = cfg["api_to_db"].get(key)
            if db_col:
                mapped[db_col] = value
        return mapped

    def list_records(self, table_name: str, filters: Optional[Dict[str, Any]] = None, order_by: Optional[str] = None) -> List[Dict[str, Any]]:
        cfg = self._cfg(table_name)
        sql = [f"SELECT * FROM {cfg['table']}"]
        args: List[Any] = []

        if filters:
            clauses = []
            for column, value in filters.items():
                if value is None:
                    continue
                if isinstance(value, tuple) and len(value) == 3 and value[0] == "COL_OP":
                    _, op, rhs_col = value
                    clauses.append(f"{column} {op} {rhs_col}")
                elif isinstance(value, tuple) and len(value) == 2:
                    op, val = value
                    clauses.append(f"{column} {op} %s")
                    args.append(val)
                else:
                    clauses.append(f"{column} = %s")
                    args.append(value)
            if clauses:
                sql.append("WHERE " + " AND ".join(clauses))

        if order_by:
            sql.append(f"ORDER BY {order_by}")

        query = " ".join(sql)
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, args)
                rows = cursor.fetchall()

        return [self._db_to_api(table_name, row) for row in rows]

    def get_record(self, table_name: str, record_id: Any) -> Optional[Dict[str, Any]]:
        cfg = self._cfg(table_name)
        query = f"SELECT * FROM {cfg['table']} WHERE {cfg['pk']} = %s"
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (record_id,))
                row = cursor.fetchone()
        if row is None:
            return None
        return self._db_to_api(table_name, row)

    def create_record(self, table_name: str, payload: Dict[str, Any]) -> int:
        cfg = self._cfg(table_name)
        mapped = self._to_db_payload(table_name, payload)

        cols = []
        values = []
        args: List[Any] = []

        if cfg["pk"] in mapped:
            cols.append(cfg["pk"])
            values.append("%s")
            args.append(mapped[cfg["pk"]])

        for col in cfg["cols"]:
            if col in mapped:
                cols.append(col)
                values.append("%s")
                args.append(mapped[col])

        if not cols:
            raise ValueError("No valid insert columns were provided")

        query = f"INSERT INTO {cfg['table']} ({', '.join(cols)}) VALUES ({', '.join(values)})"

        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, args)
                if cfg["pk"] in mapped:
                    return int(mapped[cfg["pk"]])
                return int(cursor.lastrowid)

    def update_record(self, table_name: str, record_id: Any, payload: Dict[str, Any]) -> bool:
        cfg = self._cfg(table_name)
        mapped = self._to_db_payload(table_name, payload)
        mapped.pop(cfg["pk"], None)

        if not mapped:
            raise ValueError("No updatable fields provided")

        set_parts = [f"{col} = %s" for col in mapped.keys()]
        args = list(mapped.values()) + [record_id]
        query = f"UPDATE {cfg['table']} SET {', '.join(set_parts)} WHERE {cfg['pk']} = %s"

        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, args)
                return cursor.rowcount > 0

    def delete_record(self, table_name: str, record_id: Any) -> bool:
        cfg = self._cfg(table_name)
        query = f"DELETE FROM {cfg['table']} WHERE {cfg['pk']} = %s"
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (record_id,))
                return cursor.rowcount > 0

    def table_state(self, table_name: str) -> Tuple[int, str]:
        import hashlib
        import json

        cfg = self._cfg(table_name)
        pk = cfg["pk"]
        query = f"SELECT * FROM {cfg['table']} ORDER BY {pk} ASC"
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()

        digest = hashlib.sha256()
        for row in rows:
            digest.update(str(row.get(pk)).encode("utf-8"))
            digest.update(b"|")
            digest.update(json.dumps(row, sort_keys=True, default=str).encode("utf-8"))
            digest.update(b";")

        return len(rows), digest.hexdigest()
