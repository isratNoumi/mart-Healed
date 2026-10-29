PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS order_status_history;
DROP TABLE IF EXISTS fulfillments;
DROP TABLE IF EXISTS payment_attempts;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS payment_methods;
DROP TABLE IF EXISTS addresses;
DROP TABLE IF EXISTS user_sessions;
DROP TABLE IF EXISTS cart_items;
DROP TABLE IF EXISTS carts;
DROP TABLE IF EXISTS inventory;
DROP TABLE IF EXISTS regional_prices;
DROP TABLE IF EXISTS product_variants;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS brands;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS stores;
DROP TABLE IF EXISTS regions;
DROP TABLE IF EXISTS users;

-- =========================
-- USERS
-- =========================

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- USER SESSIONS
-- Stores a SHA-256 hash of the session token, never the token itself.
-- =========================

CREATE TABLE user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_user_sessions_user
ON user_sessions(user_id);

-- =========================
-- REGIONS
-- =========================

CREATE TABLE regions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    state TEXT NOT NULL,
    country TEXT NOT NULL DEFAULT 'US',
    zip_start TEXT NOT NULL,
    zip_end TEXT NOT NULL
);

-- =========================
-- STORES
-- =========================

CREATE TABLE stores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region_id INTEGER NOT NULL,
    store_number TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    zip_code TEXT NOT NULL,
    phone TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,

    FOREIGN KEY (region_id) REFERENCES regions(id)
);

-- =========================
-- CATEGORIES
-- =========================

CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id INTEGER,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    description TEXT,

    FOREIGN KEY (parent_id) REFERENCES categories(id)
);

-- =========================
-- BRANDS
-- =========================

CREATE TABLE brands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE
);

-- =========================
-- PRODUCTS
-- =========================

CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    brand_id INTEGER NOT NULL,

    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,

    description TEXT,
    short_description TEXT,

    model_number TEXT,
    rating REAL DEFAULT 0,
    review_count INTEGER DEFAULT 0,

    image_url TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (brand_id) REFERENCES brands(id)
);

-- =========================
-- PRODUCT VARIANTS
-- =========================

CREATE TABLE product_variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,

    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,

    size TEXT,
    color TEXT,
    voltage TEXT,

    is_default INTEGER NOT NULL DEFAULT 0,

    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- =========================
-- REGIONAL PRICES
-- =========================

CREATE TABLE regional_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    product_id INTEGER NOT NULL,
    region_id INTEGER NOT NULL,

    price REAL NOT NULL,
    sale_price REAL,

    currency TEXT NOT NULL DEFAULT 'USD',

    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(product_id, region_id),

    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (region_id) REFERENCES regions(id)
);

-- =========================
-- INVENTORY
-- =========================

CREATE TABLE inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    product_id INTEGER NOT NULL,
    store_id INTEGER NOT NULL,

    quantity INTEGER NOT NULL DEFAULT 0,
    reserved_quantity INTEGER NOT NULL DEFAULT 0,

    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(product_id, store_id),

    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (store_id) REFERENCES stores(id),

    CHECK(quantity >= 0),
    CHECK(reserved_quantity >= 0),
    CHECK(reserved_quantity <= quantity)
);

-- =========================
-- CARTS
-- =========================

CREATE TABLE carts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER,
    session_id TEXT,

    status TEXT NOT NULL DEFAULT 'active',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id),

    CHECK (
        user_id IS NOT NULL
        OR session_id IS NOT NULL
    )
);

-- =========================
-- CART ITEMS
-- =========================

CREATE TABLE cart_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    cart_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    variant_id INTEGER,

    quantity INTEGER NOT NULL DEFAULT 1,

    unit_price REAL NOT NULL,

    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(cart_id, product_id, variant_id),

    FOREIGN KEY (cart_id) REFERENCES carts(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (variant_id) REFERENCES product_variants(id),

    CHECK(quantity > 0),
    CHECK(unit_price >= 0)
);

-- =========================================================
-- ADDRESSES
-- =========================================================

CREATE TABLE IF NOT EXISTS addresses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER NOT NULL,

    type TEXT NOT NULL DEFAULT 'shipping'
        CHECK (type IN ('shipping', 'billing', 'both')),

    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,

    address_line1 TEXT NOT NULL,
    address_line2 TEXT,

    city TEXT NOT NULL,
    state TEXT NOT NULL,
    zip_code TEXT NOT NULL,

    phone TEXT,

    is_default INTEGER NOT NULL DEFAULT 0
        CHECK (is_default IN (0, 1)),

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Hidden instead of deleted so past orders keep their address.
    deleted_at DATETIME,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_addresses_user
ON addresses(user_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_addresses_one_default
ON addresses(user_id)
WHERE is_default = 1 AND deleted_at IS NULL;


-- =========================================================
-- PAYMENT METHODS
-- Never store full card number or CVV.
-- =========================================================

CREATE TABLE IF NOT EXISTS payment_methods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER NOT NULL,

    type TEXT NOT NULL DEFAULT 'card'
        CHECK (type IN ('card')),

    card_brand TEXT NOT NULL,

    last4 TEXT NOT NULL
        CHECK (length(last4) = 4),

    expiry_month INTEGER NOT NULL
        CHECK (expiry_month BETWEEN 1 AND 12),

    expiry_year INTEGER NOT NULL,

    billing_address_id INTEGER,

    is_default INTEGER NOT NULL DEFAULT 0
        CHECK (is_default IN (0, 1)),

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (billing_address_id)
        REFERENCES addresses(id)
        ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_payment_methods_user
ON payment_methods(user_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_payment_methods_one_default
ON payment_methods(user_id)
WHERE is_default = 1;


-- =========================================================
-- ORDERS
-- =========================================================

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER NOT NULL,

    order_number TEXT NOT NULL UNIQUE,

    status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (
            status IN (
                'PENDING',
                'CONFIRMED',
                'PROCESSING',
                'SHIPPED',
                'DELIVERED',
                'CANCELLED'
            )
        ),

    payment_status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (
            payment_status IN (
                'PENDING',
                'PROCESSING',
                'PAID',
                'FAILED',
                'DECLINED',
                'REFUNDED'
            )
        ),

    fulfillment_status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (
            fulfillment_status IN (
                'PENDING',
                'PROCESSING',
                'READY_FOR_PICKUP',
                'SHIPPED',
                'DELIVERED',
                'CANCELLED'
            )
        ),

    shipping_address_id INTEGER,
    billing_address_id INTEGER,

    subtotal REAL NOT NULL
        CHECK (subtotal >= 0),

    discount REAL NOT NULL DEFAULT 0
        CHECK (discount >= 0),

    shipping_cost REAL NOT NULL DEFAULT 0
        CHECK (shipping_cost >= 0),

    tax REAL NOT NULL DEFAULT 0
        CHECK (tax >= 0),

    total REAL NOT NULL
        CHECK (total >= 0),

    currency TEXT NOT NULL DEFAULT 'USD',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(id),

    FOREIGN KEY (shipping_address_id)
        REFERENCES addresses(id)
        ON DELETE SET NULL,

    FOREIGN KEY (billing_address_id)
        REFERENCES addresses(id)
        ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_user
ON orders(user_id);

CREATE INDEX IF NOT EXISTS idx_orders_status
ON orders(status);

CREATE INDEX IF NOT EXISTS idx_orders_created
ON orders(created_at);


-- =========================================================
-- ORDER ITEMS
--
-- Product name and SKU are copied here intentionally.
-- This preserves the historical order if the product changes.
-- =========================================================

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    order_id INTEGER NOT NULL,

    product_id INTEGER NOT NULL,
    variant_id INTEGER,

    product_name TEXT NOT NULL,
    sku TEXT NOT NULL,

    quantity INTEGER NOT NULL
        CHECK (quantity > 0),

    unit_price REAL NOT NULL
        CHECK (unit_price >= 0),

    subtotal REAL NOT NULL
        CHECK (subtotal >= 0),

    FOREIGN KEY (order_id)
        REFERENCES orders(id)
        ON DELETE CASCADE,

    FOREIGN KEY (product_id)
        REFERENCES products(id),

    FOREIGN KEY (variant_id)
        REFERENCES product_variants(id)
);

CREATE INDEX IF NOT EXISTS idx_order_items_order
ON order_items(order_id);


-- =========================================================
-- PAYMENTS
-- =========================================================

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    order_id INTEGER NOT NULL,

    payment_method_id INTEGER,

    -- Copied from the card so the receipt survives the saved card being removed.
    card_brand TEXT,
    card_last4 TEXT,

    transaction_id TEXT UNIQUE,

    amount REAL NOT NULL
        CHECK (amount >= 0),

    currency TEXT NOT NULL DEFAULT 'USD',

    provider TEXT NOT NULL DEFAULT 'MOCK_GATEWAY',

    status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (
            status IN (
                'PENDING',
                'PROCESSING',
                'SUCCEEDED',
                'FAILED',
                'DECLINED',
                'CANCELLED'
            )
        ),

    failure_code TEXT,
    failure_message TEXT,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (order_id)
        REFERENCES orders(id)
        ON DELETE CASCADE,

    FOREIGN KEY (payment_method_id)
        REFERENCES payment_methods(id)
        ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_payments_order
ON payments(order_id);


-- =========================================================
-- PAYMENT ATTEMPTS
--
-- One payment can have multiple attempts.
-- Example:
--
-- Attempt 1 -> DECLINED
-- Attempt 2 -> SUCCEEDED
-- =========================================================

CREATE TABLE IF NOT EXISTS payment_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    payment_id INTEGER NOT NULL,

    attempt_number INTEGER NOT NULL
        CHECK (attempt_number > 0),

    payment_method_id INTEGER,

    amount REAL NOT NULL
        CHECK (amount >= 0),

    status TEXT NOT NULL
        CHECK (
            status IN (
                'PENDING',
                'PROCESSING',
                'SUCCEEDED',
                'FAILED',
                'DECLINED',
                'TIMEOUT'
            )
        ),

    transaction_id TEXT,

    failure_code TEXT,
    failure_message TEXT,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (payment_id)
        REFERENCES payments(id)
        ON DELETE CASCADE,

    FOREIGN KEY (payment_method_id)
        REFERENCES payment_methods(id)
        ON DELETE SET NULL,

    UNIQUE(payment_id, attempt_number)
);

CREATE INDEX IF NOT EXISTS idx_payment_attempts_payment
ON payment_attempts(payment_id);


-- =========================================================
-- FULFILLMENTS
-- =========================================================

CREATE TABLE IF NOT EXISTS fulfillments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    order_id INTEGER NOT NULL,

    type TEXT NOT NULL
        CHECK (
            type IN (
                'SHIP_TO_HOME',
                'STORE_PICKUP',
                'DELIVERY'
            )
        ),

    store_id INTEGER,

    status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (
            status IN (
                'PENDING',
                'PROCESSING',
                'READY_FOR_PICKUP',
                'SHIPPED',
                'DELIVERED',
                'CANCELLED'
            )
        ),

    estimated_date DATE,

    tracking_number TEXT,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (order_id)
        REFERENCES orders(id)
        ON DELETE CASCADE,

    FOREIGN KEY (store_id)
        REFERENCES stores(id)
        ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_fulfillments_order
ON fulfillments(order_id);


-- =========================================================
-- ORDER STATUS HISTORY
-- =========================================================

CREATE TABLE IF NOT EXISTS order_status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    order_id INTEGER NOT NULL,

    status TEXT NOT NULL,

    note TEXT,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (order_id)
        REFERENCES orders(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_order_status_history_order
ON order_status_history(order_id);

CREATE INDEX IF NOT EXISTS idx_order_status_history_created
ON order_status_history(created_at);

-- =========================
-- INDEXES
-- =========================

CREATE INDEX idx_products_category
ON products(category_id);

CREATE INDEX idx_products_brand
ON products(brand_id);

CREATE INDEX idx_products_active
ON products(is_active);

CREATE INDEX idx_regional_prices_product_region
ON regional_prices(product_id, region_id);

CREATE INDEX idx_inventory_product_store
ON inventory(product_id, store_id);

CREATE INDEX idx_carts_user
ON carts(user_id);

CREATE INDEX idx_carts_session
ON carts(session_id);

CREATE INDEX idx_cart_items_cart
ON cart_items(cart_id);

-- =========================
-- USERS
-- =========================

-- Passwords are set by app.init_db from BUILDMART_DEMO_PASSWORD in .env.
INSERT INTO users
(first_name, last_name, email)
VALUES
('John', 'Carter', 'john.carter@example.com'),
('Sarah', 'Miller', 'sarah.miller@example.com');

-- =========================
-- REGIONS
-- =========================

INSERT INTO regions
(name, state, country, zip_start, zip_end)
VALUES
('Houston Metro', 'TX', 'US', '77000', '77999'),
('Atlanta Metro', 'GA', 'US', '30000', '39999'),
('Dallas Metro', 'TX', 'US', '75000', '75999'),
('Phoenix Metro', 'AZ', 'US', '85000', '86999');

-- =========================
-- STORES
-- =========================

INSERT INTO stores
(region_id, store_number, name, address, city, state, zip_code, phone)
VALUES
(1, '1201', 'BuildMart Houston Central',
 '1234 Main Street', 'Houston', 'TX', '77002', '713-555-1201'),

(1, '1202', 'BuildMart Houston West',
 '8450 Westheimer Road', 'Houston', 'TX', '77063', '713-555-1202'),

(2, '2101', 'BuildMart Atlanta North',
 '4500 Peachtree Road', 'Atlanta', 'GA', '30319', '404-555-2101'),

(3, '3101', 'BuildMart Dallas North',
 '7200 Preston Road', 'Dallas', 'TX', '75225', '214-555-3101'),

(4, '4101', 'BuildMart Phoenix Central',
 '3000 Camelback Road', 'Phoenix', 'AZ', '85016', '602-555-4101');

-- =========================
-- CATEGORIES
-- =========================

INSERT INTO categories
(name, slug, description)
VALUES
('Power Tools', 'power-tools', 'Cordless and corded power tools'),
('Hand Tools', 'hand-tools', 'Professional and household hand tools'),
('Hardware', 'hardware', 'Fasteners, anchors and hardware'),
('Electrical', 'electrical', 'Electrical supplies and accessories'),
('Plumbing', 'plumbing', 'Plumbing tools and supplies'),
('Paint', 'paint', 'Interior and exterior paint supplies'),
('Lawn & Garden', 'lawn-garden', 'Outdoor lawn and garden products'),
('Outdoor Living', 'outdoor-living', 'Patio and outdoor products'),
('Storage & Organization', 'storage-organization', 'Storage solutions for home and garage'),
('Lighting', 'lighting', 'Indoor and outdoor lighting');

-- =========================
-- BRANDS
-- =========================

INSERT INTO brands (name, slug)
VALUES
('DeWalt', 'dewalt'),
('Milwaukee', 'milwaukee'),
('Makita', 'makita'),
('Ryobi', 'ryobi'),
('Stanley', 'stanley'),
('Klein Tools', 'klein-tools'),
('Everbilt', 'everbilt'),
('Husky', 'husky'),
('Philips', 'philips'),
('Behr', 'behr');

-- =========================
-- PRODUCTS
-- =========================

INSERT INTO products
(category_id, brand_id, sku, name, slug,
 description, short_description, model_number,
 rating, review_count, image_url)
VALUES

(1, 1, 'DW-DCD791D2',
 'DeWalt 20V MAX Cordless Drill Kit',
 'dewalt-20v-max-cordless-drill-kit',
 'Compact cordless drill with two-speed transmission, LED light and two 20V batteries.',
 '20V cordless drill with two batteries and charger.',
 'DCD791D2',
 4.8, 1248,
 '/images/products/DeWalt 20V MAX Cordless Drill Kit.jpg'),

(1, 2, 'MW-M18DRILL',
 'Milwaukee M18 1/2 in. Cordless Drill',
 'milwaukee-m18-cordless-drill',
 'Powerful M18 cordless drill designed for demanding construction applications.',
 'M18 brushless cordless drill.',
 '2804-20',
 4.7, 923,
 '/images/products/Milwaukee M18  Cordless Drill.jpg'),

(1, 3, 'MK-XFD13',
 'Makita 18V LXT Brushless Drill',
 'makita-18v-lxt-brushless-drill',
 'Brushless cordless drill with variable speed and compact design.',
 '18V brushless cordless drill.',
 'XFD13T',
 4.6, 745,
 '/images/products/Makita 18V LXT Brushless Drill.jpg'),

(2, 5, 'ST-FMHT82545',
 'Stanley 25 ft. PowerLock Tape Measure',
 'stanley-25ft-powerlock-tape-measure',
 'Durable 25-foot tape measure with locking mechanism.',
 '25 ft professional tape measure.',
 'FMHT82545',
 4.7, 1850,
 '/images/products/Stanley 25 ft. PowerLock Tape Measure.jpg'),

(2, 8, 'HS-65PC',
 'Husky 65-Piece Home Tool Set',
 'husky-65-piece-home-tool-set',
 'Complete household tool kit with sockets, ratchets, screwdrivers and pliers.',
 '65-piece household tool set.',
 'H65MTS',
 4.8, 2150,
 '/images/products/Husky 65-Piece Home Tool Set.jpg'),

(2, 6, 'KT-ET920',
 'Klein Tools 9-in. High-Leverage Pliers',
 'klein-tools-high-leverage-pliers',
 'Professional-grade high leverage diagonal cutting pliers.',
 'Professional high-leverage pliers.',
 'D213-9NE',
 4.9, 632,
 '/images/products/Klein Tools 9-in. High-Leverage Pliers.jpg'),

(3, 7, 'EV-SCREW100',
 'Everbilt #8 x 1-1/4 in. Wood Screws 100-Pack',
 'everbilt-wood-screws-100-pack',
 'Multi-purpose wood screws for general construction and home projects.',
 '100-pack wood screws.',
 '804102',
 4.5, 420,
 '/images/products/Wood Screws 100-Pack.jpg'),

(4, 6, 'KT-WIRECUT',
 'Klein Tools Wire Stripper and Cutter',
 'klein-tools-wire-stripper-cutter',
 'Multi-purpose wire stripper and cutter for electrical projects.',
 'Professional wire stripper and cutter.',
 '11055',
 4.8, 510,
 '/images/products/Klein Tools Wire Stripper and Cutter.jpg'),

(5, 7, 'EV-PVC34',
 'Everbilt 3/4 in. PVC Coupling',
 'everbilt-pvc-coupling',
 'PVC coupling for connecting compatible plumbing pipe.',
 '3/4 in. PVC coupling.',
 'PVC-034',
 4.4, 190,
 '/images/products/Everbilt  PVC Coupling.jpg'),

(6, 10, 'BEH-WHITE1G',
 'BEHR Premium Plus Interior Paint',
 'behr-premium-plus-interior-paint',
 'Interior wall paint with durable finish and excellent coverage.',
 'Premium interior wall paint.',
 'PP-WHITE',
 4.6, 1180,
 '/images/products/BEHR Premium Plus Interior Paint.jpg'),

(7, 4, 'RY-TRIMMER40',
 'RYOBI 40V Cordless String Trimmer',
 'ryobi-40v-cordless-string-trimmer',
 'Battery-powered string trimmer for residential lawn maintenance.',
 '40V cordless string trimmer.',
 'RY402110',
 4.5, 690,
 '/images/products/RYOBI 40V Cordless String Trimmer.jpg'),

(8, 4, 'RY-PATIOSET',
 'RYOBI Outdoor Folding Utility Cart',
 'ryobi-outdoor-folding-utility-cart',
 'Heavy-duty outdoor utility cart for gardening and household projects.',
 'Outdoor folding utility cart.',
 'P2830',
 4.3, 275,
 '/images/products/RYOBI Outdoor Folding Utility Cart.jpg'),

(9, 8, 'HS-GARAGE72',
 'Husky 72 in. Heavy-Duty Workbench',
 'husky-72-heavy-duty-workbench',
 'Heavy-duty garage workbench with storage and steel construction.',
 '72-inch professional workbench.',
 'HOTC5623',
 4.8, 850,
 '/images/products/Husky 72 in. Heavy-Duty Workbench.jpg'),

(10, 9, 'PH-LED60',
 'Philips 60W Equivalent LED Bulb 4-Pack',
 'philips-led-bulb-4-pack',
 'Energy-efficient LED bulbs for everyday indoor lighting.',
 '60W equivalent LED bulbs.',
 'LED60-4PK',
 4.7, 970,
 '/images/products/Philips 60W Equivalent LED Bulb 4-Pack.jpg');

-- =========================
-- PRODUCT VARIANTS
-- =========================

INSERT INTO product_variants
(product_id, sku, name, size, color, voltage, is_default)
VALUES
(1, 'DW-DCD791D2-KIT', '2-Battery Kit', NULL, 'Black/Yellow', '20V', 1),
(1, 'DW-DCD791D2-TOOL', 'Tool Only', NULL, 'Black/Yellow', '20V', 0),

(2, 'MW-M18DRILL-TOOL', 'Tool Only', NULL, 'Red', '18V', 1),

(3, 'MK-XFD13-KIT', '2-Battery Kit', NULL, 'Teal', '18V', 1),

(4, 'ST-FMHT82545-25', '25 ft', '25 ft', 'Black/Yellow', NULL, 1),

(5, 'HS-65PC-SET', '65-Piece Set', '65-Piece', 'Black', NULL, 1),

(10, 'BEH-WHITE1G-GAL', '1 Gallon', '1 Gallon', 'White', NULL, 1),

(11, 'RY-TRIMMER40-TOOL', 'Tool Only', NULL, 'Green', '40V', 1);

-- =========================
-- REGIONAL PRICES
-- =========================

INSERT INTO regional_prices
(product_id, region_id, price, sale_price)
VALUES

-- DeWalt
(1, 1, 179.00, 159.00),
(1, 2, 184.00, 164.00),
(1, 3, 179.00, 159.00),
(1, 4, 189.00, 169.00),

-- Milwaukee
(2, 1, 199.00, NULL),
(2, 2, 209.00, 199.00),
(2, 3, 204.00, NULL),
(2, 4, 214.00, NULL),

-- Makita
(3, 1, 229.00, 209.00),
(3, 2, 235.00, NULL),
(3, 3, 229.00, 219.00),
(3, 4, 239.00, NULL),

-- Stanley
(4, 1, 19.97, NULL),
(4, 2, 21.97, NULL),
(4, 3, 19.97, NULL),
(4, 4, 22.97, NULL),

-- Husky Tool Set
(5, 1, 89.00, 79.00),
(5, 2, 94.00, 84.00),
(5, 3, 89.00, NULL),
(5, 4, 99.00, 89.00),

-- Klein Pliers
(6, 1, 34.97, NULL),
(6, 2, 36.97, NULL),
(6, 3, 34.97, 32.97),
(6, 4, 37.97, NULL),

-- Screws
(7, 1, 8.97, NULL),
(7, 2, 9.47, NULL),
(7, 3, 8.97, NULL),
(7, 4, 9.97, NULL),

-- Wire stripper
(8, 1, 24.97, NULL),
(8, 2, 26.97, NULL),
(8, 3, 24.97, NULL),
(8, 4, 27.97, NULL),

-- PVC
(9, 1, 2.47, NULL),
(9, 2, 2.67, NULL),
(9, 3, 2.47, NULL),
(9, 4, 2.87, NULL),

-- Paint
(10, 1, 39.98, 34.98),
(10, 2, 41.98, NULL),
(10, 3, 39.98, 36.98),
(10, 4, 42.98, NULL),

-- Trimmer
(11, 1, 199.00, 179.00),
(11, 2, 209.00, 189.00),
(11, 3, 199.00, NULL),
(11, 4, 219.00, 199.00),

-- Cart
(12, 1, 129.00, NULL),
(12, 2, 139.00, 129.00),
(12, 3, 129.00, NULL),
(12, 4, 149.00, 139.00),

-- Workbench
(13, 1, 549.00, 499.00),
(13, 2, 569.00, NULL),
(13, 3, 549.00, 519.00),
(13, 4, 589.00, 539.00),

-- LED
(14, 1, 14.97, 11.97),
(14, 2, 15.97, NULL),
(14, 3, 14.97, 12.97),
(14, 4, 16.97, NULL);

-- =========================
-- INVENTORY
-- =========================

INSERT INTO inventory
(product_id, store_id, quantity, reserved_quantity)
VALUES

-- Houston Central
(1, 1, 24, 2),
(2, 1, 8, 1),
(3, 1, 14, 0),
(4, 1, 52, 3),
(5, 1, 12, 1),
(6, 1, 18, 0),
(7, 1, 75, 5),
(8, 1, 20, 0),
(9, 1, 100, 4),
(10, 1, 16, 2),
(11, 1, 9, 1),
(12, 1, 4, 0),
(13, 1, 3, 0),
(14, 1, 65, 5),

-- Houston West
(1, 2, 7, 0),
(2, 2, 16, 2),
(3, 2, 5, 0),
(4, 2, 38, 1),
(5, 2, 6, 0),
(6, 2, 11, 1),
(7, 2, 90, 10),
(8, 2, 14, 0),
(9, 2, 60, 3),
(10, 2, 10, 0),
(11, 2, 3, 0),
(12, 2, 8, 1),
(13, 2, 1, 0),
(14, 2, 48, 4),

-- Atlanta
(1, 3, 18, 1),
(2, 3, 4, 0),
(3, 3, 21, 2),
(4, 3, 60, 5),
(5, 3, 10, 0),
(6, 3, 7, 0),
(7, 3, 110, 5),
(8, 3, 22, 0),
(9, 3, 75, 5),
(10, 3, 20, 1),
(11, 3, 14, 0),
(12, 3, 6, 0),
(13, 3, 2, 0),
(14, 3, 72, 4),

-- Dallas
(1, 4, 11, 0),
(2, 4, 13, 1),
(3, 4, 8, 0),
(4, 4, 45, 2),
(5, 4, 18, 1),
(6, 4, 13, 0),
(7, 4, 80, 4),
(8, 4, 19, 0),
(9, 4, 95, 3),
(10, 4, 8, 0),
(11, 4, 7, 0),
(12, 4, 5, 0),
(13, 4, 2, 0),
(14, 4, 55, 3),

-- Phoenix
(1, 5, 3, 0),
(2, 5, 6, 0),
(3, 5, 2, 0),
(4, 5, 29, 1),
(5, 5, 5, 0),
(6, 5, 4, 0),
(7, 5, 50, 2),
(8, 5, 8, 0),
(9, 5, 42, 2),
(10, 5, 6, 0),
(11, 5, 2, 0),
(12, 5, 1, 0),
(13, 5, 0, 0),
(14, 5, 31, 2);

-- =========================
-- SAMPLE CART
-- =========================

INSERT INTO carts (user_id, status)
VALUES (1, 'active');

INSERT INTO cart_items
(cart_id, product_id, variant_id, quantity, unit_price)
VALUES
(1, 1, 1, 1, 159.00);



INSERT INTO addresses (
    user_id, type, first_name, last_name,
    address_line1, address_line2,
    city, state, zip_code, phone, is_default
) VALUES
(
    1, 'both', 'John', 'Carter',
    '1847 Westheimer Road', 'Apt 204',
    'Houston', 'TX', '77098', '713-555-0142', 1
),
(
    1, 'shipping', 'John', 'Carter',
    '5200 Buffalo Speedway', NULL,
    'Houston', 'TX', '77005', '713-555-0167', 0
),
(
    2, 'both', 'Sarah', 'Miller',
    '742 Peachtree Street NE', 'Suite 302',
    'Atlanta', 'GA', '30308', '404-555-0188', 1
),
(
    2, 'shipping', 'Sarah', 'Miller',
    '1250 Piedmont Avenue NE', NULL,
    'Atlanta', 'GA', '30309', '404-555-0199', 0
);

-- =========================================================
-- PAYMENT METHODS
-- Fake/safe payment data only.
-- Never store full card number or CVV.
--
-- Address IDs created above:
-- 1 = John's default address
-- 2 = John's second address
-- 3 = Sarah's default address
-- 4 = Sarah's second address
-- =========================================================

INSERT INTO payment_methods (
    user_id, type, card_brand, last4,
    expiry_month, expiry_year,
    billing_address_id, is_default
) VALUES
(
    1, 'card', 'VISA', '4242',
    12, 2028, 1, 1
),
(
    1, 'card', 'MASTERCARD', '1111',
    11, 2027, 1, 0
),
(
    2, 'card', 'VISA', '5555',
    8, 2029, 3, 1
);

-- =========================================================
-- HISTORICAL ORDER
-- John Carter
--
-- Product 4:
-- Stanley 25 ft. PowerLock Tape Measure
-- Variant 5:
-- ST-FMHT82545-25
--
-- Product 14:
-- Philips 60W Equivalent LED Bulb 4-Pack
-- No variant
-- =========================================================

INSERT INTO orders (
    user_id,
    order_number,
    status,
    payment_status,
    fulfillment_status,
    shipping_address_id,
    billing_address_id,
    subtotal,
    discount,
    shipping_cost,
    tax,
    total,
    currency
) VALUES (
    1,
    'BM-20260920-10001',
    'DELIVERED',
    'PAID',
    'DELIVERED',
    1,
    1,
    49.91,
    5.00,
    9.99,
    4.39,
    59.29,
    'USD'
);

-- =========================================================
-- HISTORICAL ORDER ITEMS
--
-- Order ID = 1
-- =========================================================

INSERT INTO order_items (
    order_id,
    product_id,
    variant_id,
    product_name,
    sku,
    quantity,
    unit_price,
    subtotal
) VALUES
(
    1,
    4,
    5,
    'Stanley 25 ft. PowerLock Tape Measure',
    'ST-FMHT82545-25',
    1,
    19.97,
    19.97
),
(
    1,
    14,
    NULL,
    'Philips 60W Equivalent LED Bulb 4-Pack',
    'PH-LED60',
    2,
    14.97,
    29.94
);

-- =========================================================
-- HISTORICAL PAYMENT
--
-- Payment Method ID:
-- 1 = John's VISA ending 4242
-- =========================================================

INSERT INTO payments (
    order_id,
    payment_method_id,
    card_brand,
    card_last4,
    transaction_id,
    amount,
    currency,
    provider,
    status,
    failure_code,
    failure_message
) VALUES (
    1,
    1,
    'VISA',
    '4242',
    'MOCK-TXN-10001',
    59.29,
    'USD',
    'MOCK_GATEWAY',
    'SUCCEEDED',
    NULL,
    NULL
);

-- =========================================================
-- HISTORICAL PAYMENT ATTEMPT
-- =========================================================

INSERT INTO payment_attempts (
    payment_id,
    attempt_number,
    payment_method_id,
    amount,
    status,
    transaction_id,
    failure_code,
    failure_message
) VALUES (
    1,
    1,
    1,
    59.29,
    'SUCCEEDED',
    'MOCK-TXN-10001',
    NULL,
    NULL
);

-- =========================================================
-- HISTORICAL FULFILLMENT
--
-- Store ID 1 = BuildMart Houston Central
-- =========================================================

INSERT INTO fulfillments (
    order_id,
    type,
    store_id,
    status,
    estimated_date,
    tracking_number
) VALUES (
    1,
    'SHIP_TO_HOME',
    1,
    'DELIVERED',
    '2026-09-24',
    'BMTRK100001'
);

-- =========================================================
-- HISTORICAL ORDER STATUS HISTORY
-- =========================================================

INSERT INTO order_status_history (
    order_id,
    status,
    note
) VALUES
(
    1,
    'CONFIRMED',
    'Payment successfully processed and order confirmed.'
),
(
    1,
    'PROCESSING',
    'Order sent to fulfillment.'
),
(
    1,
    'SHIPPED',
    'Order shipped from Houston Central.'
),
(
    1,
    'DELIVERED',
    'Order delivered successfully.'
);
