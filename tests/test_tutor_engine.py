import unittest

from tutor_engine import build_prompt, parse_quiz_json


class TutorEngineTests(unittest.TestCase):
    def test_build_prompt_includes_task_and_profile(self):
        prompt = build_prompt(
            "Explain recursion.",
            "Use a simple example.",
            learner_level="Beginner",
            language="Python",
        )
        self.assertIn("Explain recursion.", prompt)
        self.assertIn("Beginner", prompt)
        self.assertIn("Python", prompt)
        self.assertIn("Use a simple example.", prompt)

    def test_parse_quiz_json_validates_questions(self):
        raw = '''{"questions":[{"question":"Which type is mutable?","options":{"A":"tuple","B":"list","C":"str","D":"int"},"answer":"B","explanation":"Lists can be changed after creation."}]}'''
        quiz = parse_quiz_json(raw)
        self.assertEqual(len(quiz), 1)
        self.assertEqual(quiz[0]["answer"], "B")
        self.assertEqual(quiz[0]["options"]["B"], "list")

    def test_parse_quiz_json_accepts_fenced_response(self):
        raw = '''```json\n{"questions":[{"question":"Q?","options":{"A":"1","B":"2","C":"3","D":"4"},"answer":"A","explanation":"Because."}]}\n```'''
        self.assertEqual(parse_quiz_json(raw)[0]["answer"], "A")

    def test_parse_quiz_json_rejects_invalid_payload(self):
        with self.assertRaises(ValueError):
            parse_quiz_json("not json")


if __name__ == "__main__":
    unittest.main()
