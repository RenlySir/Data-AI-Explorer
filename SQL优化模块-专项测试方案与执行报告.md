# SQL 优化模块专项测试方案与执行报告

## 1. 测试目标

验证 SQL 优化模块在文本、文件、受控目录三种输入下，能够安全解析只读 SQL，按 TiDB 7.5-8.5 版本画像生成可解释建议，并在真实模式严格校验目标 TiDB 版本后获取 EXPLAIN。测试不把静态模拟等价为真实 TiDB 优化器。

## 2. 测试范围

| 测试域 | 核心内容 | 当前结果 |
|---|---|---|
| 版本 | 7.5、8.0-8.5 列表；patch 归一化；不支持版本拒绝 | 通过 |
| SQL 安全 | 单条 SELECT/CTE；DDL/DML/多语句拒绝 | 通过 |
| 规则 | 候选复合索引、左前缀去重、全扫、JOIN、LIKE、函数谓词、统计信息 | 通过 |
| 版本差异 | 8.3 起 `INL_MERGE_JOIN` 废弃规则 | 通过 |
| 输入 | 多文件上传、UTF-8、后缀/大小限制、受控目录和越权目录 | 通过 |
| 真实计划 | MCP 版本读取、版本一致、verbose EXPLAIN、版本冲突 | Mock 集成通过 |
| 前端 | 导航、版本切换、模拟/真实模式、编辑器、目录弹窗、结果展示 | 浏览器联调通过 |
| 构建回归 | Python 单元/接口测试、TypeScript/Vite 构建、Compose 配置 | 通过 |

## 3. 关键测试用例

| 编号 | 场景 | 预期 |
|---|---|---|
| SQL-OPT-001 | 输入 TiDB `v8.5.4` | 归一化为请求版本 8.5.4，使用 8.5 画像 |
| SQL-OPT-002 | 输入 TiDB 7.4 | HTTP 422，不回退到错误画像 |
| SQL-OPT-003 | 输入 DROP/UPDATE | HTTP 400，不调用 MCP |
| SQL-OPT-004 | SQL 含 WHERE + GROUP BY + range | 按等值、分组/排序、范围顺序生成候选索引 |
| SQL-OPT-005 | DDL 已有相同左前缀索引 | 不重复生成 CREATE INDEX |
| SQL-OPT-006 | TiDB 8.2 使用 `INL_MERGE_JOIN` | 不触发 8.3 规则 |
| SQL-OPT-007 | TiDB 8.3 使用 `INL_MERGE_JOIN` | 产生废弃提示 |
| SQL-OPT-008 | 上传 `.csv` 作为 SQL 输入 | HTTP 415 |
| SQL-OPT-009 | 扫描白名单外目录 | HTTP 403 |
| SQL-OPT-010 | 请求 8.5、实际集群 8.4 | HTTP 409，不执行 EXPLAIN |
| SQL-OPT-011 | 请求 8.5、实际集群 8.5.4 | 执行 verbose EXPLAIN，标记版本已验证 |
| SQL-OPT-012 | 模拟模式返回计划 | 节点带 `hypothesis`，响应包含三条假设说明 |

## 4. 自动化执行

```bash
PYTHONPATH=backend python -m unittest discover -s backend/tests -v
npm run build --prefix apps/web
python -m compileall -q backend
docker compose config --quiet
```

测试代码位于 `backend/tests/test_sql_optimizer.py`。MCP 集成通过可控 mock 验证调用顺序、版本门禁和计划映射，不依赖生产数据库。

## 5. 生产验收门槛

- 使用 TiDB 7.5 LTS、8.1 LTS、8.5 LTS 真实测试集群完成 MCP 连接与权限验收。
- 每个支持 minor 至少准备 30 条黄金 SQL，覆盖 OLTP 点查、范围、Join、聚合、分区、TiFlash、Index Merge 和 Plan Cache。
- 对真实 EXPLAIN 计划结构做版本兼容测试，确保列名变化不会丢失计划字段。
- 建议实施前后以 p95 时延、扫描行数、RU/CPU、内存、磁盘 spill 和写放大评估，不以“创建索引成功”作为性能验收。
- 安全验证覆盖 SSRF、路径穿越、超大输入、恶意多语句、MCP 工具越权、超时与并发资源保护。

## 6. 当前边界

当前静态模式是版本感知的规则分析器，不是 TiDB planner 的 Go 代码仿真。真实 TiDB、真实统计信息和真实数据分布尚未在本工作区提供，因此真实集群性能结论、patch 级优化器修复和压力指标必须在目标环境补充验收。
