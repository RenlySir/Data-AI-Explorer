# TiDB 全面替换专项实施方案

版本：v1.0
日期：2026-08-20
适用范围：Aegis AI Control Plane 当前 FastAPI 可运行基线，以及后续 Java 21/Spring Boot 控制面迁移

## 1. 目标与边界

平台内部不再依赖 PostgreSQL 或独立 MySQL 作为权威数据库，统一使用 TiDB 的 MySQL 协议保存平台元数据、审计、查询记录、Agent 配置、关系快照和工作流检查点。MySQL 仍可作为用户主动添加的外部业务数据源，这是数据源适配能力，不是平台内部数据库。

当前仓库的可运行实现使用 PyMySQL 连接 TiDB；Java 方案中的 JDBC 驱动继续使用 MySQL Connector/J。两者都通过 TiDB MySQL 协议工作，API DTO 不变。

## 2. 目标架构

```text
Web / API
   │
   ├── TiDB SQL 端口（控制面元数据、审计、查询记录）
   │      ├── TiKV：事务写入和点查
   │      └── TiFlash：可选分析副本，承载报表和审计分析
   │
   ├── Redis：短期缓存、限流、SSE 连接状态（非权威存储）
   ├── MinIO/S3：CSV/Parquet、导出、证据和备份对象
   ├── TiCDC → Kafka：变更事件和下游实时分析
   └── BR：TiDB 分布式备份与恢复
```

本地 Compose 使用单节点 `pingcap/tidb` 的 `mocktikv` 模式，目的是免安装运行演示；三节点演示继续连接已有 TiDB 集群。生产环境应使用 TiUP 或 TiDB Operator 部署 TiDB、TiKV、PD、TiFlash、TiCDC 和监控组件，不能把 `mocktikv` 作为生产方案。

## 3. 配置与代码变更

### 3.1 配置

统一配置：

```bash
TIDB_HOST=tidb
TIDB_PORT=4000
TIDB_USER=root
TIDB_PASSWORD=            # 生产由 Vault/OpenBao 注入
TIDB_DATABASE=aegis_demo
AEGIS_PLATFORM_DB_HOST=tidb
AEGIS_PLATFORM_DB_PORT=4000
AEGIS_PLATFORM_DB_DATABASE=aegis_platform
TIDB_READ_ENGINES=tikv,tiflash
TIDB_RESOURCE_GROUP=rg_aegis_chatbi
```

`TIDB_READ_ENGINES` 和资源组均是可选能力。未配置资源组时使用 TiDB 默认资源组；配置后，ChatBI 和 live EXPLAIN 会在连接建立时设置读引擎和资源组。TiDB 当前版本对 `SET TRANSACTION READ ONLY` 仅提供受控 no-op，因此平台通过只读数据库账号、SQL AST、超时、行数限制和资源组实现只读安全，不发送不兼容的伪只读事务语句。外部 MySQL 数据源不应用这些 TiDB session 变量。

### 3.2 当前代码

- `backend/app/platform_store.py`：平台设置与审计通过 PyMySQL 写入 TiDB。
- `backend/app/tidb.py`：统一设置 TiDB 只读事务、`tidb_isolation_read_engines` 和资源组。
- `backend/app/chatbi.py`：TiDB 数据源连接使用统一 session policy。
- `scripts/tidb-production-setup.sql`：显式创建平台表、审计分区表、查询记录分区表、资源组和可选 TiFlash 配置。
- `scripts/verify-tidb-platform.py`：检查 TiDB 版本、读引擎和平台表。
- `docker-compose.yml`：默认服务由 PostgreSQL 替换为 TiDB。

## 4. Schema 设计

### 4.1 主键和租户字段

平台业务表使用 UUIDv7 或 Snowflake 字符串 ID；高写入表不使用单调自增主键。所有生产业务表必须包含 `tenant_id`、`created_at`、`updated_at`、`version` 和必要的 `deleted_at`。TiDB 分区表的所有唯一键必须包含分区键，因此时间分区表采用 `(id, created_at)` 复合主键。

### 4.2 分区策略

优先对 `audit_events`、`ai_query_records`、`domain_events`、`sql_observations` 等时间增长表使用按月 Range 分区。保留 `pmax` 分区接收未来数据，月度运维任务提前创建新分区并归档旧分区。分区数量控制在 1000 以内，查询必须带时间条件以触发分区裁剪。

### 4.3 HTAP

在线设置、审批和审计写入 TiKV；趋势报表、审计聚合和经营分析可使用 TiFlash 副本。TiFlash 副本必须按表评估存储、同步延迟和恢复成本，不能对所有表无差别开启。脚本中 `ALTER TABLE ... SET TIFLASH REPLICA 1` 默认注释，需在 TiFlash 已部署且容量评估通过后执行。

### 4.4 资源组

`rg_aegis_chatbi` 限制自然语言分析的 RU 和优先级，`rg_aegis_background` 限制关系采集、知识库重建等后台任务。资源组预算必须由压测确定；API 只允许引用管理员预创建的资源组，不接受用户在请求中任意传入资源组名称。

## 5. 迁移路线

### 5.1 PostgreSQL/MySQL 到 TiDB

1. 盘点表、索引、约束、JSON、分区、序列、函数和扩展。
2. 使用 Dumpling 导出 MySQL/TiDB 兼容数据；PostgreSQL 数据先通过 DataX/ETL 转换为 TiDB 支持的 MySQL DDL/CSV。
3. 使用 TiDB Lightning 导入全量数据，设置导入窗口和限速。
4. MySQL 源使用 DM 做全量+增量同步；PostgreSQL 源通过 Debezium/DataX CDC 或业务双写适配器同步，不能直接假设 DM 支持 PostgreSQL。
5. 使用 `sync-diff-inspector` 对行数、Checksum、抽样和关键业务聚合做一致性校验。
6. 灰度切换只读流量，观察延迟、错误、TiKV/TiFlash 资源和 SQL 计划，再切换写流量。

### 5.2 回滚

切换前保留源库只读窗口和 Binlog/CDC 位点。应用通过配置切换数据库别名；回滚前冻结写入，确认 TiCDC/DM 位点和校验结果，禁止在未完成对账时双向写入。

## 6. CDC 与事件

平台领域事件继续使用 Outbox 语义；TiCDC 用于捕获 TiDB 表变更并投递 Kafka/Flink。两者职责不同：Outbox 表达经过业务策略确认的领域事件，TiCDC 表达数据库事实变更。下游消费者以 `event_id`/事务提交时间幂等，不把 TiCDC 当作审批或权限校验替代品。

## 7. 运维与可观测性

- 部署：TiUP 适用于虚拟机/裸机，TiDB Operator 适用于 Kubernetes。
- 监控：采集 TiDB、TiKV、PD、TiFlash、TiCDC、SQL 延迟、RU 消耗、Region、磁盘和 GC 指标。
- 备份：使用 BR 做全量/增量备份，备份清单写入对象存储并定期恢复演练。
- 变更：DDL 通过版本化迁移执行，禁止业务进程启动时执行不可逆 DDL。
- 权限：API 查询账号只读；平台迁移账号独立；关系采集账号只授予 `information_schema` 和语句摘要所需权限；禁止复用 root。
- 安全：TLS、最小权限、Secret 不入 Git、SQL AST 只读校验、查询超时、最大行数和资源组限额。

## 8. 验收标准

1. `docker compose config --quiet` 通过，默认配置不出现 PostgreSQL 服务或变量。
2. 本地 TiDB 可健康启动，平台 API 能自动创建 `aegis_platform` 和基础表。
3. `scripts/verify-tidb-platform.py` 返回 TiDB 版本、读引擎和平台表。
4. 三节点 `/health`、`/api/v1/deployment/status` 和 ChatBI/SSE 链路通过。
5. 真实 TiDB 只读查询、关系采集、SQL `EXPLAIN` 和审计写入通过。
6. 生产 TiFlash、TiCDC、BR、资源组和分区需在目标集群完成独立容量、故障和恢复验收。

## 9. 明确限制

本轮未把用户主动配置的 MySQL 外部数据源删除，因为产品需求仍要求支持 MySQL 数据源；“全面替换”指平台内部控制面和默认部署基础设施。Java 21/Spring Boot 目标架构的 JDBC、Flyway、Repository 和事务实现应按本方案迁移到 TiDB，当前 FastAPI 代码不声称已经完成 Java 控制面的重写。
