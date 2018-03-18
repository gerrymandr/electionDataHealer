import unittest
from downloadRawFiles import DownloadDirectoryListing

class TestDownloads(unittest.TestCase):
    def test_directory_listing_url(self):
        ddl = DownloadDirectoryListing('ShapeFiles/VTD')
        self.assertEqual(ddl.url(),
                         'https://dl.ncsbe.gov/?prefix=ShapeFiles/VTD')

    def test_user_agent(self):
        ddl = DownloadDirectoryListing('ShapeFiles/VTD')
        self.assertTrue(ddl.USER_AGENT.startswith('Moz'))
