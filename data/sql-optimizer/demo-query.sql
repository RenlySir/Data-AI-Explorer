SELECT
  o.customer_id,
  SUM(o.amount) AS total_amount
FROM sales.orders AS o
WHERE o.created_at >= '2026-01-01'
GROUP BY o.customer_id
ORDER BY total_amount DESC;
