CREATE TABLE sales.orders (
  order_id BIGINT PRIMARY KEY,
  customer_id BIGINT NOT NULL,
  created_at DATETIME NOT NULL,
  amount DECIMAL(18, 2) NOT NULL,
  KEY idx_created_at (created_at)
);
