import unittest
from httpx import Response

from red_teaming.gym.src.session.utils import id_from_location


class TestIdFromLocation(unittest.TestCase):

    def test_extract_id(self):
        response = Response(
            status_code=201,
            headers={
                "Location": "http://localhost:7070/agents/12345"
            },
        )

        self.assertEqual(id_from_location(response), "12345")

    def test_extract_id_with_trailing_slash(self):
        
        response = Response(
            status_code=201,
            headers={
                "Location": "http://localhost:7070/agents/12345/"
            },
        )

        self.assertEqual(id_from_location(response), "12345")

    def test_extract_id_with_nested_path(self):
        
        response = Response(
            status_code=201,
            headers={
                "Location": "/api/v1/agents/12345"
            },
        )

        self.assertEqual(id_from_location(response), "12345")

    def test_missing_location_header(self):
        
        response = Response(status_code=201)

        with self.assertRaises(KeyError):
            id_from_location(response)

    def test_root_location(self):
        
        response = Response(
            status_code=201,
            headers={"Location": "/"},
        )

        self.assertEqual(id_from_location(response), "")


if __name__ == "__main__":
    unittest.main()