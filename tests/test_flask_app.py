import unittest

from app import create_app


class FlaskAppSmokeTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-secret"})
        self.client = self.app.test_client()

    def test_home_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Understand code", response.data)

    def test_all_workspaces_load(self):
        for path in ("/chat", "/explain", "/debug", "/hints", "/quiz", "/roadmap"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)

    def test_settings_are_saved_without_putting_key_in_cookie(self):
        response = self.client.post(
            "/settings",
            data={
                "level": "Intermediate",
                "language": "C++",
                "learning_style": "Direct and practical",
                "model_name": "gemini-test-model",
                "api_key": "test-key-do-not-leak",
                "next": "/",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Intermediate", response.data)
        self.assertNotIn(b"test-key-do-not-leak", response.headers.get("Set-Cookie", "").encode())

    def test_chat_page_has_composer(self):
        response = self.client.get("/chat")
        self.assertIn(b'name="question"', response.data)
        self.assertIn(b"Clear chat", response.data)


if __name__ == "__main__":
    unittest.main()
