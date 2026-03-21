"""
Database Initialization and Core Schema Setup
Establishes the B+ Tree-based database with proper core system tables.
Ensures strict separation: core system data vs. project-specific data.
"""

try:
    from .db_manager import DatabaseManager
except ImportError:
    from db_manager import DatabaseManager
from datetime import datetime
import hashlib


class DatabaseInitializer:
    """Initializes and manages the database schema with core system tables."""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.core_db_name = "system_core"
        self.project_db_name = "outlet_management"
    
    def initialize_all(self):
        """Complete database initialization: core system + project-specific."""
        print("[*] Initializing database environment...")
        
        # Step 1: Create core system database
        self.init_core_system()
        
        # Step 2: Create project-specific database
        self.init_project_database()
        
        print("[✓] Database initialization completed successfully!")
        return {
            'core_db': self.core_db_name,
            'project_db': self.project_db_name,
            'status': 'initialized'
        }
    
    def init_core_system(self):
        """Initialize core system database with member, credential, and group tables."""
        print(f"\n[*] Creating core system database: {self.core_db_name}")
        self.db_manager.create_database(self.core_db_name)
        
        # Table 1: Members (core identity)
        member_schema = {
            "member_id": int,
            "username": str,
            "email": str,
            "full_name": str,
            "department": str,
            "status": str,  # 'active', 'inactive', 'suspended'
            "created_at": str,
            "updated_at": str
        }
        self.db_manager.create_table(
            self.core_db_name, 'members', member_schema,
            order=8, search_key='member_id'
        )
        print("  ✓ Created table: members")
        
        # Table 2: Credentials (authentication - separate from members)
        credential_schema = {
            "credential_id": int,
            "member_id": int,
            "password_hash": str,
            "salt": str,
            "last_login": str,
            "login_attempts": int,
            "locked": int,  # 1 = locked, 0 = unlocked
            "created_at": str,
            "updated_at": str
        }
        self.db_manager.create_table(
            self.core_db_name, 'credentials', credential_schema,
            order=8, search_key='credential_id'
        )
        print("  ✓ Created table: credentials")
        
        # Table 3: Groups (logical grouping)
        group_schema = {
            "group_id": int,
            "group_name": str,
            "description": str,
            "created_at": str,
            "updated_at": str
        }
        self.db_manager.create_table(
            self.core_db_name, 'groups', group_schema,
            order=8, search_key='group_id'
        )
        print("  ✓ Created table: groups")
        
        # Table 4: Member-Group Mapping (many-to-many relationship)
        member_group_schema = {
            "mapping_id": int,
            "member_id": int,
            "group_id": int,
            "role_in_group": str,  # 'admin', 'user', 'viewer'
            "assigned_at": str
        }
        self.db_manager.create_table(
            self.core_db_name, 'member_group_mappings', member_group_schema,
            order=8, search_key='mapping_id'
        )
        print("  ✓ Created table: member_group_mappings")
        
        # Table 5: Audit Log (integrity tracking)
        audit_schema = {
            "audit_id": int,
            "action_type": str,  # 'create', 'update', 'delete', 'login'
            "table_name": str,
            "record_id": int,
            "member_id": int,
            "change_details": str,
            "timestamp": str
        }
        self.db_manager.create_table(
            self.core_db_name, 'audit_log', audit_schema,
            order=8, search_key='audit_id'
        )
        print("  ✓ Created table: audit_log")
    
    def init_project_database(self):
        """Initialize project-specific database (outlet management from Databases_A1.sql)."""
        print(f"\n[*] Creating project database: {self.project_db_name}")
        self.db_manager.create_database(self.project_db_name)
        
        # Project Table 1: Products
        product_schema = {
            "product_id": int,
            "name": str,
            "price": float,
            "stock_quantity": int,
            "reorder_level": int,
            "category_id": int,
            "created_at": str
        }
        self.db_manager.create_table(
            self.project_db_name, 'products', product_schema,
            order=8, search_key='product_id'
        )
        print("  ✓ Created table: products")
        
        # Project Table 2: Categories
        category_schema = {
            "category_id": int,
            "category_name": str,
            "description": str,
            "created_at": str
        }
        self.db_manager.create_table(
            self.project_db_name, 'categories', category_schema,
            order=8, search_key='category_id'
        )
        print("  ✓ Created table: categories")
        
        # Project Table 3: Customers
        customer_schema = {
            "customer_id": int,
            "name": str,
            "email": str,
            "contact_number": str,
            "loyalty_points": int,
            "created_at": str
        }
        self.db_manager.create_table(
            self.project_db_name, 'customers', customer_schema,
            order=8, search_key='customer_id'
        )
        print("  ✓ Created table: customers")
        
        # Project Table 4: Sales
        sale_schema = {
            "sale_id": int,
            "customer_id": int,
            "staff_member_id": int,  # References core system member_id
            "sale_date": str,
            "total_amount": float,
            "created_at": str
        }
        self.db_manager.create_table(
            self.project_db_name, 'sales', sale_schema,
            order=8, search_key='sale_id'
        )
        print("  ✓ Created table: sales")
        
        # Project Table 5: Sale Items
        sale_items_schema = {
            "sale_item_id": int,
            "sale_id": int,
            "product_id": int,
            "quantity": int,
            "unit_price": float,
            "created_at": str
        }
        self.db_manager.create_table(
            self.project_db_name, 'sale_items', sale_items_schema,
            order=8, search_key='sale_item_id'
        )
        print("  ✓ Created table: sale_items")
    
    def get_manager(self):
        """Return the database manager instance for further operations."""
        return self.db_manager


# Utility function for password hashing
def hash_password(password, salt=None):
    """Hash password with salt for secure storage."""
    if salt is None:
        salt = hashlib.sha256(str(datetime.now()).encode()).hexdigest()[:16]
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return password_hash, salt


def verify_password(password, stored_hash, salt):
    """Verify password against stored hash."""
    computed_hash, _ = hash_password(password, salt)
    return computed_hash == stored_hash
