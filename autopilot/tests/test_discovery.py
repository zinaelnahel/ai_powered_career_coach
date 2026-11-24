import unittest
from unittest.mock import patch
from autopilot.discovery import rank, run

class DiscoveryTests(unittest.TestCase):
    def test_rank(self):
        self.assertEqual(rank({"title":"Python Developer","description":"Python SQL"}, ["Python Developer"], ["Python","SQL"]), 100)

    @patch("autopilot.discovery.fetch")
    def test_filter_and_deduplicate(self, fetch):
        item = {"id":1,"title":"Python Developer","absolute_url":"https://example.org/job","location":{"name":"Berlin"},"content":"Python"}
        fetch.return_value = {"jobs":[item,item]}
        result = run({"roles":["Python Developer"],"skills":["Python"],"locations":["Berlin"],"greenhouse_boards":["example"]})
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["status"],"review_required")
        self.assertNotIn("description",result[0])
