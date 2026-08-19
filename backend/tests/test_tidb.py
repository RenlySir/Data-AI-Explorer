import os
import unittest
from unittest.mock import MagicMock, patch

from app.tidb import configure_session, platform_connection_settings


class TidbSessionPolicyTest(unittest.TestCase):
    def test_tidb_session_is_read_only_and_uses_configured_resource_group(self) -> None:
        cursor = MagicMock()
        with patch.dict(os.environ, {"TIDB_READ_ENGINES": "tikv,tiflash", "TIDB_RESOURCE_GROUP": "rg_chatbi"}):
            configure_session(cursor, tidb=True)
        statements = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertIn("tidb_isolation_read_engines", statements[0])
        self.assertEqual(statements[1], "SET RESOURCE GROUP `rg_chatbi`")

    def test_mysql_connection_does_not_receive_tidb_session_commands(self) -> None:
        cursor = MagicMock()
        configure_session(cursor, tidb=False)
        cursor.execute.assert_not_called()

    def test_invalid_read_engine_is_rejected(self) -> None:
        cursor = MagicMock()
        with patch.dict(os.environ, {"TIDB_READ_ENGINES": "mysql"}):
            with self.assertRaises(ValueError):
                configure_session(cursor, tidb=True)
        cursor.execute.assert_not_called()

    def test_health_settings_are_non_secret(self) -> None:
        with patch.dict(os.environ, {"AEGIS_PLATFORM_DB_DATABASE": "aegis_platform", "TIDB_RESOURCE_GROUP": "rg_chatbi"}):
            settings = platform_connection_settings()
        self.assertEqual(settings["engine"], "tidb")
        self.assertEqual(settings["resource_group"], "rg_chatbi")
        self.assertNotIn("password", settings)


if __name__ == "__main__":
    unittest.main()
