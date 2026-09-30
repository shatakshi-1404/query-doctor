-- 10,000 users
INSERT INTO users (name, email, city, created_at)
SELECT
    'User ' || g,
    'user' || g || '@example.com',
    (ARRAY['Mumbai','Delhi','Bangalore','Pune','Chennai',
           'Kolkata','Hyderabad','Bhopal','Indore','Jaipur'])[1 + floor(random() * 10)::int],
    now() - make_interval(days => floor(random() * 365)::int)
FROM generate_series(1, 10000) AS g;

-- 1,000 products
INSERT INTO products (name, category, price)
SELECT
    'Product ' || g,
    (ARRAY['Electronics','Books','Clothing','Home','Sports'])[1 + floor(random() * 5)::int],
    round((100 + random() * 4900)::numeric, 2)
FROM generate_series(1, 1000) AS g;

-- 50,000 orders
INSERT INTO orders (user_id, status, total, created_at)
SELECT
    1 + floor(random() * 10000)::int,
    (ARRAY['pending','paid','shipped','cancelled'])[1 + floor(random() * 4)::int],
    round((200 + random() * 9800)::numeric, 2),
    now() - make_interval(days => floor(random() * 365)::int)
FROM generate_series(1, 50000) AS g;

-- 150,000 order items
INSERT INTO order_items (order_id, product_id, quantity, unit_price)
SELECT
    1 + floor(random() * 50000)::int,
    1 + floor(random() * 1000)::int,
    1 + floor(random() * 5)::int,
    round((100 + random() * 4900)::numeric, 2)
FROM generate_series(1, 150000) AS g;

-- Refresh planner statistics (important for EXPLAIN later)
ANALYZE;
