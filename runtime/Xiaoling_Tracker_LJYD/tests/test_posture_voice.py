import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pc'))
from posture_link import PostureLink
from esp_transport import ESPTransport


class PostureVoiceTests(unittest.TestCase):
    def test_no_command_without_known_device_boot(self):
        link = PostureLink('http://device:81', ESPTransport())
        link.action('posture_on', {})
        link.report('alert', {})
        self.assertTrue(link.queue.empty())

    def test_commands_target_observed_boot(self):
        link = PostureLink('http://device:81', ESPTransport())
        link.action('posture_calibrate', {'boot_id': 4})
        path, payload, _ = link.queue.get_nowait()
        self.assertEqual(path, '/api/posture')
        self.assertEqual(payload, {'action': 'posture_calibrate', 'boot_id': 4})

    def test_reports_have_distinct_deduplication_ids(self):
        link = PostureLink('http://device:81', ESPTransport())
        for _ in range(2):
            link.report('alert', {'boot_id': 8})
        first, second = [link.queue.get_nowait()[1] for _ in range(2)]
        self.assertEqual(first['boot_id'], 8)
        self.assertEqual(len(first['event_id']), 32)
        self.assertNotEqual(first['event_id'], second['event_id'])


if __name__ == '__main__':
    unittest.main()
