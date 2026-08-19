"""Create deterministic, read-only demo data in the existing TiDB cluster.

The script only touches the `aegis_demo` database and can be rerun safely.
It uses the same read-only query shapes exercised by ChatBI, Data Relationships,
and SQL Optimizer demos.
"""

from __future__ import annotations

import os
from datetime import date, timedelta

import pymysql


HOST = os.getenv("TIDB_HOST", "10.2.106.5")
PORT = int(os.getenv("TIDB_PORT", "4100"))
USER = os.getenv("TIDB_USER", "root")
PASSWORD = os.getenv("TIDB_PASSWORD", "")
DATABASE = os.getenv("TIDB_DATABASE", "aegis_demo")


def main() -> None:
    connection = pymysql.connect(
        host=HOST,
        port=PORT,
        user=USER,
        password=PASSWORD,
        autocommit=True,
        charset="utf8mb4",
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DATABASE}`")
            cursor.execute(f"USE `{DATABASE}`")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    id BIGINT PRIMARY KEY COMMENT '客户ID',
                    customer_name VARCHAR(120) NOT NULL COMMENT '客户名称',
                    region VARCHAR(40) NOT NULL COMMENT '所属区域',
                    created_at DATE NOT NULL COMMENT '建档日期'
                ) COMMENT='客户主数据'
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id BIGINT PRIMARY KEY COMMENT '订单ID',
                    customer_id BIGINT NOT NULL COMMENT '客户ID',
                    order_date DATE NOT NULL COMMENT '下单日期',
                    amount DECIMAL(14, 2) NOT NULL COMMENT '订单金额',
                    status VARCHAR(20) NOT NULL COMMENT '订单状态',
                    KEY idx_orders_customer_date (customer_id, order_date)
                ) COMMENT='订单事实表'
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS incidents (
                    id BIGINT PRIMARY KEY COMMENT '事件ID',
                    service VARCHAR(80) NOT NULL COMMENT '服务名称',
                    severity VARCHAR(10) NOT NULL COMMENT '事件等级',
                    status VARCHAR(20) NOT NULL COMMENT '处理状态',
                    opened_at DATETIME NOT NULL COMMENT '发现时间',
                    summary VARCHAR(255) NOT NULL COMMENT '事件摘要'
                ) COMMENT='AIOps 事件演示表'
            """)
            # CREATE TABLE IF NOT EXISTS does not update comments on an existing
            # demo database, so keep metadata idempotent for repeated demos.
            for statement in (
                "ALTER TABLE customers MODIFY COLUMN id BIGINT NOT NULL COMMENT '客户ID'",
                "ALTER TABLE customers MODIFY COLUMN customer_name VARCHAR(120) NOT NULL COMMENT '客户名称'",
                "ALTER TABLE customers MODIFY COLUMN region VARCHAR(40) NOT NULL COMMENT '所属区域'",
                "ALTER TABLE customers MODIFY COLUMN created_at DATE NOT NULL COMMENT '建档日期'",
                "ALTER TABLE orders MODIFY COLUMN id BIGINT NOT NULL COMMENT '订单ID'",
                "ALTER TABLE orders MODIFY COLUMN customer_id BIGINT NOT NULL COMMENT '客户ID'",
                "ALTER TABLE orders MODIFY COLUMN order_date DATE NOT NULL COMMENT '下单日期'",
                "ALTER TABLE orders MODIFY COLUMN amount DECIMAL(14, 2) NOT NULL COMMENT '订单金额'",
                "ALTER TABLE orders MODIFY COLUMN status VARCHAR(20) NOT NULL COMMENT '订单状态'",
                "ALTER TABLE incidents MODIFY COLUMN id BIGINT NOT NULL COMMENT '事件ID'",
                "ALTER TABLE incidents MODIFY COLUMN service VARCHAR(80) NOT NULL COMMENT '服务名称'",
                "ALTER TABLE incidents MODIFY COLUMN severity VARCHAR(10) NOT NULL COMMENT '事件等级'",
                "ALTER TABLE incidents MODIFY COLUMN status VARCHAR(20) NOT NULL COMMENT '处理状态'",
                "ALTER TABLE incidents MODIFY COLUMN opened_at DATETIME NOT NULL COMMENT '发现时间'",
                "ALTER TABLE incidents MODIFY COLUMN summary VARCHAR(255) NOT NULL COMMENT '事件摘要'",
            ):
                cursor.execute(statement)
            cursor.execute("DELETE FROM orders")
            cursor.execute("DELETE FROM customers")
            cursor.execute("DELETE FROM incidents")
            customers = [(1, "华东零售", "华东", date(2025, 1, 12)), (2, "华南制造", "华南", date(2025, 2, 3)), (3, "西北能源", "西北", date(2025, 3, 18))]
            cursor.executemany("INSERT INTO customers VALUES (%s,%s,%s,%s)", customers)
            base = date(2026, 8, 1)
            orders = []
            for index in range(1, 31):
                orders.append((index, (index % 3) + 1, base + timedelta(days=index % 10), 1000 + index * 87.5, "paid" if index % 5 else "pending"))
            cursor.executemany("INSERT INTO orders VALUES (%s,%s,%s,%s,%s)", orders)
            incidents = [(1, "order-sync", "P1", "investigating", "2026-08-19 08:42:00", "订单入仓延迟"), (2, "tidb-cluster", "P2", "open", "2026-08-19 07:15:00", "Region 调度需要关注"), (3, "bi-scheduler", "P2", "resolved", "2026-08-18 21:08:00", "日报刷新恢复")]
            cursor.executemany("INSERT INTO incidents VALUES (%s,%s,%s,%s,%s,%s)", incidents)
            cursor.execute("ANALYZE TABLE customers")
            cursor.execute("ANALYZE TABLE orders")
            cursor.execute("ANALYZE TABLE incidents")
            cursor.execute("SELECT COUNT(*) FROM customers")
            customer_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM orders")
            order_count = cursor.fetchone()[0]
            print({"host": HOST, "port": PORT, "database": DATABASE, "customers": customer_count, "orders": order_count})
    finally:
        connection.close()


if __name__ == "__main__":
    main()
