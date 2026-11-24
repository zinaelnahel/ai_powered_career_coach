import tempfile
import unittest
from pathlib import Path
from autopilot.storage import Ledger

class StorageTests(unittest.TestCase):
    def test_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.sqlite"
            job = dict(id="1",url="https://example.org/job",title="Developer",score=80)
            ledger = Ledger(path)
            ledger.ingest([job,job])
            ledger.close()
            ledger = Ledger(path)
            self.assertEqual(len(ledger.pending()),1)
            ledger.close()
