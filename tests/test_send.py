import os
import tempfile
import unittest
from unittest import mock

from src.env import load_dotenv
from src.send import build_message, mail_settings_from_env, send_email


class BuildMessageTest(unittest.TestCase):
    def test_has_text_and_html_parts(self):
        msg = build_message("Asunto", "<p>hola</p>", "hola", "a@x.com", ["b@x.com", "c@x.com"])
        self.assertEqual(msg["Subject"], "Asunto")
        self.assertEqual(msg["To"], "b@x.com, c@x.com")
        types = [p.get_content_type() for p in msg.iter_parts()]
        self.assertEqual(types, ["text/plain", "text/html"])


class SettingsTest(unittest.TestCase):
    def test_missing_variables_raise(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                mail_settings_from_env()

    def test_password_spaces_removed_and_multiple_recipients(self):
        env = {"SMTP_USER": "a@x.com", "SMTP_PASSWORD": "abcd efgh ijkl mnop", "MAIL_TO": "b@x.com, c@x.com"}
        with mock.patch.dict(os.environ, env, clear=True):
            cfg = mail_settings_from_env()
        self.assertEqual(cfg["password"], "abcdefghijklmnop")
        self.assertEqual(cfg["to"], ["b@x.com", "c@x.com"])
        self.assertEqual((cfg["host"], cfg["port"]), ("smtp.gmail.com", 465))


class SendTest(unittest.TestCase):
    def test_send_logs_in_and_sends(self):
        msg = build_message("S", "<p>h</p>", "h", "a@x.com", ["b@x.com"])
        with mock.patch("src.send.smtplib.SMTP_SSL") as smtp_cls:
            send_email(msg, "a@x.com", "secreto")
        smtp = smtp_cls.return_value.__enter__.return_value
        smtp.login.assert_called_once_with("a@x.com", "secreto")
        smtp.send_message.assert_called_once_with(msg)


class DotenvTest(unittest.TestCase):
    def test_loads_values_without_overriding_existing(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, ".env")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write('# comentario\nFOO_TEST=uno\nBAR_TEST="dos"\n')
            with mock.patch.dict(os.environ, {"FOO_TEST": "ya_definida"}, clear=False):
                load_dotenv(path)
                self.assertEqual(os.environ["FOO_TEST"], "ya_definida")
                self.assertEqual(os.environ["BAR_TEST"], "dos")
            os.environ.pop("BAR_TEST", None)


if __name__ == "__main__":
    unittest.main()
