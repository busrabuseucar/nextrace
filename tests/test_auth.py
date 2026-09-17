import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from auth import AuthenticationError, AuthService  # noqa: E402
from engine import TraceGraph  # noqa: E402
from storage import ProjectStore  # noqa: E402


class AuthServiceTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        database = Path(self.temporary_directory.name) / "auth-test.db"
        self.store = ProjectStore(database)
        self.auth = AuthService(self.store)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_setup_login_and_logout_flow(self):
        setup_token, setup_user, _ = self.auth.setup(
            "admin@nextrace.local", "GuvenliParola2026"
        )
        self.assertEqual(setup_user["role"], "admin")
        self.assertFalse(setup_user["must_change_password"])
        self.assertEqual(self.auth.authenticate(setup_token)["email"], "admin@nextrace.local")

        login_token, login_user, _ = self.auth.login(
            "ADMIN@nextrace.local", "GuvenliParola2026"
        )
        self.assertEqual(login_user["id"], setup_user["id"])
        self.auth.logout(login_token)
        self.assertIsNone(self.auth.authenticate(login_token))

    def test_rejects_weak_password_and_second_setup(self):
        with self.assertRaises(AuthenticationError):
            self.auth.setup("admin@nextrace.local", "short")
        self.auth.setup("admin@nextrace.local", "GuvenliParola2026")
        with self.assertRaises(ValueError):
            self.auth.setup("other@nextrace.local", "BaskaGuvenli2026")

    def test_wrong_password_fails(self):
        self.auth.setup("admin@nextrace.local", "GuvenliParola2026")
        with self.assertRaises(AuthenticationError):
            self.auth.login("admin@nextrace.local", "YanlisParola2026")

    def test_analyst_only_sees_assigned_projects(self):
        _, admin, _ = self.auth.setup("admin@nextrace.local", "GuvenliParola2026")
        analyst = self.auth.create_user(
            "analyst@nextrace.local", "AnalistParola2026", "analyst"
        )
        data = ROOT / "backend" / "data"
        graph = TraceGraph.from_csv_files(data / "nodes.csv", data / "edges.csv")
        self.store.save_project("demo", "Demo", graph)
        self.assertEqual(self.store.list_projects(analyst["id"]), [])
        self.store.set_project_access("demo", analyst["id"], "viewer")
        projects = self.store.list_projects(analyst["id"])
        self.assertEqual(projects[0]["id"], "demo")
        self.assertEqual(projects[0]["access_level"], "viewer")
        self.assertEqual(self.store.get_project_access("demo", analyst["id"]), "viewer")
        with self.assertRaises(ValueError):
            self.store.set_project_access("demo", admin["id"], "analyst")

    def test_user_changes_temporary_password_and_old_sessions_are_closed(self):
        self.auth.setup("admin@nextrace.local", "GuvenliParola2026")
        analyst = self.auth.create_user(
            "analyst@nextrace.local", "GeciciParola2026", "analyst"
        )
        self.assertTrue(analyst["must_change_password"])
        old_token, login_user, _ = self.auth.login(
            "analyst@nextrace.local", "GeciciParola2026"
        )
        self.assertTrue(login_user["must_change_password"])

        new_token, updated_user, _ = self.auth.change_password(
            analyst["id"], "GeciciParola2026", "YeniGuvenliParola2026"
        )
        self.assertFalse(updated_user["must_change_password"])
        self.assertIsNone(self.auth.authenticate(old_token))
        self.assertEqual(self.auth.authenticate(new_token)["id"], analyst["id"])
        with self.assertRaises(AuthenticationError):
            self.auth.login("analyst@nextrace.local", "GeciciParola2026")

    def test_admin_reset_requires_password_change_and_closes_sessions(self):
        self.auth.setup("admin@nextrace.local", "GuvenliParola2026")
        analyst = self.auth.create_user(
            "analyst@nextrace.local", "GeciciParola2026", "analyst"
        )
        old_token, _, _ = self.auth.login(
            "analyst@nextrace.local", "GeciciParola2026"
        )

        reset_user = self.auth.admin_reset_password(
            analyst["id"], "YoneticiGecici2026"
        )
        self.assertTrue(reset_user["must_change_password"])
        self.assertIsNone(self.auth.authenticate(old_token))
        _, login_user, _ = self.auth.login(
            "analyst@nextrace.local", "YoneticiGecici2026"
        )
        self.assertTrue(login_user["must_change_password"])

    def test_deactivated_user_cannot_login_and_session_is_closed(self):
        self.auth.setup("admin@nextrace.local", "GuvenliParola2026")
        analyst = self.auth.create_user(
            "analyst@nextrace.local", "GeciciParola2026", "analyst"
        )
        token, _, _ = self.auth.login("analyst@nextrace.local", "GeciciParola2026")
        disabled = self.auth.set_user_active(analyst["id"], False)
        self.assertFalse(disabled["active"])
        self.assertIsNone(self.auth.authenticate(token))
        with self.assertRaises(AuthenticationError):
            self.auth.login("analyst@nextrace.local", "GeciciParola2026")

        enabled = self.auth.set_user_active(analyst["id"], True)
        self.assertTrue(enabled["active"])
        self.assertEqual(
            self.auth.login("analyst@nextrace.local", "GeciciParola2026")[1]["id"],
            analyst["id"],
        )

    def test_last_active_admin_cannot_be_deactivated(self):
        _, admin, _ = self.auth.setup(
            "admin@nextrace.local", "GuvenliParola2026"
        )
        with self.assertRaisesRegex(ValueError, "Son aktif yönetici"):
            self.auth.set_user_active(admin["id"], False)

        second_admin = self.auth.create_user(
            "second-admin@nextrace.local", "IkinciYonetici2026", "admin"
        )
        disabled = self.auth.set_user_active(second_admin["id"], False)
        self.assertFalse(disabled["active"])


if __name__ == "__main__":
    unittest.main()
