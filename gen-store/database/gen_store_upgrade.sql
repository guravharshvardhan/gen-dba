-- GenStore uses the existing Gen-DBA gendba database.
-- Run this once in pgAdmin Query Tool.

ALTER TABLE products ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS image_url TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS rating DECIMAL(2,1) DEFAULT 4.5;
ALTER TABLE products ADD COLUMN IF NOT EXISTS reviews_count INT DEFAULT 0;

-- Small realistic catalog for the demo. Existing products are not removed.
INSERT INTO products (name, category, price, stock, description, image_url, rating, reviews_count)
SELECT 'AeroBeat Pro Wireless Headphones', 'Electronics', 3499.00, 120,
       'Adaptive noise cancellation, 40-hour battery and low-latency audio for work and travel.',
       'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=900&q=80', 4.7, 1842
WHERE NOT EXISTS (SELECT 1 FROM products WHERE name = 'AeroBeat Pro Wireless Headphones');

INSERT INTO products (name, category, price, stock, description, image_url, rating, reviews_count)
SELECT 'PixelView 27-inch 4K Monitor', 'Electronics', 28999.00, 48,
       '4K IPS display with USB-C connectivity and a creator-friendly color profile.',
       'https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=900&q=80', 4.6, 734
WHERE NOT EXISTS (SELECT 1 FROM products WHERE name = 'PixelView 27-inch 4K Monitor');

INSERT INTO products (name, category, price, stock, description, image_url, rating, reviews_count)
SELECT 'FlexKey Mechanical Keyboard', 'Accessories', 5299.00, 95,
       'Hot-swappable mechanical keyboard with compact layout and programmable controls.',
       'https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=900&q=80', 4.8, 621
WHERE NOT EXISTS (SELECT 1 FROM products WHERE name = 'FlexKey Mechanical Keyboard');

INSERT INTO products (name, category, price, stock, description, image_url, rating, reviews_count)
SELECT 'Orbit Wireless Mouse', 'Accessories', 1999.00, 180,
       'Ergonomic wireless mouse with silent clicks and precision tracking.',
       'https://images.unsplash.com/photo-1527814050087-3793815479db?auto=format&fit=crop&w=900&q=80', 4.5, 1103
WHERE NOT EXISTS (SELECT 1 FROM products WHERE name = 'Orbit Wireless Mouse');

INSERT INTO products (name, category, price, stock, description, image_url, rating, reviews_count)
SELECT 'NorthPeak Everyday Backpack', 'Travel', 3199.00, 70,
       'Water-resistant commuter backpack with laptop sleeve and smart organization.',
       'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=900&q=80', 4.7, 987
WHERE NOT EXISTS (SELECT 1 FROM products WHERE name = 'NorthPeak Everyday Backpack');

INSERT INTO products (name, category, price, stock, description, image_url, rating, reviews_count)
SELECT 'UrbanForm Running Shoes', 'Fashion', 4499.00, 84,
       'Lightweight daily trainers built for city runs and long walks.',
       'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=80', 4.6, 1456
WHERE NOT EXISTS (SELECT 1 FROM products WHERE name = 'UrbanForm Running Shoes');

INSERT INTO products (name, category, price, stock, description, image_url, rating, reviews_count)
SELECT 'TerraSip Steel Bottle', 'Home', 1299.00, 210,
       'Double-wall insulated steel bottle that keeps drinks cold for up to 24 hours.',
       'https://images.unsplash.com/photo-1602143407151-7111542de6e8?auto=format&fit=crop&w=900&q=80', 4.8, 2187
WHERE NOT EXISTS (SELECT 1 FROM products WHERE name = 'TerraSip Steel Bottle');

INSERT INTO products (name, category, price, stock, description, image_url, rating, reviews_count)
SELECT 'Luma Desk Lamp', 'Home', 2299.00, 65,
       'Minimal LED desk lamp with adjustable color temperature and touch controls.',
       'https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=900&q=80', 4.5, 512
WHERE NOT EXISTS (SELECT 1 FROM products WHERE name = 'Luma Desk Lamp');

INSERT INTO products (name, category, price, stock, description, image_url, rating, reviews_count)
SELECT 'StudioDock USB-C Hub', 'Electronics', 3999.00, 90,
       '7-in-1 USB-C hub with HDMI, card readers and high-speed USB ports.',
       'https://images.unsplash.com/photo-1625842268584-8f3296236761?auto=format&fit=crop&w=900&q=80', 4.6, 401
WHERE NOT EXISTS (SELECT 1 FROM products WHERE name = 'StudioDock USB-C Hub');

INSERT INTO products (name, category, price, stock, description, image_url, rating, reviews_count)
SELECT 'Cedar Everyday Sneakers', 'Fashion', 3799.00, 76,
       'Clean everyday sneakers with cushioned footbed and durable rubber outsole.',
       'https://images.unsplash.com/photo-1549298916-b41d501d3772?auto=format&fit=crop&w=900&q=80', 4.4, 833
WHERE NOT EXISTS (SELECT 1 FROM products WHERE name = 'Cedar Everyday Sneakers');

-- Helpful index used by the normal catalog filter.
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);

-- Gen-DBA intentionally already has an index on users(city).
-- The customer-search endpoint uses LOWER(city) to create a realistic
-- optimization candidate for the Gen-DBA advisor demo.
