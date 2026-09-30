DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    email       VARCHAR(150) NOT NULL,
    city        VARCHAR(50)  NOT NULL,
    created_at  TIMESTAMP    NOT NULL DEFAULT now()
);

CREATE TABLE products (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(150) NOT NULL,
    category    VARCHAR(50)  NOT NULL,
    price       NUMERIC(10,2) NOT NULL
);

CREATE TABLE orders (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    status      VARCHAR(20) NOT NULL,
    total       NUMERIC(10,2) NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE order_items (
    id          SERIAL PRIMARY KEY,
    order_id    INTEGER NOT NULL REFERENCES orders(id),
    product_id  INTEGER NOT NULL REFERENCES products(id),
    quantity    INTEGER NOT NULL,
    unit_price  NUMERIC(10,2) NOT NULL
);
