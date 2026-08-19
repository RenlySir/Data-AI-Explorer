CREATE DATABASE IF NOT EXISTS aegis_chatbi_demo
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_bin;

USE aegis_chatbi_demo;

CREATE TABLE IF NOT EXISTS number_seed (
  n INT PRIMARY KEY COMMENT '演示数据序号'
) COMMENT='演示数据生成辅助表';

CREATE TABLE IF NOT EXISTS customer_dim (
  customer_id BIGINT PRIMARY KEY COMMENT '客户唯一标识',
  customer_name VARCHAR(64) NOT NULL COMMENT '客户名称',
  region VARCHAR(32) NOT NULL COMMENT '客户所属区域',
  customer_level VARCHAR(16) NOT NULL COMMENT '客户等级',
  registered_at DATE NOT NULL COMMENT '注册日期'
) COMMENT='客户维度表';

CREATE TABLE IF NOT EXISTS product_dim (
  product_id BIGINT PRIMARY KEY COMMENT '商品唯一标识',
  product_name VARCHAR(64) NOT NULL COMMENT '商品名称',
  category VARCHAR(32) NOT NULL COMMENT '商品品类',
  unit_price DECIMAL(12,2) NOT NULL COMMENT '商品单价'
) COMMENT='商品维度表';

CREATE TABLE IF NOT EXISTS order_fact (
  order_id BIGINT PRIMARY KEY COMMENT '订单唯一标识',
  order_date DATE NOT NULL COMMENT '下单日期',
  customer_id BIGINT NOT NULL COMMENT '客户标识',
  product_id BIGINT NOT NULL COMMENT '商品标识',
  channel VARCHAR(16) NOT NULL COMMENT '销售渠道',
  quantity INT NOT NULL COMMENT '购买数量',
  amount DECIMAL(14,2) NOT NULL COMMENT '订单金额',
  order_status VARCHAR(16) NOT NULL COMMENT '订单状态',
  KEY idx_order_date_region (order_date, customer_id),
  KEY idx_product (product_id)
) COMMENT='经营分析订单事实表';

TRUNCATE TABLE number_seed;
TRUNCATE TABLE order_fact;
TRUNCATE TABLE customer_dim;
TRUNCATE TABLE product_dim;

INSERT INTO number_seed (n) VALUES
  (0),(1),(2),(3),(4),(5),(6),(7),(8),(9),
  (10),(11),(12),(13),(14),(15),(16),(17),(18),(19),
  (20),(21),(22),(23),(24),(25),(26),(27),(28),(29),
  (30),(31),(32),(33),(34),(35),(36),(37),(38),(39),
  (40),(41),(42),(43),(44),(45),(46),(47),(48),(49),
  (50),(51),(52),(53),(54),(55),(56),(57),(58),(59),
  (60),(61),(62),(63),(64),(65),(66),(67),(68),(69),
  (70),(71),(72),(73),(74),(75),(76),(77),(78),(79),
  (80),(81),(82),(83),(84),(85),(86),(87),(88),(89),
  (90),(91),(92),(93),(94),(95),(96),(97),(98),(99);

INSERT INTO customer_dim
SELECT
  n + 1,
  CONCAT('客户-', LPAD(n + 1, 3, '0')),
  CASE MOD(n, 4) WHEN 0 THEN '华东' WHEN 1 THEN '华南' WHEN 2 THEN '华北' ELSE '西南' END,
  CASE MOD(n, 3) WHEN 0 THEN '战略' WHEN 1 THEN '重点' ELSE '普通' END,
  DATE_ADD('2025-01-01', INTERVAL n * 5 DAY)
FROM number_seed
WHERE n < 30;

INSERT INTO product_dim VALUES
  (1, '智能传感器 A1', '传感器', 680.00),
  (2, '工业网关 G2', '边缘设备', 1980.00),
  (3, '数据采集器 C3', '边缘设备', 1280.00),
  (4, '控制模块 M4', '控制器', 2380.00),
  (5, '高精度仪表 P5', '仪器仪表', 3280.00),
  (6, '视觉检测单元 V6', '机器视觉', 5680.00),
  (7, '设备管理软件 S7', '工业软件', 8800.00),
  (8, '预测维护套件 K8', '工业软件', 12800.00);

INSERT INTO order_fact
SELECT
  seed.n + 10001 AS order_id,
  DATE_ADD('2026-08-01', INTERVAL MOD(seed.n, 15) DAY) AS order_date,
  MOD(seed.n * 7, 30) + 1 AS customer_id,
  product.product_id,
  CASE MOD(seed.n, 3) WHEN 0 THEN '直销' WHEN 1 THEN '渠道' ELSE '电商' END AS channel,
  MOD(seed.n, 4) + 1 AS quantity,
  product.unit_price * (MOD(seed.n, 4) + 1) AS amount,
  CASE MOD(seed.n, 10) WHEN 0 THEN '已取消' WHEN 1 THEN '处理中' ELSE '已完成' END AS order_status
FROM number_seed AS seed
JOIN product_dim AS product ON product.product_id = MOD(seed.n * 5, 8) + 1
WHERE seed.n < 90;

CREATE OR REPLACE VIEW daily_sales AS
SELECT
  order_date AS stat_date,
  COUNT(*) AS order_count,
  SUM(amount) AS gmv,
  SUM(CASE WHEN order_status = '已完成' THEN amount ELSE 0 END) AS completed_gmv
FROM order_fact
GROUP BY order_date;
