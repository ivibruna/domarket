import os
import unittest
from unittest import mock

from src.notify import run_url


class RunUrlTest(unittest.TestCase):
    def test_builds_url_when_github_vars_present(self):
        env = {"GITHUB_SERVER_URL": "https://github.com", "GITHUB_REPOSITORY": "ivibruna/domarket",
               "GITHUB_RUN_ID": "123"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(run_url(), "https://github.com/ivibruna/domarket/actions/runs/123")

    def test_falls_back_without_github_vars(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIn("localmente", run_url())


if __name__ == "__main__":
    unittest.main()
