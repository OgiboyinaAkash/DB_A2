-- SubTask 5: SQL Indexing Performance Benchmark
-- Run this script in MySQL after loading Databases_A1.sql data.
-- Use it in two phases:
--   1) BEFORE index creation (drop indexes first)
--   2) AFTER index creation (create indexes, then re-run)

USE outlet_management;

SET profiling = 1;

-- ------------------------------------------------------------
-- 0) Optional helper to safely drop benchmark indexes
-- ------------------------------------------------------------
DROP PROCEDURE IF EXISTS drop_index_if_exists;
DELIMITER $$
CREATE PROCEDURE drop_index_if_exists(IN idx_name VARCHAR(128), IN tbl_name VARCHAR(128))
BEGIN
  DECLARE idx_count INT DEFAULT 0;
  SELECT COUNT(*) INTO idx_count
  FROM information_schema.statistics
  WHERE table_schema = DATABASE()
    AND table_name = tbl_name
    AND index_name = idx_name;

  IF idx_count > 0 THEN
    SET @sql_stmt = CONCAT('DROP INDEX ', idx_name, ' ON ', tbl_name);
    PREPARE stmt FROM @sql_stmt;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
  END IF;
END $$
DELIMITER ;

-- ------------------------------------------------------------
-- 1) BEFORE phase: remove tuning indexes
-- ------------------------------------------------------------
CALL drop_index_if_exists('ux_product_name', 'Product');
CALL drop_index_if_exists('idx_product_category', 'Product');
CALL drop_index_if_exists('idx_product_category_price', 'Product');
CALL drop_index_if_exists('idx_product_stock_reorder', 'Product');
CALL drop_index_if_exists('ux_category_name', 'Category');
CALL drop_index_if_exists('ux_customer_email', 'Customer');
CALL drop_index_if_exists('idx_customer_contact', 'Customer');
CALL drop_index_if_exists('idx_customer_loyalty', 'Customer');
CALL drop_index_if_exists('idx_sale_customer', 'Sale');
CALL drop_index_if_exists('idx_sale_staff', 'Sale');
CALL drop_index_if_exists('idx_sale_date', 'Sale');
CALL drop_index_if_exists('idx_sale_customer_date', 'Sale');
CALL drop_index_if_exists('idx_sale_staff_date', 'Sale');
CALL drop_index_if_exists('idx_saleitem_sale', 'SaleItem');
CALL drop_index_if_exists('idx_saleitem_product', 'SaleItem');
CALL drop_index_if_exists('idx_saleitem_sale_product', 'SaleItem');
CALL drop_index_if_exists('idx_payment_sale', 'Payment');
CALL drop_index_if_exists('idx_payment_date', 'Payment');
CALL drop_index_if_exists('idx_payment_method_date', 'Payment');
CALL drop_index_if_exists('idx_purchaseorder_supplier_date', 'PurchaseOrder');
CALL drop_index_if_exists('idx_poitem_poid_product', 'PurchaseOrderItem');

-- ------------------------------------------------------------
-- 2) Representative API-like queries (BEFORE)
-- ------------------------------------------------------------
-- Q1: Products by category + sort by price
EXPLAIN SELECT ProductID, Name, Price
FROM Product
WHERE CategoryID = 1
ORDER BY Price DESC;

SELECT ProductID, Name, Price
FROM Product
WHERE CategoryID = 1
ORDER BY Price DESC;

-- Q2: Sales by customer in date range
EXPLAIN SELECT SaleID, CustomerID, StaffID, SaleDate, TotalAmount
FROM Sale
WHERE CustomerID = 1
  AND SaleDate BETWEEN '2025-02-01' AND '2025-06-30'
ORDER BY SaleDate DESC;

SELECT SaleID, CustomerID, StaffID, SaleDate, TotalAmount
FROM Sale
WHERE CustomerID = 1
  AND SaleDate BETWEEN '2025-02-01' AND '2025-06-30'
ORDER BY SaleDate DESC;

-- Q3: Join sale items with product details
EXPLAIN SELECT si.SaleID, si.ProductID, p.Name, si.Quantity, si.UnitPrice
FROM SaleItem si
JOIN Product p ON p.ProductID = si.ProductID
WHERE si.SaleID = 10;

SELECT si.SaleID, si.ProductID, p.Name, si.Quantity, si.UnitPrice
FROM SaleItem si
JOIN Product p ON p.ProductID = si.ProductID
WHERE si.SaleID = 10;

-- Q4: Customer lookup by email
EXPLAIN SELECT CustomerID, Name, ContactNumber, LoyaltyPoints
FROM Customer
WHERE Email = 'rahul.verma@example.com';

SELECT CustomerID, Name, ContactNumber, LoyaltyPoints
FROM Customer
WHERE Email = 'rahul.verma@example.com';

-- Capture raw execution profiles for BEFORE phase
SHOW PROFILES;

-- ------------------------------------------------------------
-- 3) Create indexes (AFTER phase setup)
-- ------------------------------------------------------------
CREATE UNIQUE INDEX ux_product_name ON Product(Name);
CREATE INDEX idx_product_category ON Product(CategoryID);
CREATE INDEX idx_product_category_price ON Product(CategoryID, Price);
CREATE INDEX idx_product_stock_reorder ON Product(StockQuantity, ReorderLevel);

CREATE UNIQUE INDEX ux_category_name ON Category(CategoryName);

CREATE UNIQUE INDEX ux_customer_email ON Customer(Email);
CREATE INDEX idx_customer_contact ON Customer(ContactNumber);
CREATE INDEX idx_customer_loyalty ON Customer(LoyaltyPoints);

CREATE INDEX idx_sale_customer ON Sale(CustomerID);
CREATE INDEX idx_sale_staff ON Sale(StaffID);
CREATE INDEX idx_sale_date ON Sale(SaleDate);
CREATE INDEX idx_sale_customer_date ON Sale(CustomerID, SaleDate);
CREATE INDEX idx_sale_staff_date ON Sale(StaffID, SaleDate);

CREATE INDEX idx_saleitem_sale ON SaleItem(SaleID);
CREATE INDEX idx_saleitem_product ON SaleItem(ProductID);
CREATE INDEX idx_saleitem_sale_product ON SaleItem(SaleID, ProductID);

CREATE INDEX idx_payment_sale ON Payment(SaleID);
CREATE INDEX idx_payment_date ON Payment(PaymentDate);
CREATE INDEX idx_payment_method_date ON Payment(PaymentMethod, PaymentDate);

CREATE INDEX idx_purchaseorder_supplier_date ON PurchaseOrder(SupplierID, OrderDate);
CREATE INDEX idx_poitem_poid_product ON PurchaseOrderItem(POID, ProductID);

-- ------------------------------------------------------------
-- 4) Repeat same queries (AFTER)
-- ------------------------------------------------------------
EXPLAIN SELECT ProductID, Name, Price
FROM Product
WHERE CategoryID = 1
ORDER BY Price DESC;

SELECT ProductID, Name, Price
FROM Product
WHERE CategoryID = 1
ORDER BY Price DESC;

EXPLAIN SELECT SaleID, CustomerID, StaffID, SaleDate, TotalAmount
FROM Sale
WHERE CustomerID = 1
  AND SaleDate BETWEEN '2025-02-01' AND '2025-06-30'
ORDER BY SaleDate DESC;

SELECT SaleID, CustomerID, StaffID, SaleDate, TotalAmount
FROM Sale
WHERE CustomerID = 1
  AND SaleDate BETWEEN '2025-02-01' AND '2025-06-30'
ORDER BY SaleDate DESC;

EXPLAIN SELECT si.SaleID, si.ProductID, p.Name, si.Quantity, si.UnitPrice
FROM SaleItem si
JOIN Product p ON p.ProductID = si.ProductID
WHERE si.SaleID = 10;

SELECT si.SaleID, si.ProductID, p.Name, si.Quantity, si.UnitPrice
FROM SaleItem si
JOIN Product p ON p.ProductID = si.ProductID
WHERE si.SaleID = 10;

EXPLAIN SELECT CustomerID, Name, ContactNumber, LoyaltyPoints
FROM Customer
WHERE Email = 'rahul.verma@example.com';

SELECT CustomerID, Name, ContactNumber, LoyaltyPoints
FROM Customer
WHERE Email = 'rahul.verma@example.com';

SHOW PROFILES;

-- Optional detailed profile for a specific query id:
-- SHOW PROFILE FOR QUERY <query_id>;

DROP PROCEDURE IF EXISTS drop_index_if_exists;
