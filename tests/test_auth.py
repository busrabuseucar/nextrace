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


if __name__ == "__main__":
    unittest.main()
