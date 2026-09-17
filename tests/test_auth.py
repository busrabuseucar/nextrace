import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from auth import AuthenticationError, AuthService  # noqa: E402
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


if __name__ == "__main__":
    unittest.main()
