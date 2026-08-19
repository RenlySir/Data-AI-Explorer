-- TiDB platform setup (review and run with a privileged migration account).
-- The API's idempotent bootstrap creates the two minimum tables as well; this
-- script is the explicit production baseline for resource groups and HTAP.

CREATE DATABASE IF NOT EXISTS aegis_platform
  CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;

USE aegis_platform;

CREATE TABLE IF NOT EXISTS platform_settings (
  id TINYINT NOT NULL,
  payload JSON NOT NULL,
  updated_at DATETIME(6) NOT NULL,
  PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS audit_events (
  event_id VARCHAR(40) NOT NULL,
  actor VARCHAR(160) NOT NULL,
  action VARCHAR(120) NOT NULL,
  resource_type VARCHAR(80) NOT NULL,
  resource_id VARCHAR(160) NULL,
  payload JSON NOT NULL,
  created_at DATETIME(6) NOT NULL,
  PRIMARY KEY (event_id, created_at),
  KEY idx_audit_created_at (created_at),
  KEY idx_audit_resource (resource_type, resource_id)
)
PARTITION BY RANGE (TO_DAYS(created_at)) (
  PARTITION p202608 VALUES LESS THAN (TO_DAYS('2026-09-01')),
  PARTITION pmax VALUES LESS THAN MAXVALUE
);

-- Resource groups isolate analytical ChatBI from control-plane writes. The
-- exact RU budget must be sized from production load tests.
CREATE RESOURCE GROUP IF NOT EXISTS rg_aegis_chatbi
  RU_PER_SEC = 100 PRIORITY = HIGH;
CREATE RESOURCE GROUP IF NOT EXISTS rg_aegis_background
  RU_PER_SEC = 50 PRIORITY = LOW;

-- Optional HTAP replicas. Execute only after TiFlash is installed and the
-- replica count has been reviewed for storage and recovery capacity.
-- ALTER TABLE audit_events SET TIFLASH REPLICA 1;

-- Optional time-series tables for a production migration. Every unique key
-- contains the partition key, as required by TiDB/MySQL partitioning rules.
CREATE TABLE IF NOT EXISTS ai_query_records (
  id VARCHAR(40) NOT NULL,
  tenant_id VARCHAR(64) NOT NULL,
  datasource_id VARCHAR(160) NOT NULL,
  status VARCHAR(32) NOT NULL,
  question TEXT NOT NULL,
  sql_text TEXT NULL,
  created_at DATETIME(6) NOT NULL,
  PRIMARY KEY (id, created_at),
  KEY idx_query_tenant_created (tenant_id, created_at),
  KEY idx_query_datasource_created (datasource_id, created_at)
)
PARTITION BY RANGE (TO_DAYS(created_at)) (
  PARTITION p202608 VALUES LESS THAN (TO_DAYS('2026-09-01')),
  PARTITION pmax VALUES LESS THAN MAXVALUE
);
