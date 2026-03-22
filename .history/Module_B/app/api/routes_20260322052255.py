# api/routes.py
import hashlib
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from flask import Blueprint, Response, g, jsonify, request

# Make Module_A database utilities importable after repository reorganization.
MODULE_A_DB_PATH = Path(__file__).resolve().parents[3] / "Module_A" / "database"
if MODULE_A_DB_PATH.exists() and str(MODULE_A_DB_PATH) not in sys.path:
    sys.path.insert(0, str(MODULE_A_DB_PATH))

from auth_manager import AuthenticationManager
from db_init import DatabaseInitializer
from group_manager import GroupManager
from member_manager import MemberManager
from sql_project_store import SQLProjectStore

api = Blueprint("api", __name__)

CORE_DB = "system_core"
PROJECT_DB = "outlet_management"
CORE_PROJECT_TABLE = "projects"
CORE_MEMBER_PROJECT_MAPPING_TABLE = "member_project_mappings"
PROJECT_TABLES = {
    "members": "MemberID",
    "staff": "StaffID",
    "products": "ProductID",
    "categories": "CategoryID",
    "customers": "CustomerID",
    "suppliers": "SupplierID",
    "purchase_orders": "POID",
    "purchase_order_items": "POItemID",
    "sales": "SaleID",
    "sale_items": "SaleItemID",
    "payments": "PaymentID",
    "attendance": "AttendanceID",
}
ROLE_TABLE_ACCESS = {
    "member": set(PROJECT_TABLES.keys()) | {CORE_PROJECT_TABLE},
    "customer": {"products", "categories", "sales", "payments"},
    "staff": {"products", "attendance", "categories", "customers", "sales", "sale_items", "payments"},
}
PREDEFINED_ACCOUNT_ROLES = {
    "aarav": "admin",
    "vivaan": "staff",
    "vivan": "staff",
    "customer1": "customer",
}
PUBLIC_ENDPOINTS = {
    "api.login",
    "api.login_legacy",
    "api.is_auth_legacy",
    "api.health",
    "api.welcome",
}
AUDIT_LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "audit.log")
MONITORED_TABLES = [
    (PROJECT_DB, "products"),
    (PROJECT_DB, "categories"),
    (PROJECT_DB, "customers"),
    (PROJECT_DB, "sales"),
    (PROJECT_DB, "sale_items"),
    (CORE_DB, "members"),
    (CORE_DB, "credentials"),
    (CORE_DB, "groups"),
    (CORE_DB, "member_group_mappings"),
    (CORE_DB, CORE_PROJECT_TABLE),
    (CORE_DB, CORE_MEMBER_PROJECT_MAPPING_TABLE),
]
ENDPOINT_METRICS = {}


initializer = DatabaseInitializer()
initializer.initialize_all()
db_manager = initializer.get_manager()
member_manager = MemberManager(db_manager, core_db_name=CORE_DB)
group_manager = GroupManager(db_manager, core_db_name=CORE_DB)
auth_manager = AuthenticationManager(db_manager, core_db_name=CORE_DB)
sql_project_store = SQLProjectStore()
SQL_AVAILABLE, SQL_STATUS = sql_project_store.ping()


def _next_id(table):
    records = table.get_all()
    if not records:
        return 1
    return max(record_id for record_id, _ in records) + 1


def _append_file_audit(entry):
    line = json.dumps(entry, ensure_ascii=True, default=str)
    with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as audit_file:
        audit_file.write(line + "\n")


def _insert_audit_table_entry(entry):
    audit_table, _ = db_manager.get_table(CORE_DB, "audit_log")
    audit_record = {
        "audit_id": _next_id(audit_table),
        "action_type": entry["action"],
        "table_name": entry["table"],
        "record_id": entry.get("record_id") if isinstance(entry.get("record_id"), int) else 0,
        "member_id": entry.get("actor_member_id", 0),
        "change_details": json.dumps(entry, ensure_ascii=True, default=str),
        "timestamp": entry["timestamp"],
    }
    audit_table.insert(audit_record)


def _compute_table_state(db_name, table_name):
    if db_name == PROJECT_DB:
        if not SQL_AVAILABLE:
            raise ValueError(f"SQL backend unavailable: {SQL_STATUS}")
        row_count, checksum = sql_project_store.table_state(table_name)
        return {
            "row_count": row_count,
            "key_checksum": checksum,
        }

    table, message = db_manager.get_table(db_name, table_name)
    if table is None:
        raise ValueError(message)

    records = table.get_all()
    digest = hashlib.sha256()
    for record_id, record_data in records:
        digest.update(str(record_id).encode("utf-8"))
        digest.update(b"|")
        digest.update(json.dumps(record_data, sort_keys=True, default=str).encode("utf-8"))
        digest.update(b";")

    return {
        "row_count": len(records),
        "key_checksum": digest.hexdigest(),
    }


def _ensure_api_audit_state_table():
    schema = {
        "state_id": int,
        "db_name": str,
        "table_name": str,
        "row_count": int,
        "key_checksum": str,
        "last_api_write_at": str,
        "last_api_actor": str,
        "source_marker": str,
    }
    db_manager.create_table(
        CORE_DB,
        "api_audit_state",
        schema,
        order=8,
        search_key="state_id",
    )


def _latest_api_state(db_name, table_name):
    state_table, _ = db_manager.get_table(CORE_DB, "api_audit_state")
    matches = state_table.search({"db_name": db_name, "table_name": table_name})
    if not matches:
        return None, None
    matches.sort(key=lambda item: item[0], reverse=True)
    return matches[0]


def _upsert_expected_state(db_name, table_name, actor, source_marker="session_validated_api"):
    state_table, _ = db_manager.get_table(CORE_DB, "api_audit_state")
    now = datetime.utcnow().isoformat()
    state = _compute_table_state(db_name, table_name)
    latest_id, latest_data = _latest_api_state(db_name, table_name)

    payload = {
        "db_name": db_name,
        "table_name": table_name,
        "row_count": state["row_count"],
        "key_checksum": state["key_checksum"],
        "last_api_write_at": now,
        "last_api_actor": actor,
        "source_marker": source_marker,
    }

    if latest_data is None:
        payload["state_id"] = _next_id(state_table)
        state_table.insert(payload)
    else:
        payload["state_id"] = latest_data["state_id"]
        state_table.update(latest_id, payload)


def _audit_write(action, db_name, table_name, record_id, status, details):
    actor_member_id = getattr(g, "current_member_id", 0)
    actor_username = getattr(g, "current_member", {}).get("username", "system") if hasattr(g, "current_member") else "system"
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "action": action,
        "db": db_name,
        "table": table_name,
        "record_id": record_id,
        "status": status,
        "details": details,
        "actor_member_id": actor_member_id,
        "actor_username": actor_username,
        "source": "session_validated_api",
    }
    _append_file_audit(entry)
    _insert_audit_table_entry(entry)

    if status == "success":
        _upsert_expected_state(
            db_name,
            table_name,
            actor=f"{actor_username}:{actor_member_id}",
            source_marker="session_validated_api",
        )


def _admin_forbidden_response():
    if not getattr(g, "is_admin", False):
        return jsonify({"error": "Admin role required for this operation"}), 403
    return None


def _record_endpoint_metric(duration_ms, status_code):
    if request.path.startswith("/static/"):
        return

    route_pattern = request.path
    if getattr(request, "url_rule", None) is not None and request.url_rule.rule:
        route_pattern = request.url_rule.rule

    metric_key = f"{request.method} {route_pattern}"
    existing = ENDPOINT_METRICS.get(
        metric_key,
        {
            "hits": 0,
            "total_ms": 0.0,
            "max_ms": 0.0,
            "errors": 0,
            "slow_hits": 0,
            "last_status": 200,
            "last_seen_at": None,
        },
    )

    existing["hits"] += 1
    existing["total_ms"] += duration_ms
    existing["max_ms"] = max(existing["max_ms"], duration_ms)
    existing["last_status"] = int(status_code)
    existing["last_seen_at"] = datetime.utcnow().isoformat()
    if status_code >= 400:
        existing["errors"] += 1
    if duration_ms >= 75.0:
        existing["slow_hits"] += 1

    ENDPOINT_METRICS[metric_key] = existing


def _ensure_member_project_tables():
    projects_schema = {
        "project_id": int,
        "project_name": str,
        "description": str,
        "status": str,
        "created_at": str,
        "updated_at": str,
    }
    db_manager.create_table(
        CORE_DB,
        CORE_PROJECT_TABLE,
        projects_schema,
        order=8,
        search_key="project_id",
    )

    mapping_schema = {
        "mapping_id": int,
        "member_id": int,
        "project_id": int,
        "assigned_at": str,
    }
    db_manager.create_table(
        CORE_DB,
        CORE_MEMBER_PROJECT_MAPPING_TABLE,
        mapping_schema,
        order=8,
        search_key="mapping_id",
    )


def _next_table_id(table_name, id_field):
    table, _ = db_manager.get_table(CORE_DB, table_name)
    records = table.get_all()
    if not records:
        return 1
    max_id = 0
    for _, data in records:
        value = data.get(id_field, 0)
        if isinstance(value, int):
            max_id = max(max_id, value)
    return max_id + 1


def _member_project_ids(member_id):
    mapping_table, _ = db_manager.get_table(CORE_DB, CORE_MEMBER_PROJECT_MAPPING_TABLE)
    mappings = mapping_table.get_all()
    return {
        row.get("project_id")
        for _, row in mappings
        if row.get("member_id") == member_id and isinstance(row.get("project_id"), int)
    }


def _project_record(project_id):
    project_table, _ = db_manager.get_table(CORE_DB, CORE_PROJECT_TABLE)
    return project_table.get(project_id)


def _project_member_ids(project_id):
    mapping_table, _ = db_manager.get_table(CORE_DB, CORE_MEMBER_PROJECT_MAPPING_TABLE)
    mappings = mapping_table.get_all()
    return {
        row.get("member_id")
        for _, row in mappings
        if row.get("project_id") == project_id and isinstance(row.get("member_id"), int)
    }


def _member_projects(member_id):
    project_ids = _member_project_ids(member_id)
    projects = []
    for project_id in sorted(project_ids):
        project = _project_record(project_id)
        if project:
            projects.append(project)
    return projects


def _assign_member_to_project(member_id, project_id):
    members_table, _ = db_manager.get_table(CORE_DB, "members")
    if not members_table.get(member_id):
        return {"success": False, "message": f"Member {member_id} not found"}

    project = _project_record(project_id)
    if not project:
        return {"success": False, "message": f"Project {project_id} not found"}

    mapping_table, _ = db_manager.get_table(CORE_DB, CORE_MEMBER_PROJECT_MAPPING_TABLE)
    all_rows = mapping_table.get_all()
    for _, row in all_rows:
        if row.get("member_id") == member_id and row.get("project_id") == project_id:
            return {"success": False, "message": "Member already assigned to project"}

    mapping_id = _next_table_id(CORE_MEMBER_PROJECT_MAPPING_TABLE, "mapping_id")
    record = {
        "mapping_id": mapping_id,
        "member_id": member_id,
        "project_id": project_id,
        "assigned_at": datetime.utcnow().isoformat(),
    }
    mapping_table.insert(record)
    return {"success": True, "mapping_id": mapping_id, "record": record}


def _remove_member_from_project(member_id, project_id):
    mapping_table, _ = db_manager.get_table(CORE_DB, CORE_MEMBER_PROJECT_MAPPING_TABLE)
    all_rows = mapping_table.get_all()
    for record_id, row in all_rows:
        if row.get("member_id") == member_id and row.get("project_id") == project_id:
            mapping_table.delete(record_id)
            return {"success": True, "message": "Member removed from project"}
    return {"success": False, "message": "Member-project mapping not found"}


def _seed_if_needed():
    members = member_manager.list_all_members()
    if members:
        existing_usernames = {m.get("username") for m in members}
        if "customer1" not in existing_usernames:
            member_manager.create_member(
                username="customer1",
                email="customer1@example.com",
                full_name="Portal Customer",
                department="Customer",
                password="Customer@123",
            )
        return

    seed_members = [
        {
            "username": "aarav",
            "email": "aarav.sharma@example.com",
            "full_name": "Aarav Sharma",
            "department": "Management",
            "password": "Aarav@123",
        },
        {
            "username": "vivaan",
            "email": "vivaan.singh@example.com",
            "full_name": "Vivaan Singh",
            "department": "Sales",
            "password": "Vivaan@123",
        },
        {
            "username": "ananya",
            "email": "ananya.patel@example.com",
            "full_name": "Ananya Patel",
            "department": "Cashier",
            "password": "Ananya@123",
        },
        {
            "username": "rohan",
            "email": "rohan.desai@example.com",
            "full_name": "Rohan Desai",
            "department": "Accounting",
            "password": "Rohan@123",
        },
    ]

    for member in seed_members:
        member_manager.create_member(**member)

    member_manager.create_member(
        username="customer1",
        email="customer1@example.com",
        full_name="Portal Customer",
        department="Customer",
        password="Customer@123",
    )

    groups = [
        ("admins", "System administrators"),
        ("sales_team", "Sales and cashier team"),
        ("finance", "Accounting and finance"),
    ]
    for group_name, description in groups:
        group_manager.create_group(group_name, description)

    group_manager.add_member_to_group(member_id=1, group_id=1, role="admin")
    group_manager.add_member_to_group(member_id=2, group_id=2, role="user")
    group_manager.add_member_to_group(member_id=3, group_id=2, role="user")
    group_manager.add_member_to_group(member_id=4, group_id=3, role="user")

    products_table, _ = db_manager.get_table(PROJECT_DB, "products")
    if not products_table.get_all():
        products_table.insert(
            {
                "product_id": 1,
                "name": "Smartphone",
                "price": 15000.0,
                "stock_quantity": 50,
                "reorder_level": 5,
                "category_id": 1,
                "created_at": "2025-01-01T00:00:00",
            }
        )

    project_table, _ = db_manager.get_table(CORE_DB, CORE_PROJECT_TABLE)
    if not project_table.get_all():
        now = datetime.utcnow().isoformat()
        project_table.insert(
            {
                "project_id": 1,
                "project_name": "Retail Dashboard Revamp",
                "description": "Revamp dashboard and KPI widgets",
                "status": "active",
                "created_at": now,
                "updated_at": now,
            }
        )
        project_table.insert(
            {
                "project_id": 2,
                "project_name": "POS Performance Audit",
                "description": "Optimize checkout performance and reporting",
                "status": "active",
                "created_at": now,
                "updated_at": now,
            }
        )

    mapping_table, _ = db_manager.get_table(CORE_DB, CORE_MEMBER_PROJECT_MAPPING_TABLE)
    if not mapping_table.get_all():
        _assign_member_to_project(member_id=1, project_id=1)
        _assign_member_to_project(member_id=2, project_id=1)
        _assign_member_to_project(member_id=3, project_id=2)
        _assign_member_to_project(member_id=4, project_id=2)
        products_table.insert(
            {
                "product_id": 2,
                "name": "Laptop",
                "price": 55000.0,
                "stock_quantity": 20,
                "reorder_level": 3,
                "category_id": 1,
                "created_at": "2025-01-01T00:00:00",
            }
        )


_ensure_member_project_tables()
_seed_if_needed()
_ensure_api_audit_state_table()

# Initialize expected state baselines. If SQL is unavailable, skip project DB
# baselines so the API can still boot for core auth/RBAC demonstrations.
for db_name, table_name in MONITORED_TABLES:
    if db_name == PROJECT_DB and not SQL_AVAILABLE:
        continue
    try:
        _upsert_expected_state(db_name, table_name, actor="system-bootstrap", source_marker="bootstrap")
    except Exception:
        # Keep bootstrap resilient; errors are surfaced via health/admin checks.
        continue


def _extract_token():
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    return request.headers.get("X-Session-Token", "").strip()


def _member_groups(member_id):
    return group_manager.get_member_groups(member_id)


def _is_admin(member_id):
    for group in _member_groups(member_id):
        if group.get("role_in_group") == "admin":
            return True
        if str(group.get("group_name", "")).lower() == "admins":
            return True
    return False


def _resolve_member_role(member_id, member_record=None):
    if _is_admin(member_id):
        return "member"

    member_record = member_record or member_manager.get_member(member_id) or {}
    department = str(member_record.get("department", "")).strip().lower()
    if department == "customer":
        return "customer"

    for group in _member_groups(member_id):
        group_name = str(group.get("group_name", "")).strip().lower()
        if group_name in {"customer", "customers"}:
            return "customer"

    return "staff"


def _resolve_portal_role(member_id, member_record=None):
    member_record = member_record or member_manager.get_member(member_id) or {}
    username = str(member_record.get("username", "")).strip().lower()
    predefined_role = PREDEFINED_ACCOUNT_ROLES.get(username)

    if predefined_role == "admin":
        return "member"
    if predefined_role == "staff":
        return "staff"
    if predefined_role == "customer":
        return "customer"

    if _is_admin(member_id):
        return "member"

    internal_role = _resolve_member_role(member_id, member_record)
    if internal_role == "customer":
        return "customer"
    return "staff"


def _is_table_allowed(table_name, role_name):
    allowed = ROLE_TABLE_ACCESS.get(role_name, set())
    return table_name in allowed


def _table_forbidden_response(table_name):
    role_name = getattr(g, "role_name", "staff")
    if _is_table_allowed(table_name, role_name):
        return None
    return (
        jsonify(
            {
                "error": f"Role '{role_name}' cannot access table '{table_name}'",
                "role": role_name,
                "allowed_tables": sorted(ROLE_TABLE_ACCESS.get(role_name, set())),
            }
        ),
        403,
    )


def _can_view_member(requester_id, target_id):
    if requester_id == target_id:
        return True
    if _is_admin(requester_id):
        return True

    requester_project_ids = _member_project_ids(requester_id)
    target_project_ids = _member_project_ids(target_id)
    return bool(requester_project_ids.intersection(target_project_ids))


def _allowed_self_portfolio_fields():
    return {"full_name", "email", "department"}


def _find_member_by_username(username):
    for member in member_manager.list_all_members():
        if member.get("username") == username:
            return member
    return None


def _ensure_sql_backend():
    if not SQL_AVAILABLE:
        return False, SQL_STATUS
    return True, "connected"


def _get_project_table_name(table_name):
    if table_name == CORE_PROJECT_TABLE:
        return table_name, "OK"
    if table_name not in PROJECT_TABLES:
        return None, f"Unsupported table '{table_name}'"
    return table_name, "OK"


def _coerce_record_id(record_id):
    return int(record_id)


FALLBACK_ID_FIELDS = {
    "products": "product_id",
    "categories": "category_id",
    "customers": "customer_id",
    "sales": "sale_id",
    "sale_items": "sale_item_id",
}


def _fallback_table(table_name):
    if table_name == "members":
        return db_manager.get_table(CORE_DB, "members")
    return db_manager.get_table(PROJECT_DB, table_name)


def _fallback_list_records(table_name):
    table, message = _fallback_table(table_name)
    if table is None:
        return None, message
    records = [{"id": record_id, "data": record_data} for record_id, record_data in table.get_all()]
    return records, "OK"


def _fallback_get_record(table_name, normalized_id):
    table, message = _fallback_table(table_name)
    if table is None:
        return None, message
    return table.get(normalized_id), "OK"


def _fallback_create_record(table_name, payload):
    table, message = _fallback_table(table_name)
    if table is None:
        return None, message

    record = dict(payload)
    id_field = FALLBACK_ID_FIELDS.get(table_name)
    if id_field and not isinstance(record.get(id_field), int):
        record[id_field] = _next_id(table)

    table.insert(record)
    record_id = record.get(id_field) if id_field else _next_id(table) - 1
    return int(record_id) if isinstance(record_id, int) else None, "OK"


def _fallback_update_record(table_name, normalized_id, payload):
    table, message = _fallback_table(table_name)
    if table is None:
        return None, message

    current = table.get(normalized_id)
    if not current:
        return False, "Record not found"

    updated = current.copy()
    updated.update(payload)
    table.update(normalized_id, updated)
    return True, "OK"


def _fallback_delete_record(table_name, normalized_id):
    table, message = _fallback_table(table_name)
    if table is None:
        return None, message

    current = table.get(normalized_id)
    if not current:
        return False, "Record not found"

    table.delete(normalized_id)
    return True, "OK"


def _build_sql_filters_and_order(table_name):
    args = request.args
    filters = {}
    order_by = None

    if table_name == "products":
        if args.get("category_id"):
            filters["CategoryID"] = int(args.get("category_id"))
        if args.get("name"):
            filters["Name"] = args.get("name")
        if args.get("low_stock") == "1":
            filters["StockQuantity"] = ("COL_OP", "<=", "ReorderLevel")
        sort = args.get("sort")
        if sort == "price_asc":
            order_by = "Price ASC"
        elif sort == "price_desc":
            order_by = "Price DESC"

    elif table_name == "customers":
        if args.get("email"):
            filters["Email"] = args.get("email")
        if args.get("contact_number"):
            filters["ContactNumber"] = args.get("contact_number")
        if args.get("min_loyalty"):
            filters["LoyaltyPoints"] = (">=", int(args.get("min_loyalty")))
        sort = args.get("sort")
        if sort == "loyalty_desc":
            order_by = "LoyaltyPoints DESC"

    elif table_name == "sales":
        if args.get("customer_id"):
            filters["CustomerID"] = int(args.get("customer_id"))
        if args.get("staff_id"):
            filters["StaffID"] = int(args.get("staff_id"))
        if args.get("start_date"):
            filters["SaleDate"] = (">=", args.get("start_date"))
        sort = args.get("sort")
        if sort == "sale_date_desc":
            order_by = "SaleDate DESC"
        elif sort == "sale_date_asc":
            order_by = "SaleDate ASC"

    elif table_name == "sale_items":
        if args.get("sale_id"):
            filters["SaleID"] = int(args.get("sale_id"))
        if args.get("product_id"):
            filters["ProductID"] = int(args.get("product_id"))

    return filters, order_by


@api.before_request
def require_session_for_api_calls():
    g.request_start = time.perf_counter()

    if request.endpoint in PUBLIC_ENDPOINTS:
        return None

    token = _extract_token()
    if not token:
        return jsonify({"error": "Missing session token"}), 401

    session_status = auth_manager.validate_session(token)
    if not session_status.get("valid"):
        return jsonify({"error": session_status.get("message", "Invalid session")}), 401

    member_id = session_status.get("member_id")
    member = member_manager.get_member(member_id)
    if not member:
        return jsonify({"error": "Session user not found"}), 401

    g.session_token = token
    g.current_member_id = member_id
    g.current_member = member
    g.is_admin = _is_admin(member_id)
    g.role_name = _resolve_member_role(member_id, member)
    g.portal_role = _resolve_portal_role(member_id, member)
    return None


@api.after_request
def track_response_metrics(response):
    started = getattr(g, "request_start", None)
    if started is not None:
        duration_ms = (time.perf_counter() - started) * 1000.0
        _record_endpoint_metric(duration_ms, response.status_code)
    return response


@api.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "local-api"})


@api.route("/", methods=["GET"])
def welcome():
    return jsonify({"message": "Welcome to test APIs"})


@api.route("/auth/login", methods=["POST"])
def login():
    payload = request.get_json(silent=True) or {}
    username = payload.get("username")
    password = payload.get("password")
    portal_role = str(payload.get("portal_role", "")).strip().lower()

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    if portal_role and portal_role not in {"member", "staff", "customer"}:
        return jsonify({"error": "portal_role must be one of member, staff, customer"}), 400

    member_before = _find_member_by_username(username)
    result = auth_manager.login(username=username, password=password)
    login_audit = {
        "timestamp": datetime.utcnow().isoformat(),
        "action": "auth_login",
        "db": CORE_DB,
        "table": "credentials",
        "record_id": member_before.get("member_id") if member_before else 0,
        "status": "success" if result.get("success") else "failed",
        "details": result.get("message", "Login attempt"),
        "actor_member_id": member_before.get("member_id") if member_before else 0,
        "actor_username": username,
        "source": "session_validated_api",
    }
    _append_file_audit(login_audit)
    _insert_audit_table_entry(login_audit)
    if member_before:
        _upsert_expected_state(CORE_DB, "credentials", actor=f"{username}:{member_before.get('member_id', 0)}")

    if not result.get("success"):
        return jsonify({"error": result.get("message", "Login failed")}), 401

    member = member_manager.get_member(result["member_id"])
    resolved_portal_role = _resolve_portal_role(result["member_id"], member)
    if portal_role and portal_role != resolved_portal_role:
        auth_manager.logout(result["session_token"])
        return (
            jsonify(
                {
                    "error": f"Selected role '{portal_role}' does not match account role '{resolved_portal_role}'",
                    "expected_role": resolved_portal_role,
                }
            ),
            403,
        )

    resolved_internal_role = _resolve_member_role(result["member_id"], member)
    return jsonify(
        {
            "message": result.get("message", "Login successful"),
            "session_token": result["session_token"],
            "member": member,
            "role": resolved_internal_role,
            "portal_role": resolved_portal_role,
            "allowed_tables": sorted(ROLE_TABLE_ACCESS.get(resolved_internal_role, set())),
        }
    )


@api.route("/login", methods=["POST"])
def login_legacy():
    """Legacy compatibility endpoint required by assignment appendix."""
    return login()


@api.route("/auth/logout", methods=["POST"])
def logout():
    result = auth_manager.logout(g.session_token)
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Logout failed")}), 400
    return jsonify({"message": result.get("message", "Logged out")})


@api.route("/auth/me", methods=["GET"])
def auth_me():
    return jsonify(
        {
            "member": g.current_member,
            "is_admin": g.is_admin,
            "role": g.role_name,
            "portal_role": g.portal_role,
            "allowed_tables": sorted(ROLE_TABLE_ACCESS.get(g.role_name, set())),
            "groups": _member_groups(g.current_member_id),
        }
    )


@api.route("/isAuth", methods=["GET"])
def is_auth_legacy():
    """Legacy compatibility endpoint required by assignment appendix."""
    token = _extract_token() or request.args.get("session_token", "").strip()
    if not token:
        return jsonify({"error": "No session found"}), 401

    session_status = auth_manager.validate_session(token)
    if not session_status.get("valid"):
        message = session_status.get("message", "Invalid session token")
        lowered = message.lower()
        if "expired" in lowered:
            return jsonify({"error": "Session expired"}), 401
        return jsonify({"error": "Invalid session token"}), 401

    member_id = session_status.get("member_id")
    member = member_manager.get_member(member_id)
    if not member:
        return jsonify({"error": "Invalid session token"}), 401

    return jsonify(
        {
            "message": "User is authenticated",
            "username": member.get("username"),
            "role": _resolve_member_role(member_id, member),
            "expiry": auth_manager.active_sessions.get(token, {}).get("expires_at"),
        }
    )


@api.route("/project/<table_name>", methods=["GET"])
def list_project_records(table_name):
    table_name, message = _get_project_table_name(table_name)
    if table_name is None:
        return jsonify({"error": message}), 404

    forbidden = _table_forbidden_response(table_name)
    if forbidden:
        return forbidden

    if table_name == CORE_PROJECT_TABLE:
        table, _ = db_manager.get_table(CORE_DB, CORE_PROJECT_TABLE)
        records = [{"id": data.get("project_id"), "data": data} for _, data in table.get_all()]
        return jsonify({"table": table_name, "records": records, "count": len(records)})

    ok, status = _ensure_sql_backend()
    if not ok:
        records, fallback_message = _fallback_list_records(table_name)
        if records is None:
            return jsonify({"error": f"SQL backend unavailable: {status}", "fallback_error": fallback_message}), 503
        return jsonify({"table": table_name, "records": records, "count": len(records), "backend": "bplustree_fallback"})

    filters, order_by = _build_sql_filters_and_order(table_name)
    try:
        records_raw = sql_project_store.list_records(table_name, filters=filters, order_by=order_by)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400

    id_key = {
        "members": "member_id",
        "staff": "staff_id",
        "products": "product_id",
        "categories": "category_id",
        "customers": "customer_id",
        "suppliers": "supplier_id",
        "purchase_orders": "poid",
        "purchase_order_items": "po_item_id",
        "sales": "sale_id",
        "sale_items": "sale_item_id",
        "payments": "payment_id",
        "attendance": "attendance_id",
    }[table_name]
    records = [{"id": record_data.get(id_key), "data": record_data} for record_data in records_raw]
    return jsonify({"table": table_name, "records": records, "count": len(records)})


@api.route("/project/<table_name>/<record_id>", methods=["GET"])
def get_project_record(table_name, record_id):
    table_name, message = _get_project_table_name(table_name)
    if table_name is None:
        return jsonify({"error": message}), 404

    forbidden = _table_forbidden_response(table_name)
    if forbidden:
        return forbidden

    try:
        normalized_id = _coerce_record_id(record_id)
    except ValueError:
        return jsonify({"error": "Invalid record id type"}), 400

    if table_name == CORE_PROJECT_TABLE:
        record = _project_record(normalized_id)
        if record is None:
            return jsonify({"error": "Record not found"}), 404
        return jsonify({"id": normalized_id, "data": record})

    ok, status = _ensure_sql_backend()
    if not ok:
        record, fallback_message = _fallback_get_record(table_name, normalized_id)
        if fallback_message != "OK":
            return jsonify({"error": f"SQL backend unavailable: {status}", "fallback_error": fallback_message}), 503
        if record is None:
            return jsonify({"error": "Record not found"}), 404
        return jsonify({"id": normalized_id, "data": record, "backend": "bplustree_fallback"})

    record = sql_project_store.get_record(table_name, normalized_id)
    if record is None:
        return jsonify({"error": "Record not found"}), 404
    return jsonify({"id": normalized_id, "data": record})


@api.route("/project/<table_name>", methods=["POST"])
def create_project_record(table_name):
    forbidden = _admin_forbidden_response()
    if forbidden:
        return forbidden

    table_name, message = _get_project_table_name(table_name)
    if table_name is None:
        return jsonify({"error": message}), 404

    forbidden = _table_forbidden_response(table_name)
    if forbidden:
        return forbidden

    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "Record data is required"}), 400

    if table_name == CORE_PROJECT_TABLE:
        table, _ = db_manager.get_table(CORE_DB, CORE_PROJECT_TABLE)
        project_id = payload.get("project_id") if isinstance(payload.get("project_id"), int) else _next_table_id(CORE_PROJECT_TABLE, "project_id")
        all_projects = table.get_all()
        for _, row in all_projects:
            if row.get("project_id") == project_id:
                return jsonify({"error": f"Project {project_id} already exists"}), 400
            if row.get("project_name") == payload.get("project_name"):
                return jsonify({"error": "Project name already exists"}), 400

        now = datetime.utcnow().isoformat()
        record = {
            "project_id": project_id,
            "project_name": payload.get("project_name", "").strip(),
            "description": payload.get("description", ""),
            "status": payload.get("status", "active"),
            "created_at": payload.get("created_at", now),
            "updated_at": now,
        }
        if not record["project_name"]:
            return jsonify({"error": "project_name is required"}), 400
        table.insert(record)
        _audit_write("create", CORE_DB, CORE_PROJECT_TABLE, project_id, "success", "Project created")
        return jsonify({"message": "Record created", "id": project_id}), 201

    ok, status = _ensure_sql_backend()
    if not ok:
        if isinstance(payload, list):
            results = []
            for record in payload:
                created_id, fallback_message = _fallback_create_record(table_name, record)
                if fallback_message != "OK":
                    results.append({"status": "failed", "error": fallback_message})
                else:
                    results.append({"status": "success", "id": created_id})
            return jsonify({"message": "Bulk insert processed", "results": results, "backend": "bplustree_fallback"}), 201

        created_id, fallback_message = _fallback_create_record(table_name, payload)
        if fallback_message != "OK":
            return jsonify({"error": f"SQL backend unavailable: {status}", "fallback_error": fallback_message}), 503
        _audit_write("create", PROJECT_DB, table_name, created_id if isinstance(created_id, int) else -1, "success", "Record created (fallback)")
        return jsonify({"message": "Record created", "id": created_id, "backend": "bplustree_fallback"}), 201

    if isinstance(payload, list):
        results = []
        for record in payload:
            try:
                result = sql_project_store.create_record(table_name, record)
                results.append({"status": "success", "id": result})
                _audit_write("create", PROJECT_DB, table_name, result, "success", "Bulk insert item created")
            except Exception as exc:
                error_text = str(exc)
                results.append({"status": "failed", "error": error_text})
                _audit_write("create", PROJECT_DB, table_name, -1, "failed", error_text)
        return jsonify({"message": "Bulk insert processed", "results": results}), 201

    try:
        result = sql_project_store.create_record(table_name, payload)
    except Exception as exc:
        _audit_write("create", PROJECT_DB, table_name, -1, "failed", str(exc))
        return jsonify({"error": str(exc)}), 400
    _audit_write("create", PROJECT_DB, table_name, result, "success", "Record created")
    return jsonify({"message": "Record created", "id": result}), 201


@api.route("/project/<table_name>/<record_id>", methods=["PUT"])
def update_project_record(table_name, record_id):
    forbidden = _admin_forbidden_response()
    if forbidden:
        return forbidden

    table_name, message = _get_project_table_name(table_name)
    if table_name is None:
        return jsonify({"error": message}), 404

    forbidden = _table_forbidden_response(table_name)
    if forbidden:
        return forbidden

    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "Record data is required"}), 400

    try:
        normalized_id = _coerce_record_id(record_id)
    except ValueError:
        return jsonify({"error": "Invalid record id type"}), 400

    if table_name == CORE_PROJECT_TABLE:
        table, _ = db_manager.get_table(CORE_DB, CORE_PROJECT_TABLE)
        current = table.get(normalized_id)
        if not current:
            _audit_write("update", CORE_DB, CORE_PROJECT_TABLE, normalized_id, "failed", "Record not found")
            return jsonify({"error": "Record not found"}), 404

        updated = current.copy()
        for field in ("project_name", "description", "status"):
            if field in payload:
                updated[field] = payload[field]
        updated["updated_at"] = datetime.utcnow().isoformat()
        table.update(normalized_id, updated)
        _audit_write("update", CORE_DB, CORE_PROJECT_TABLE, normalized_id, "success", "Project updated")
        return jsonify({"message": f"Record '{normalized_id}' updated successfully"})

    ok, status = _ensure_sql_backend()
    if not ok:
        updated, fallback_message = _fallback_update_record(table_name, normalized_id, payload)
        if fallback_message != "OK":
            if fallback_message == "Record not found":
                return jsonify({"error": "Record not found"}), 404
            return jsonify({"error": f"SQL backend unavailable: {status}", "fallback_error": fallback_message}), 503
        _audit_write("update", PROJECT_DB, table_name, normalized_id, "success", "Record updated (fallback)")
        return jsonify({"message": f"Record '{normalized_id}' updated successfully", "backend": "bplustree_fallback"})

    try:
        updated = sql_project_store.update_record(table_name, normalized_id, payload)
    except Exception as exc:
        _audit_write("update", PROJECT_DB, table_name, normalized_id, "failed", str(exc))
        return jsonify({"error": str(exc)}), 400

    if not updated:
        _audit_write("update", PROJECT_DB, table_name, normalized_id, "failed", "Record not found")
        return jsonify({"error": "Record not found"}), 404

    _audit_write("update", PROJECT_DB, table_name, normalized_id, "success", "Record updated")
    return jsonify({"message": f"Record '{normalized_id}' updated successfully"})


@api.route("/project/<table_name>/<record_id>", methods=["DELETE"])
def delete_project_record(table_name, record_id):
    forbidden = _admin_forbidden_response()
    if forbidden:
        return forbidden

    table_name, message = _get_project_table_name(table_name)
    if table_name is None:
        return jsonify({"error": message}), 404

    forbidden = _table_forbidden_response(table_name)
    if forbidden:
        return forbidden

    try:
        normalized_id = _coerce_record_id(record_id)
    except ValueError:
        return jsonify({"error": "Invalid record id type"}), 400

    if table_name == CORE_PROJECT_TABLE:
        table, _ = db_manager.get_table(CORE_DB, CORE_PROJECT_TABLE)
        current = table.get(normalized_id)
        if not current:
            _audit_write("delete", CORE_DB, CORE_PROJECT_TABLE, normalized_id, "failed", "Record not found")
            return jsonify({"error": "Record not found"}), 404

        mapping_table, _ = db_manager.get_table(CORE_DB, CORE_MEMBER_PROJECT_MAPPING_TABLE)
        all_maps = mapping_table.get_all()
        for map_id, row in all_maps:
            if row.get("project_id") == normalized_id:
                mapping_table.delete(map_id)

        table.delete(normalized_id)
        _audit_write("delete", CORE_DB, CORE_PROJECT_TABLE, normalized_id, "success", "Project deleted")
        return jsonify({"message": f"Record '{normalized_id}' deleted successfully"})

    ok, status = _ensure_sql_backend()
    if not ok:
        deleted, fallback_message = _fallback_delete_record(table_name, normalized_id)
        if fallback_message != "OK":
            if fallback_message == "Record not found":
                return jsonify({"error": "Record not found"}), 404
            return jsonify({"error": f"SQL backend unavailable: {status}", "fallback_error": fallback_message}), 503
        _audit_write("delete", PROJECT_DB, table_name, normalized_id, "success", "Record deleted (fallback)")
        return jsonify({"message": f"Record '{normalized_id}' deleted successfully", "backend": "bplustree_fallback"})

    try:
        deleted = sql_project_store.delete_record(table_name, normalized_id)
    except Exception as exc:
        _audit_write("delete", PROJECT_DB, table_name, normalized_id, "failed", str(exc))
        return jsonify({"error": str(exc)}), 400

    if not deleted:
        _audit_write("delete", PROJECT_DB, table_name, normalized_id, "failed", "Record not found")
        return jsonify({"error": "Record not found"}), 404

    _audit_write("delete", PROJECT_DB, table_name, normalized_id, "success", "Record deleted")
    return jsonify({"message": f"Record '{normalized_id}' deleted successfully"})


@api.route("/member-portfolio", methods=["GET"])
def member_portfolio():
    all_members = member_manager.list_all_members()
    visible = []

    for member in all_members:
        member_id = member.get("member_id")
        if _can_view_member(g.current_member_id, member_id):
            visible.append(
                {
                    "member_id": member_id,
                    "username": member.get("username"),
                    "full_name": member.get("full_name"),
                    "email": member.get("email"),
                    "department": member.get("department"),
                    "status": member.get("status"),
                    "groups": _member_groups(member_id),
                    "projects": _member_projects(member_id),
                }
            )

    return jsonify({"records": visible, "count": len(visible)})


@api.route("/member-portfolio/<int:member_id>", methods=["GET"])
def member_portfolio_detail(member_id):
    member = member_manager.get_member(member_id)
    if not member:
        return jsonify({"error": "Member not found"}), 404

    if not _can_view_member(g.current_member_id, member_id):
        return jsonify({"error": "Permission denied for this member profile"}), 403

    return jsonify(
        {
            "member": member,
            "groups": _member_groups(member_id),
            "projects": _member_projects(member_id),
            "can_manage": g.is_admin,
        }
    )


@api.route("/members", methods=["GET"])
def list_members():
    members = member_manager.list_all_members()
    return jsonify({"records": members, "count": len(members)})


@api.route("/members/<int:member_id>", methods=["GET"])
def get_member(member_id):
    member = member_manager.get_member(member_id)
    if not member:
        return jsonify({"error": "Member not found"}), 404

    if not _can_view_member(g.current_member_id, member_id):
        return jsonify({"error": "Permission denied for this member profile"}), 403

    return jsonify({"member": member, "projects": _member_projects(member_id)})


@api.route("/members", methods=["POST"])
def create_member():
    forbidden = _admin_forbidden_response()
    if forbidden:
        return forbidden

    payload = request.get_json(silent=True) or {}
    required = ["username", "email", "full_name", "department", "password"]
    missing = [field for field in required if not payload.get(field)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    result = member_manager.create_member(
        username=payload["username"],
        email=payload["email"],
        full_name=payload["full_name"],
        department=payload["department"],
        password=payload["password"],
    )
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Create failed")}), 400
    return jsonify(result), 201


@api.route("/members/<int:member_id>", methods=["PUT"])
def update_member(member_id):
    payload = request.get_json(silent=True) or {}

    if not (g.is_admin or g.current_member_id == member_id):
        return jsonify({"error": "Permission denied"}), 403

    if not g.is_admin and getattr(g, "role_name", "staff") == "customer":
        return jsonify({"error": "Customers cannot update portfolio"}), 403

    if not g.is_admin:
        allowed_fields = _allowed_self_portfolio_fields()
        payload = {key: value for key, value in payload.items() if key in allowed_fields}

    if not payload:
        return jsonify({"error": "No valid fields provided"}), 400

    result = member_manager.update_member(member_id, payload)
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Update failed")}), 400
    return jsonify(result)


@api.route("/members/<int:member_id>", methods=["DELETE"])
def delete_member(member_id):
    forbidden = _admin_forbidden_response()
    if forbidden:
        return forbidden

    result = member_manager.delete_member(member_id)
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Delete failed")}), 400
    return jsonify(result)


@api.route("/projects/<int:project_id>/members", methods=["GET"])
def project_members(project_id):
    project = _project_record(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    member_ids = sorted(_project_member_ids(project_id))
    members = []
    for member_id in member_ids:
        member = member_manager.get_member(member_id)
        if member:
            members.append(member)

    return jsonify({"project": project, "members": members, "count": len(members)})


@api.route("/projects/<int:project_id>/members", methods=["POST"])
def add_member_to_project(project_id):
    forbidden = _admin_forbidden_response()
    if forbidden:
        return forbidden

    payload = request.get_json(silent=True) or {}
    member_id = payload.get("member_id")
    if not isinstance(member_id, int):
        return jsonify({"error": "member_id (int) is required"}), 400

    result = _assign_member_to_project(member_id, project_id)
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Assignment failed")}), 400

    _audit_write("create", CORE_DB, CORE_MEMBER_PROJECT_MAPPING_TABLE, result.get("mapping_id", -1), "success", f"Assigned member {member_id} to project {project_id}")
    return jsonify(result), 201


@api.route("/projects/<int:project_id>/members/<int:member_id>", methods=["DELETE"])
def remove_member_from_project(project_id, member_id):
    forbidden = _admin_forbidden_response()
    if forbidden:
        return forbidden

    result = _remove_member_from_project(member_id, project_id)
    if not result.get("success"):
        return jsonify({"error": result.get("message", "Removal failed")}), 400

    _audit_write("delete", CORE_DB, CORE_MEMBER_PROJECT_MAPPING_TABLE, member_id, "success", f"Removed member {member_id} from project {project_id}")
    return jsonify(result)


@api.route("/member-portfolio/me", methods=["PUT"])
def update_own_portfolio():
    if getattr(g, "role_name", "staff") == "customer":
        return jsonify({"error": "Customers cannot update portfolio"}), 403

    payload = request.get_json(silent=True) or {}
    allowed_fields = _allowed_self_portfolio_fields()
    updates = {key: value for key, value in payload.items() if key in allowed_fields}

    if not updates:
        return jsonify({"error": f"Allowed fields: {sorted(allowed_fields)}"}), 400

    result = member_manager.update_member(g.current_member_id, updates)
    if not result.get("success"):
        _audit_write("update", CORE_DB, "members", g.current_member_id, "failed", result.get("message", "Update failed"))
        return jsonify({"error": result.get("message", "Update failed")}), 400

    _audit_write("update", CORE_DB, "members", g.current_member_id, "success", f"Self portfolio updated fields: {list(updates.keys())}")
    return jsonify({"message": result.get("message"), "record": result.get("record")})


@api.route("/admin/groups", methods=["GET"])
def admin_list_groups():
    forbidden = _admin_forbidden_response()
    if forbidden:
        return forbidden

    groups = group_manager.list_all_groups()
    detailed = []
    for group in groups:
        group_id = group.get("group_id")
        detailed.append(
            {
                **group,
                "members": group_manager.get_group_members(group_id),
            }
        )
    return jsonify({"records": detailed, "count": len(detailed)})


@api.route("/admin/groups/<int:group_id>/members", methods=["POST"])
def admin_add_member_to_group(group_id):
    forbidden = _admin_forbidden_response()
    if forbidden:
        return forbidden

    payload = request.get_json(silent=True) or {}
    member_id = payload.get("member_id")
    role = payload.get("role", "user")

    if member_id is None:
        return jsonify({"error": "member_id is required"}), 400

    result = group_manager.add_member_to_group(member_id=member_id, group_id=group_id, role=role)
    if not result.get("success"):
        _audit_write("create", CORE_DB, "member_group_mappings", -1, "failed", result.get("message", "Add member failed"))
        return jsonify({"error": result.get("message")}), 400

    _audit_write("create", CORE_DB, "member_group_mappings", result.get("mapping_id", -1), "success", f"Added member {member_id} to group {group_id} as {role}")
    return jsonify(result), 201


@api.route("/admin/groups/<int:group_id>/members/<int:member_id>", methods=["DELETE"])
def admin_remove_member_from_group(group_id, member_id):
    forbidden = _admin_forbidden_response()
    if forbidden:
        return forbidden

    result = group_manager.remove_member_from_group(member_id=member_id, group_id=group_id)
    if not result.get("success"):
        _audit_write("delete", CORE_DB, "member_group_mappings", -1, "failed", result.get("message", "Remove member failed"))
        return jsonify({"error": result.get("message")}), 400

    _audit_write("delete", CORE_DB, "member_group_mappings", member_id, "success", f"Removed member {member_id} from group {group_id}")
    return jsonify(result)


@api.route("/admin/audit/unauthorized-check", methods=["GET"])
def admin_unauthorized_check():
    forbidden = _admin_forbidden_response()
    if forbidden:
        return forbidden

    suspicious = []
    for db_name, table_name in MONITORED_TABLES:
        try:
            live_state = _compute_table_state(db_name, table_name)
            _, expected = _latest_api_state(db_name, table_name)
            if expected is None:
                suspicious.append(
                    {
                        "db": db_name,
                        "table": table_name,
                        "status": "no_api_baseline",
                        "note": "No API baseline found; direct modifications cannot be verified.",
                    }
                )
                continue

            if (
                live_state["row_count"] != expected["row_count"]
                or live_state["key_checksum"] != expected["key_checksum"]
            ):
                suspicious.append(
                    {
                        "db": db_name,
                        "table": table_name,
                        "status": "suspicious_mismatch",
                        "expected": {
                            "row_count": expected["row_count"],
                            "key_checksum": expected["key_checksum"],
                            "last_api_write_at": expected["last_api_write_at"],
                            "last_api_actor": expected["last_api_actor"],
                            "source_marker": expected["source_marker"],
                        },
                        "live": live_state,
                        "note": "Likely direct/unauthorized modification outside session-validated APIs.",
                    }
                )
        except Exception as exc:
            suspicious.append(
                {
                    "db": db_name,
                    "table": table_name,
                    "status": "error",
                    "note": str(exc),
                }
            )

    return jsonify(
        {
            "suspicious_count": len(suspicious),
            "suspicious": suspicious,
            "audit_file": AUDIT_LOG_FILE,
        }
    )


@api.route("/admin/performance/endpoint-stats", methods=["GET"])
def admin_endpoint_stats():
    forbidden = _admin_forbidden_response()
    if forbidden:
        return forbidden

    stats = []
    for endpoint, metric in ENDPOINT_METRICS.items():
        avg_ms = metric["total_ms"] / metric["hits"] if metric["hits"] else 0.0
        stats.append(
            {
                "endpoint": endpoint,
                "hits": metric["hits"],
                "avg_ms": round(avg_ms, 3),
                "max_ms": round(metric["max_ms"], 3),
                "errors": metric["errors"],
                "slow_hits": metric["slow_hits"],
                "last_status": metric["last_status"],
                "last_seen_at": metric["last_seen_at"],
            }
        )

    stats.sort(key=lambda item: item["hits"], reverse=True)
    return jsonify({"count": len(stats), "stats": stats})


@api.route("/admin/performance/reset-metrics", methods=["POST"])
def admin_reset_performance_metrics():
    forbidden = _admin_forbidden_response()
    if forbidden:
        return forbidden

    previous_count = len(ENDPOINT_METRICS)
    ENDPOINT_METRICS.clear()
    return jsonify(
        {
            "message": "Endpoint performance metrics reset",
            "cleared_endpoint_count": previous_count,
        }
    )


@api.route("/admin/performance/insights", methods=["GET"])
def admin_performance_insights():
    forbidden = _admin_forbidden_response()
    if forbidden:
        return forbidden

    stats = []
    for endpoint, metric in ENDPOINT_METRICS.items():
        avg_ms = metric["total_ms"] / metric["hits"] if metric["hits"] else 0.0
        stats.append(
            {
                "endpoint": endpoint,
                "hits": metric["hits"],
                "avg_ms": avg_ms,
                "max_ms": metric["max_ms"],
            }
        )

    most_accessed = sorted(stats, key=lambda item: item["hits"], reverse=True)[:5]
    slowest_average = sorted(stats, key=lambda item: item["avg_ms"], reverse=True)[:5]
    slowest_peak = sorted(stats, key=lambda item: item["max_ms"], reverse=True)[:5]

    return jsonify(
        {
            "most_accessed_endpoints": most_accessed,
            "slowest_avg_endpoints": slowest_average,
            "slowest_peak_endpoints": slowest_peak,
            "note": "Use these insights to prioritize index and query tuning.",
        }
    )


@api.route("/databases/<db_name>/tables/<table_name>/visualize", methods=["GET"])
def visualize_tree(db_name, table_name):
    table, message = db_manager.get_table(db_name, table_name)
    if table is None:
        return jsonify({"error": message}), 404

    dot = table.data.visualize_tree()
    svg_data = dot.pipe(format="svg").decode("utf-8")
    return Response(svg_data, mimetype="image/svg+xml")

 