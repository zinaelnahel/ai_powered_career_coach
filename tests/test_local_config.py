from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from local_config import LocalConfig


class LocalConfigTests(unittest.TestCase):
    def test_load_new_file_then_update_and_remove_key(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            environ = {}
            config = LocalConfig(path, environ)
            config.refresh()
            path.write_text('OPENAI_API_KEY=first-test-value', encoding='utf-8')
            config.refresh()
            self.assertEqual(environ['OPENAI_API_KEY'], 'first-test-value')
            path.write_text('OPENAI_API_KEY=second-test-value-longer', encoding='utf-8')
            config.refresh()
            self.assertEqual(environ['OPENAI_API_KEY'], 'second-test-value-longer')
            path.unlink()
            config.refresh()
            self.assertNotIn('OPENAI_API_KEY', environ)

    def test_host_environment_takes_precedence(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            path.write_text('OPENAI_API_KEY=local-value', encoding='utf-8')
            environ = {'OPENAI_API_KEY': 'host-provided-value'}
            config = LocalConfig(path, environ)
            config.refresh()
            self.assertEqual(environ['OPENAI_API_KEY'], 'host-provided-value')

    def test_bom_quotes_export_and_empty_environment(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            path.write_text('export OPENAI_API_KEY="test-value"\nOPENAI_MODEL=gpt-4.1-mini # model\nIGNORED=value', encoding='utf-8-sig')
            environ = {'OPENAI_API_KEY': ''}
            LocalConfig(path, environ).refresh()
            self.assertEqual(environ['OPENAI_API_KEY'], 'test-value')
            self.assertEqual(environ['OPENAI_MODEL'], 'gpt-4.1-mini')
            self.assertNotIn('IGNORED', environ)
