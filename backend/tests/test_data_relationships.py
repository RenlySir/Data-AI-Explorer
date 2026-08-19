import time
import unittest

from fastapi.testclient import TestClient

from app.data_relationships import QUERY_LOG_COUNTS, SQL_EDGES, SQL_OBSERVATIONS
from app.main import (
    RELATIONSHIP_CATALOGS,
    SQL_COLLECTOR_STATUS,
    SQL_COLLECTOR_STOPS,
    app,
    stop_sql_collector,
)


class DataRelationshipApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        for datasource_id in list(SQL_COLLECTOR_STOPS):
            stop_sql_collector(datasource_id)
        SQL_COLLECTOR_STATUS.clear()
        RELATIONSHIP_CATALOGS.clear()
        SQL_OBSERVATIONS.clear()
        SQL_EDGES.clear()
        QUERY_LOG_COUNTS.clear()

    def test_metadata_collection_builds_table_and_field_network(self) -> None:
        response = self.client.post(
            "/api/v1/data-relationships/ds-demo-tidb/collect"
        )
        self.assertEqual(response.status_code, 200, response.text)
        snapshot = response.json()
        self.assertEqual(len(snapshot["schemas"]), 2)
        self.assertEqual(
            len([node for node in snapshot["nodes"] if node["kind"] == "table"]),
            3,
        )
        self.assertTrue(
            any(
                edge["level"] == "field"
                and edge["kind"] == "foreign_key"
                and edge["source"] == "sales.orders.customer_id"
                for edge in snapshot["edges"]
            )
        )
        self.assertTrue(
            any(
                edge["level"] == "table"
                and edge["source"] == "sales.orders"
                and edge["target"] == "sales.customers"
                for edge in snapshot["edges"]
            )
        )

    def test_manual_sql_observation_discovers_join_columns(self) -> None:
        self.client.post("/api/v1/data-relationships/ds-demo-tidb/collect")
        response = self.client.post(
            "/api/v1/data-relationships/ds-demo-tidb/sql-observations",
            json={
                "source": "manual-test",
                "sql": (
                    "SELECT o.order_id, c.region FROM sales.orders o "
                    "JOIN sales.customers c ON c.customer_id=o.customer_id"
                ),
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["execution_count"], 1)
        snapshot = self.client.get(
            "/api/v1/data-relationships/ds-demo-tidb"
        ).json()
        sql_edges = [
            edge
            for edge in snapshot["edges"]
            if edge["source_type"] == "sql" and edge["level"] == "field"
        ]
        self.assertEqual(len(sql_edges), 1)
        self.assertEqual(sql_edges[0]["source"], "sales.customers.customer_id")
        self.assertEqual(sql_edges[0]["target"], "sales.orders.customer_id")

        blocked = self.client.post(
            "/api/v1/data-relationships/ds-demo-tidb/sql-observations",
            json={"sql": "DELETE FROM sales.orders"},
        )
        self.assertEqual(blocked.status_code, 422)

        literal = self.client.post(
            "/api/v1/data-relationships/ds-demo-tidb/sql-observations",
            json={
                "sql": (
                    "SELECT * FROM sales.orders o JOIN sales.customers c "
                    "ON c.customer_id=o.customer_id WHERE c.region='private-value'"
                )
            },
        )
        self.assertEqual(literal.status_code, 201)
        self.assertNotIn("private-value", literal.json()["sql_preview"])
        self.assertIn("?", literal.json()["sql_preview"])

    def test_statement_summary_collection_is_incremental(self) -> None:
        first = self.client.post(
            "/api/v1/data-relationships/ds-demo-tidb/collect-sql"
        )
        self.assertEqual(first.status_code, 200, first.text)
        first_counts = {
            item["digest"]: item["execution_count"]
            for item in first.json()["sql_observations"]
        }
        self.assertEqual(sorted(first_counts.values()), [6, 18])

        second = self.client.post(
            "/api/v1/data-relationships/ds-demo-tidb/collect-sql"
        )
        second_counts = {
            item["digest"]: item["execution_count"]
            for item in second.json()["sql_observations"]
        }
        self.assertEqual(second_counts, first_counts)
        self.assertEqual(
            self.client.get("/api/v1/data-relationships/missing").status_code,
            404,
        )

    def test_server_collector_runs_and_can_be_stopped(self) -> None:
        enabled = self.client.put(
            "/api/v1/data-relationships/ds-demo-tidb/sql-collector",
            json={"enabled": True, "interval_seconds": 30},
        )
        self.assertEqual(enabled.status_code, 200, enabled.text)
        self.assertTrue(enabled.json()["enabled"])

        status = enabled.json()
        for _ in range(50):
            status = self.client.get(
                "/api/v1/data-relationships/ds-demo-tidb/sql-collector"
            ).json()
            if status["last_collected_at"]:
                break
            time.sleep(0.01)
        self.assertIsNotNone(status["last_collected_at"])
        snapshot = self.client.get(
            "/api/v1/data-relationships/ds-demo-tidb"
        ).json()
        self.assertEqual(len(snapshot["sql_observations"]), 2)

        disabled = self.client.put(
            "/api/v1/data-relationships/ds-demo-tidb/sql-collector",
            json={"enabled": False, "interval_seconds": 30},
        )
        self.assertEqual(disabled.status_code, 200, disabled.text)
        self.assertFalse(disabled.json()["enabled"])


if __name__ == "__main__":
    unittest.main()
