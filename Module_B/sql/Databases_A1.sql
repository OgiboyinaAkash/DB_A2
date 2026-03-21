drop database if exists outlet_management;
create database outlet_management;
use outlet_management;

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- 1. Table Creation
-- ============================================================

CREATE TABLE Member (
    MemberID INT PRIMARY KEY AUTO_INCREMENT,
    Name VARCHAR(100) NOT NULL,
    Image VARCHAR(255) NOT NULL,
    Age INT NOT NULL,
    Email VARCHAR(150) NOT NULL UNIQUE,
    ContactNumber VARCHAR(15) NOT NULL,
    Role VARCHAR(50) NOT NULL,
    CreatedAt DATETIME NOT NULL
);

CREATE TABLE Customer (
    CustomerID INT PRIMARY KEY AUTO_INCREMENT,
    Name VARCHAR(100) NOT NULL,
    Email VARCHAR(150) UNIQUE,
    ContactNumber VARCHAR(15) NOT NULL,
    LoyaltyPoints INT NOT NULL DEFAULT 0,
    CreatedAt DATETIME NOT NULL
);

CREATE TABLE Staff (
    StaffID INT PRIMARY KEY AUTO_INCREMENT,
    Name VARCHAR(100) NOT NULL,
    Role VARCHAR(50) NOT NULL,
    Salary DECIMAL(10,2) NOT NULL,
    ContactNumber VARCHAR(15) NOT NULL,
    JoinDate DATE NOT NULL,
    MemberID INT,
    FOREIGN KEY (MemberID) REFERENCES Member(MemberID)
        ON DELETE SET NULL
        ON UPDATE CASCADE
);

CREATE TABLE Category (
    CategoryID INT PRIMARY KEY AUTO_INCREMENT,
    CategoryName VARCHAR(100) NOT NULL UNIQUE,
    Description TEXT NOT NULL,
    CreatedAt DATETIME NOT NULL
);

CREATE TABLE Product (
    ProductID INT PRIMARY KEY AUTO_INCREMENT,
    Name VARCHAR(150) NOT NULL,
    Price DECIMAL(10,2) NOT NULL CHECK (Price > 0),
    StockQuantity INT NOT NULL CHECK (StockQuantity >= 0),
    ReorderLevel INT NOT NULL,
    CategoryID INT,
    FOREIGN KEY (CategoryID) REFERENCES Category(CategoryID)
        ON DELETE SET NULL
        ON UPDATE CASCADE
);

CREATE TABLE Supplier (
    SupplierID INT PRIMARY KEY AUTO_INCREMENT,
    Name VARCHAR(100) NOT NULL,
    ContactNumber VARCHAR(15) NOT NULL,
    Email VARCHAR(150) NOT NULL UNIQUE,
    Address VARCHAR(255) NOT NULL
);

CREATE TABLE PurchaseOrder (
    POID INT PRIMARY KEY AUTO_INCREMENT,
    SupplierID INT,
    OrderDate DATE NOT NULL,
    TotalAmount DECIMAL(12,2) NOT NULL CHECK (TotalAmount > 0),
    Status VARCHAR(50) NOT NULL,
    FOREIGN KEY (SupplierID) REFERENCES Supplier(SupplierID)
        ON DELETE SET NULL
        ON UPDATE CASCADE
);

CREATE TABLE PurchaseOrderItem (
    POItemID INT PRIMARY KEY AUTO_INCREMENT,
    POID INT NOT NULL,
    ProductID INT NOT NULL,
    Quantity INT NOT NULL CHECK (Quantity > 0),
    CostPrice DECIMAL(10,2) NOT NULL CHECK (CostPrice > 0),
    FOREIGN KEY (POID) REFERENCES PurchaseOrder(POID)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    FOREIGN KEY (ProductID) REFERENCES Product(ProductID)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);

CREATE TABLE Sale (
    SaleID INT PRIMARY KEY AUTO_INCREMENT,
    CustomerID INT,
    StaffID INT,
    SaleDate DATETIME NOT NULL,
    TotalAmount DECIMAL(12,2) NOT NULL CHECK (TotalAmount >= 0),
    FOREIGN KEY (CustomerID) REFERENCES Customer(CustomerID)
        ON DELETE SET NULL
        ON UPDATE CASCADE,
    FOREIGN KEY (StaffID) REFERENCES Staff(StaffID)
        ON DELETE SET NULL
        ON UPDATE CASCADE
);

CREATE TABLE SaleItem (
    SaleItemID INT PRIMARY KEY AUTO_INCREMENT,
    SaleID INT NOT NULL,
    ProductID INT NOT NULL,
    Quantity INT NOT NULL CHECK (Quantity > 0),
    UnitPrice DECIMAL(10,2) NOT NULL CHECK (UnitPrice > 0),
    FOREIGN KEY (SaleID) REFERENCES Sale(SaleID)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    FOREIGN KEY (ProductID) REFERENCES Product(ProductID)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
);

CREATE TABLE Payment (
    PaymentID INT PRIMARY KEY AUTO_INCREMENT,
    SaleID INT NOT NULL,
    PaymentMethod VARCHAR(50) NOT NULL,
    Amount DECIMAL(12,2) NOT NULL CHECK (Amount > 0),
    PaymentDate DATETIME NOT NULL,
    FOREIGN KEY (SaleID) REFERENCES Sale(SaleID)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

CREATE TABLE Attendance (
    AttendanceID INT PRIMARY KEY AUTO_INCREMENT,
    StaffID INT NOT NULL,
    EntryTime DATETIME NOT NULL,
    ExitTime DATETIME NOT NULL,
    WorkDate DATE NOT NULL,
    CHECK (ExitTime > EntryTime),
    FOREIGN KEY (StaffID) REFERENCES Staff(StaffID)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- ============================================================
-- 2. Data Population
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Member (10 rows)
-- ----------------------------
INSERT INTO Member (Name, Image, Age, Email, ContactNumber, Role, CreatedAt) VALUES
('Aarav Sharma', 'aarav.jpg', 35, 'aarav.sharma@example.com', '9876543210', 'Owner', '2025-01-10 09:00:00'),
('Vivaan Singh', 'vivaan.jpg', 28, 'vivaan.singh@example.com', '9876543211', 'Manager', '2025-01-15 10:30:00'),
('Ananya Patel', 'ananya.jpg', 32, 'ananya.patel@example.com', '9876543212', 'Cashier', '2025-02-01 11:45:00'),
('Ishita Gupta', 'ishita.jpg', 26, 'ishita.gupta@example.com', '9876543213', 'Stock Clerk', '2025-02-10 09:15:00'),
('Rohan Desai', 'rohan.jpg', 40, 'rohan.desai@example.com', '9876543214', 'Accountant', '2025-03-05 14:20:00'),
('Priya Nair', 'priya.jpg', 29, 'priya.nair@example.com', '9876543215', 'Sales Assistant', '2025-03-12 08:30:00'),
('Kabir Malhotra', 'kabir.jpg', 33, 'kabir.malhotra@example.com', '9876543216', 'Security', '2025-04-01 13:00:00'),
('Sanya Kapoor', 'sanya.jpg', 24, 'sanya.kapoor@example.com', '9876543217', 'Cashier', '2025-04-18 12:10:00'),
('Arjun Reddy', 'arjun.jpg', 45, 'arjun.reddy@example.com', '9876543218', 'Manager', '2025-05-02 16:45:00'),
('Neha Joshi', 'neha.jpg', 31, 'neha.joshi@example.com', '9876543219', 'HR', '2025-05-20 10:00:00');

-- ----------------------------
-- Customer (15 rows)
-- ----------------------------
INSERT INTO Customer (Name, Email, ContactNumber, LoyaltyPoints, CreatedAt) VALUES
('Rahul Verma', 'rahul.verma@example.com', '9988776655', 120, '2025-01-05 12:30:00'),
('Sneha Iyer', 'sneha.iyer@example.com', '9988776656', 250, '2025-01-12 15:45:00'),
('Amit Kumar', 'amit.kumar@example.com', '9988776657', 80, '2025-01-20 09:20:00'),
('Pooja Mehta', 'pooja.mehta@example.com', '9988776658', 300, '2025-02-02 14:10:00'),
('Rajesh Khanna', 'rajesh.khanna@example.com', '9988776659', 50, '2025-02-14 11:00:00'),
('Sunita Rao', 'sunita.rao@example.com', '9988776660', 180, '2025-02-25 16:30:00'),
('Vikram Singh', 'vikram.singh@example.com', '9988776661', 90, '2025-03-07 10:45:00'),
('Kavita Sharma', 'kavita.sharma@example.com', '9988776662', 210, '2025-03-19 13:20:00'),
('Deepak Choudhary', 'deepak.c@example.com', '9988776663', 40, '2025-04-01 08:15:00'),
('Anjali Deshpande', 'anjali.d@example.com', '9988776664', 320, '2025-04-10 17:00:00'),
('Suresh Yadav', 'suresh.y@example.com', '9988776665', 60, '2025-04-22 12:00:00'),
('Meera Nair', 'meera.nair@example.com', '9988776666', 150, '2025-05-05 09:30:00'),
('Gaurav Patil', 'gaurav.p@example.com', '9988776667', 75, '2025-05-18 14:45:00'),
('Nidhi Jain', 'nidhi.jain@example.com', '9988776668', 200, '2025-06-01 11:10:00'),
('Ravi Shastri', 'ravi.s@example.com', '9988776669', 95, '2025-06-12 16:20:00');

-- ----------------------------
-- Category (12 rows)
-- ----------------------------
INSERT INTO Category (CategoryName, Description, CreatedAt) VALUES
('Electronics', 'Gadgets, accessories, and electronic items', '2025-01-01 00:00:00'),
('Groceries', 'Daily food and household essentials', '2025-01-01 00:00:00'),
('Clothing', 'Men, women, and kids apparel', '2025-01-01 00:00:00'),
('Stationery', 'Office and school supplies', '2025-01-01 00:00:00'),
('Home & Kitchen', 'Utensils, decor, and kitchenware', '2025-01-01 00:00:00'),
('Personal Care', 'Health, beauty, and hygiene products', '2025-01-01 00:00:00'),
('Sports', 'Equipment, accessories, and sportswear', '2025-01-01 00:00:00'),
('Toys', 'Games and toys for children', '2025-01-01 00:00:00'),
('Books', 'Fiction, non-fiction, educational books', '2025-01-01 00:00:00'),
('Furniture', 'Chairs, tables, shelves', '2025-01-01 00:00:00');

-- ----------------------------
-- Supplier (10 rows)
-- ----------------------------
INSERT INTO Supplier (Name, ContactNumber, Email, Address) VALUES
('TechDistributors Inc.', '1122334455', 'sales@techdist.com', '123 Industrial Area, Mumbai'),
('FreshMart Supplies', '2233445566', 'orders@freshmart.com', '456 Market Street, Delhi'),
('FashionHub Ltd.', '3344556677', 'contact@fashionhub.com', '789 Garment Complex, Bangalore'),
('OfficeNeeds Co.', '4455667788', 'info@officeneeds.com', '101 Business Park, Chennai'),
('HomeComforts', '5566778899', 'support@homecomforts.com', '202 Residency Road, Pune'),
('Wellness World', '6677889900', 'sales@wellnessworld.com', '303 Health Avenue, Hyderabad'),
('SportzGear', '7788990011', 'orders@sportzgear.com', '404 Stadium Road, Kolkata'),
('KidzJoy', '8899001122', 'contact@kidzjoy.com', '505 Toy Street, Ahmedabad'),
('BookWorld Distributors', '9900112233', 'orders@bookworld.com', '606 Library Road, Lucknow'),
('FurniCraft', '9911223344', 'sales@furnicraft.com', '707 Wood Street, Jaipur');

-- ----------------------------
-- Staff (12 rows)
-- ----------------------------
INSERT INTO Staff (Name, Role, Salary, ContactNumber, JoinDate, MemberID) VALUES
('Aarav Sharma', 'Owner', 75000.00, '9876543210', '2025-01-10', 1),
('Vivaan Singh', 'Manager', 50000.00, '9876543211', '2025-01-15', 2),
('Ananya Patel', 'Cashier', 25000.00, '9876543212', '2025-02-01', 3),
('Ishita Gupta', 'Stock Clerk', 22000.00, '9876543213', '2025-02-10', 4),
('Rohan Desai', 'Accountant', 40000.00, '9876543214', '2025-03-05', 5),
('Priya Nair', 'Sales Assistant', 20000.00, '9876543215', '2025-03-12', 6),
('Kabir Malhotra', 'Security', 18000.00, '9876543216', '2025-04-01', 7),
('Sanya Kapoor', 'Cashier', 24000.00, '9876543217', '2025-04-18', 8),
('Arjun Reddy', 'Manager', 52000.00, '9876543218', '2025-05-02', 9),
('Neha Joshi', 'HR', 35000.00, '9876543219', '2025-05-20', 10),
('Manoj Tiwari', 'Cleaner', 15000.00, '9988776601', '2025-06-01', NULL),
('Rekha Bansal', 'Sales Assistant', 19000.00, '9988776602', '2025-06-10', NULL);

-- ----------------------------
-- Product (20 rows)
-- ----------------------------
INSERT INTO Product (Name, Price, StockQuantity, ReorderLevel, CategoryID) VALUES
('Smartphone', 15000.00, 50, 5, 1),
('Laptop', 55000.00, 20, 3, 1),
('Headphones', 2000.00, 100, 10, 1),
('Rice (5kg)', 300.00, 200, 20, 2),
('Wheat Flour (10kg)', 400.00, 150, 15, 2),
('Milk (1L)', 60.00, 300, 30, 2),
('T-Shirt (Men)', 500.00, 80, 10, 3),
('Jeans (Women)', 1200.00, 60, 8, 3),
('Notebook', 50.00, 500, 50, 4),
('Pen Pack (10)', 100.00, 400, 40, 4),
('Non-stick Pan', 800.00, 40, 5, 5),
('Bedsheet', 1500.00, 30, 4, 5),
('Shampoo (200ml)', 180.00, 120, 15, 6),
('Soap (pack of 3)', 90.00, 200, 20, 6),
('Cricket Bat', 2500.00, 25, 3, 7),
('Football', 800.00, 40, 5, 7),
('Lego Set', 1200.00, 35, 4, 8),
('Doll', 600.00, 50, 6, 8),
('Coffee Powder (250g)', 250.00, 80, 10, 2),
('Umbrella', 350.00, 60, 8, 5);

-- ----------------------------
-- PurchaseOrder (15 rows)
-- ----------------------------
INSERT INTO PurchaseOrder (SupplierID, OrderDate, TotalAmount, Status) VALUES
(1, '2025-02-01', 750000.00, 'Completed'),
(2, '2025-02-10', 45000.00, 'Completed'),
(3, '2025-02-15', 60000.00, 'Completed'),
(4, '2025-03-01', 12000.00, 'Completed'),
(5, '2025-03-10', 35000.00, 'Completed'),
(6, '2025-03-20', 18000.00, 'Completed'),
(7, '2025-04-05', 40000.00, 'Shipped'),
(8, '2025-04-12', 25000.00, 'Pending'),
(1, '2025-04-20', 320000.00, 'Completed'),
(2, '2025-05-01', 28000.00, 'Completed'),
(3, '2025-05-10', 50000.00, 'Shipped'),
(4, '2025-05-18', 9000.00, 'Completed'),
(5, '2025-06-01', 22000.00, 'Shipped'),
(6, '2025-06-08', 15000.00, 'Pending'),
(7, '2025-06-15', 35000.00, 'Pending');

-- ----------------------------
-- PurchaseOrderItem (25 rows)
-- ----------------------------
INSERT INTO PurchaseOrderItem (POID, ProductID, Quantity, CostPrice) VALUES
(1, 1, 30, 12000.00), (1, 2, 10, 45000.00), (1, 3, 50, 1500.00),
(2, 4, 100, 250.00), (2, 5, 50, 350.00),
(3, 7, 80, 400.00), (3, 8, 40, 1000.00),
(4, 9, 200, 40.00), (4, 10, 150, 80.00),
(5, 11, 30, 600.00), (5, 12, 20, 1200.00),
(6, 13, 80, 150.00), (6, 14, 150, 70.00),
(7, 15, 15, 2000.00), (7, 16, 30, 600.00),
(8, 17, 20, 1000.00), (8, 18, 30, 500.00),
(9, 1, 20, 11800.00), (9, 2, 5, 44800.00),
(10, 4, 60, 245.00), (10, 19, 40, 200.00),
(11, 7, 50, 390.00), (11, 8, 25, 980.00),
(12, 9, 100, 38.00), (12, 10, 80, 78.00);

-- ----------------------------
-- Sale (20 rows)
-- ----------------------------
INSERT INTO Sale (SaleID, CustomerID, StaffID, SaleDate, TotalAmount) VALUES
(1, 1, 3, '2025-02-05 10:30:00', 17000.00),
(2, 2, 6, '2025-02-12 14:15:00', 670.00),
(3, 3, 8, '2025-02-20 11:45:00', 2900.00),
(4, 4, 3, '2025-03-02 16:00:00', 2650.00),
(5, 5, 6, '2025-03-08 12:30:00', 540.00),
(6, 6, 8, '2025-03-15 09:20:00', 2000.00),
(7, 7, 3, '2025-03-22 18:10:00', 7100.00),
(8, 8, 6, '2025-04-01 13:40:00', 450.00),
(9, 9, 8, '2025-04-09 11:00:00', 3900.00),
(10, 10, 3, '2025-04-18 15:30:00', 9200.00),
(11, 11, 6, '2025-04-25 10:15:00', 600.00),
(12, 12, 8, '2025-05-03 17:45:00', 4100.00),
(13, 13, 3, '2025-05-10 12:00:00', 2700.00),
(14, 14, 6, '2025-05-18 14:30:00', 1300.00),
(15, 15, 8, '2025-05-25 09:50:00', 8200.00),
(16, 1, 3, '2025-06-02 11:20:00', 3450.00), 
(17, 2, 6, '2025-06-09 16:40:00', 1800.00),  
(18, 3, 8, '2025-06-15 10:00:00', 5900.00),  
(19, 4, 3, '2025-06-20 13:10:00', 700.00),   
(20, 5, 6, '2025-06-25 15:55:00', 4500.00);   

-- ----------------------------
-- SaleItem (30 rows)
-- ----------------------------
INSERT INTO SaleItem (SaleID, ProductID, Quantity, UnitPrice) VALUES
(1, 1, 1, 15000.00), (1, 3, 1, 2000.00),
(2, 4, 1, 300.00), (2, 6, 2, 60.00), (2, 19, 1, 250.00),
(3, 7, 2, 500.00), (3, 8, 1, 1200.00), (3, 9, 10, 50.00), (3, 10, 2, 100.00),
(4, 11, 1, 800.00), (4, 12, 1, 1500.00), (4, 20, 1, 350.00),
(5, 13, 2, 180.00), (5, 14, 2, 90.00),
(6, 5, 3, 400.00), (6, 6, 5, 60.00), (6, 19, 2, 250.00),
(7, 15, 1, 2500.00), (7, 16, 2, 800.00), (7, 17, 1, 1200.00), (7, 18, 3, 600.00),
(8, 9, 5, 50.00), (8, 10, 2, 100.00),
(9, 7, 3, 500.00), (9, 8, 2, 1200.00),
(10, 15, 2, 2500.00), (10, 16, 1, 800.00), (10, 17, 1, 1200.00), (10, 18, 2, 600.00), (10, 19, 4, 250.00);

-- ----------------------------
-- Payment (20 rows)
-- ----------------------------
INSERT INTO Payment (SaleID, PaymentMethod, Amount, PaymentDate) VALUES
(1, 'Credit Card', 17000.00, '2025-02-05 10:35:00'),
(2, 'Cash', 670.00, '2025-02-12 14:20:00'),
(3, 'Debit Card', 2900.00, '2025-02-20 11:50:00'),
(4, 'UPI', 2650.00, '2025-03-02 16:05:00'),
(5, 'Cash', 540.00, '2025-03-08 12:35:00'),
(6, 'Credit Card', 2000.00, '2025-03-15 09:25:00'),
(7, 'Cash', 5000.00, '2025-03-22 18:15:00'),
(7, 'UPI', 2100.00, '2025-03-22 18:20:00'),
(8, 'Cash', 450.00, '2025-04-01 13:45:00'),
(9, 'Debit Card', 3900.00, '2025-04-09 11:05:00'),
(10, 'Credit Card', 9200.00, '2025-04-18 15:35:00'),
(11, 'Cash', 600.00, '2025-04-25 10:20:00'),
(12, 'UPI', 4100.00, '2025-05-03 17:50:00'),
(13, 'Cash', 2000.00, '2025-05-10 12:05:00'),
(13, 'Credit Card', 700.00, '2025-05-10 12:10:00'),
(14, 'Cash', 1300.00, '2025-05-18 14:35:00'),
(15, 'Debit Card', 8200.00, '2025-05-25 09:55:00'),
(16, 'UPI', 3450.00, '2025-06-02 11:25:00'),
(17, 'Cash', 1800.00, '2025-06-09 16:45:00'),
(18, 'Credit Card', 5900.00, '2025-06-15 10:05:00');

-- ----------------------------
-- Attendance (25 rows)
-- ----------------------------
INSERT INTO Attendance (StaffID, EntryTime, ExitTime, WorkDate) VALUES
(1, '2025-02-01 09:00:00', '2025-02-01 18:00:00', '2025-02-01'),
(2, '2025-02-01 08:30:00', '2025-02-01 17:30:00', '2025-02-01'),
(3, '2025-02-01 09:15:00', '2025-02-01 18:15:00', '2025-02-01'),
(4, '2025-02-02 08:45:00', '2025-02-02 17:45:00', '2025-02-02'),
(5, '2025-02-02 09:00:00', '2025-02-02 18:00:00', '2025-02-02'),
(6, '2025-02-03 08:30:00', '2025-02-03 17:30:00', '2025-02-03'),
(7, '2025-02-03 09:00:00', '2025-02-03 18:00:00', '2025-02-03'),
(8, '2025-02-04 09:15:00', '2025-02-04 18:15:00', '2025-02-04'),
(9, '2025-02-04 08:45:00', '2025-02-04 17:45:00', '2025-02-04'),
(10, '2025-02-05 09:00:00', '2025-02-05 18:00:00', '2025-02-05'),
(11, '2025-02-05 08:30:00', '2025-02-05 17:30:00', '2025-02-05'),
(12, '2025-02-06 09:00:00', '2025-02-06 18:00:00', '2025-02-06'),
(1, '2025-02-06 09:00:00', '2025-02-06 18:00:00', '2025-02-06'),
(2, '2025-02-07 08:30:00', '2025-02-07 17:30:00', '2025-02-07'),
(3, '2025-02-07 09:15:00', '2025-02-07 18:15:00', '2025-02-07'),
(4, '2025-02-08 08:45:00', '2025-02-08 17:45:00', '2025-02-08'),
(5, '2025-02-08 09:00:00', '2025-02-08 18:00:00', '2025-02-08'),
(6, '2025-02-09 08:30:00', '2025-02-09 17:30:00', '2025-02-09'),
(7, '2025-02-09 09:00:00', '2025-02-09 18:00:00', '2025-02-09'),
(8, '2025-02-10 09:15:00', '2025-02-10 18:15:00', '2025-02-10'),
(9, '2025-02-10 08:45:00', '2025-02-10 17:45:00', '2025-02-10'),
(10, '2025-02-11 09:00:00', '2025-02-11 18:00:00', '2025-02-11'),
(11, '2025-02-11 08:30:00', '2025-02-11 17:30:00', '2025-02-11'),
(12, '2025-02-12 09:00:00', '2025-02-12 18:00:00', '2025-02-12'),
(1, '2025-02-12 09:00:00', '2025-02-12 18:00:00', '2025-02-12');

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- 3. Verification Queries
-- ============================================================

-- Row counts
SELECT 'Member' AS TableName, COUNT(*) FROM Member UNION ALL
SELECT 'Customer', COUNT(*) FROM Customer UNION ALL
SELECT 'Staff', COUNT(*) FROM Staff UNION ALL
SELECT 'Category', COUNT(*) FROM Category UNION ALL
SELECT 'Product', COUNT(*) FROM Product UNION ALL
SELECT 'Supplier', COUNT(*) FROM Supplier UNION ALL
SELECT 'PurchaseOrder', COUNT(*) FROM PurchaseOrder UNION ALL
SELECT 'PurchaseOrderItem', COUNT(*) FROM PurchaseOrderItem UNION ALL
SELECT 'Sale', COUNT(*) FROM Sale UNION ALL
SELECT 'SaleItem', COUNT(*) FROM SaleItem UNION ALL
SELECT 'Payment', COUNT(*) FROM Payment UNION ALL
SELECT 'Attendance', COUNT(*) FROM Attendance;

-- Check foreign key integrity
SELECT 'Sale with invalid CustomerID' AS Referential_Issues FROM Sale 
WHERE CustomerID IS NOT NULL AND CustomerID NOT IN (SELECT CustomerID FROM Customer)
UNION ALL
SELECT 'Sale with invalid StaffID' FROM Sale 
WHERE StaffID IS NOT NULL AND StaffID NOT IN (SELECT StaffID FROM Staff)
UNION ALL
SELECT 'PurchaseOrder with invalid SupplierID' FROM PurchaseOrder 
WHERE SupplierID IS NOT NULL AND SupplierID NOT IN (SELECT SupplierID FROM Supplier)
UNION ALL
SELECT 'Product with invalid CategoryID' FROM Product 
WHERE CategoryID IS NOT NULL AND CategoryID NOT IN (SELECT CategoryID FROM Category)
UNION ALL
SELECT 'Staff with invalid MemberID' FROM Staff 
WHERE MemberID IS NOT NULL AND MemberID NOT IN (SELECT MemberID FROM Member)
UNION ALL
SELECT 'Payment with invalid SaleID' FROM Payment 
WHERE SaleID NOT IN (SELECT SaleID FROM Sale)
UNION ALL
SELECT 'SaleItem with invalid SaleID' FROM SaleItem 
WHERE SaleID NOT IN (SELECT SaleID FROM Sale)
UNION ALL
SELECT 'SaleItem with invalid ProductID' FROM SaleItem 
WHERE ProductID NOT IN (SELECT ProductID FROM Product)
UNION ALL
SELECT 'PurchaseOrderItem with invalid POID' FROM PurchaseOrderItem 
WHERE POID NOT IN (SELECT POID FROM PurchaseOrder)
UNION ALL
SELECT 'PurchaseOrderItem with invalid ProductID' FROM PurchaseOrderItem 
WHERE ProductID NOT IN (SELECT ProductID FROM Product)
UNION ALL
SELECT 'Attendance with invalid StaffID' FROM Attendance 
WHERE StaffID NOT IN (SELECT StaffID FROM Staff);

-- Check logical constraint
SELECT 'Attendance with ExitTime <= EntryTime' AS Logical_Issues 
FROM Attendance WHERE ExitTime <= EntryTime;

-- NOT NULL Constraint Verification
SELECT 'Member - Name NULL' AS Not_Null_Issues, COUNT(*) FROM Member WHERE Name IS NULL UNION ALL
SELECT 'Member - Image NULL', COUNT(*) FROM Member WHERE Image IS NULL UNION ALL
SELECT 'Member - Age NULL', COUNT(*) FROM Member WHERE Age IS NULL UNION ALL
SELECT 'Member - Email NULL', COUNT(*) FROM Member WHERE Email IS NULL UNION ALL
SELECT 'Member - ContactNumber NULL', COUNT(*) FROM Member WHERE ContactNumber IS NULL UNION ALL
SELECT 'Member - Role NULL', COUNT(*) FROM Member WHERE Role IS NULL UNION ALL
SELECT 'Member - CreatedAt NULL', COUNT(*) FROM Member WHERE CreatedAt IS NULL UNION ALL

SELECT 'Customer - Name NULL', COUNT(*) FROM Customer WHERE Name IS NULL UNION ALL
SELECT 'Customer - ContactNumber NULL', COUNT(*) FROM Customer WHERE ContactNumber IS NULL UNION ALL
SELECT 'Customer - LoyaltyPoints NULL', COUNT(*) FROM Customer WHERE LoyaltyPoints IS NULL UNION ALL
SELECT 'Customer - CreatedAt NULL', COUNT(*) FROM Customer WHERE CreatedAt IS NULL UNION ALL

SELECT 'Staff - Name NULL', COUNT(*) FROM Staff WHERE Name IS NULL UNION ALL
SELECT 'Staff - Role NULL', COUNT(*) FROM Staff WHERE Role IS NULL UNION ALL
SELECT 'Staff - Salary NULL', COUNT(*) FROM Staff WHERE Salary IS NULL UNION ALL
SELECT 'Staff - ContactNumber NULL', COUNT(*) FROM Staff WHERE ContactNumber IS NULL UNION ALL
SELECT 'Staff - JoinDate NULL', COUNT(*) FROM Staff WHERE JoinDate IS NULL UNION ALL

SELECT 'Category - CategoryName NULL', COUNT(*) FROM Category WHERE CategoryName IS NULL UNION ALL
SELECT 'Category - Description NULL', COUNT(*) FROM Category WHERE Description IS NULL UNION ALL
SELECT 'Category - CreatedAt NULL', COUNT(*) FROM Category WHERE CreatedAt IS NULL UNION ALL

SELECT 'Product - Name NULL', COUNT(*) FROM Product WHERE Name IS NULL UNION ALL
SELECT 'Product - Price NULL', COUNT(*) FROM Product WHERE Price IS NULL UNION ALL
SELECT 'Product - StockQuantity NULL', COUNT(*) FROM Product WHERE StockQuantity IS NULL UNION ALL
SELECT 'Product - ReorderLevel NULL', COUNT(*) FROM Product WHERE ReorderLevel IS NULL UNION ALL

SELECT 'Supplier - Name NULL', COUNT(*) FROM Supplier WHERE Name IS NULL UNION ALL
SELECT 'Supplier - ContactNumber NULL', COUNT(*) FROM Supplier WHERE ContactNumber IS NULL UNION ALL
SELECT 'Supplier - Email NULL', COUNT(*) FROM Supplier WHERE Email IS NULL UNION ALL
SELECT 'Supplier - Address NULL', COUNT(*) FROM Supplier WHERE Address IS NULL UNION ALL

SELECT 'PurchaseOrder - OrderDate NULL', COUNT(*) FROM PurchaseOrder WHERE OrderDate IS NULL UNION ALL
SELECT 'PurchaseOrder - TotalAmount NULL', COUNT(*) FROM PurchaseOrder WHERE TotalAmount IS NULL UNION ALL
SELECT 'PurchaseOrder - Status NULL', COUNT(*) FROM PurchaseOrder WHERE Status IS NULL UNION ALL

SELECT 'POItem - POID NULL', COUNT(*) FROM PurchaseOrderItem WHERE POID IS NULL UNION ALL
SELECT 'POItem - ProductID NULL', COUNT(*) FROM PurchaseOrderItem WHERE ProductID IS NULL UNION ALL
SELECT 'POItem - Quantity NULL', COUNT(*) FROM PurchaseOrderItem WHERE Quantity IS NULL UNION ALL
SELECT 'POItem - CostPrice NULL', COUNT(*) FROM PurchaseOrderItem WHERE CostPrice IS NULL UNION ALL

SELECT 'Sale - SaleDate NULL', COUNT(*) FROM Sale WHERE SaleDate IS NULL UNION ALL
SELECT 'Sale - TotalAmount NULL', COUNT(*) FROM Sale WHERE TotalAmount IS NULL UNION ALL

SELECT 'SaleItem - SaleID NULL', COUNT(*) FROM SaleItem WHERE SaleID IS NULL UNION ALL
SELECT 'SaleItem - ProductID NULL', COUNT(*) FROM SaleItem WHERE ProductID IS NULL UNION ALL
SELECT 'SaleItem - Quantity NULL', COUNT(*) FROM SaleItem WHERE Quantity IS NULL UNION ALL
SELECT 'SaleItem - UnitPrice NULL', COUNT(*) FROM SaleItem WHERE UnitPrice IS NULL UNION ALL

SELECT 'Payment - SaleID NULL', COUNT(*) FROM Payment WHERE SaleID IS NULL UNION ALL
SELECT 'Payment - PaymentMethod NULL', COUNT(*) FROM Payment WHERE PaymentMethod IS NULL UNION ALL
SELECT 'Payment - Amount NULL', COUNT(*) FROM Payment WHERE Amount IS NULL UNION ALL
SELECT 'Payment - PaymentDate NULL', COUNT(*) FROM Payment WHERE PaymentDate IS NULL UNION ALL

SELECT 'Attendance - StaffID NULL', COUNT(*) FROM Attendance WHERE StaffID IS NULL UNION ALL
SELECT 'Attendance - EntryTime NULL', COUNT(*) FROM Attendance WHERE EntryTime IS NULL UNION ALL
SELECT 'Attendance - ExitTime NULL', COUNT(*) FROM Attendance WHERE ExitTime IS NULL UNION ALL
SELECT 'Attendance - WorkDate NULL', COUNT(*) FROM Attendance WHERE WorkDate IS NULL;

-- ============================================================
-- 5. Indexing for Query Optimization (SubTask 4)
-- Targets WHERE/JOIN/ORDER BY patterns used by APIs and reports.
-- ============================================================

-- Product lookup and filtering
CREATE UNIQUE INDEX ux_product_name ON Product(Name);
CREATE INDEX idx_product_category ON Product(CategoryID);
CREATE INDEX idx_product_category_price ON Product(CategoryID, Price);
CREATE INDEX idx_product_stock_reorder ON Product(StockQuantity, ReorderLevel);

-- Category lookup
CREATE UNIQUE INDEX ux_category_name ON Category(CategoryName);

-- Customer lookup/search patterns
CREATE UNIQUE INDEX ux_customer_email ON Customer(Email);
CREATE INDEX idx_customer_contact ON Customer(ContactNumber);
CREATE INDEX idx_customer_loyalty ON Customer(LoyaltyPoints);

-- Sales filtering, joins, and date sorting
CREATE INDEX idx_sale_customer ON Sale(CustomerID);
CREATE INDEX idx_sale_staff ON Sale(StaffID);
CREATE INDEX idx_sale_date ON Sale(SaleDate);
CREATE INDEX idx_sale_customer_date ON Sale(CustomerID, SaleDate);
CREATE INDEX idx_sale_staff_date ON Sale(StaffID, SaleDate);

-- SaleItem joins and line-item queries
CREATE INDEX idx_saleitem_sale ON SaleItem(SaleID);
CREATE INDEX idx_saleitem_product ON SaleItem(ProductID);
CREATE INDEX idx_saleitem_sale_product ON SaleItem(SaleID, ProductID);

-- Payment transaction retrieval by sale/date
CREATE INDEX idx_payment_sale ON Payment(SaleID);
CREATE INDEX idx_payment_date ON Payment(PaymentDate);
CREATE INDEX idx_payment_method_date ON Payment(PaymentMethod, PaymentDate);

-- Purchase-side optimization for supplier/date analyses
CREATE INDEX idx_purchaseorder_supplier_date ON PurchaseOrder(SupplierID, OrderDate);
CREATE INDEX idx_poitem_poid_product ON PurchaseOrderItem(POID, ProductID);