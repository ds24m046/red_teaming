import unittest
from httpx import Response

from red_teaming.gym.src.utils import id_from_location


class TestIdFromLocation(unittest.TestCase):

    def test_extract_id_from_absolute_url(self):
        response = Response(
            201,
            headers={"Location": "http://localhost:7070/agents/12345"},
        )

        self.assertEqual(id_from_location(response), "12345")

    def test_extract_id_with_trailing_slash(self):
        response = Response(
            201,
            headers={"Location": "/agents/12345/"},
        )

        self.assertEqual(id_from_location(response), "12345")

    def test_extract_id_from_nested_path(self):
        response = Response(
            201,
            headers={"Location": "/api/v1/agents/12345"},
        )

        self.assertEqual(id_from_location(response), "12345")

    def test_missing_location_header(self):
        response = Response(201)

        with self.assertRaises(KeyError):
            id_from_location(response)

    def test_empty_location_path(self):
        response = Response(
            201,
            headers={"Location": "/"},
        )

        with self.assertRaises(ValueError):
            id_from_location(response)


if __name__ == "__main__":
    unittest.main()
