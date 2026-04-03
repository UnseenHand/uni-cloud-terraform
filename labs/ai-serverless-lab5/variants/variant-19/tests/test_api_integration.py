import json
import os
import unittest
import urllib.error
import urllib.request
import uuid


def _api_request(method: str, path: str, payload: dict | None = None, raw_body: str | None = None):
    base_url = os.environ["API_URL"].rstrip("/")
    url = f"{base_url}{path}"

    if raw_body is not None:
        body_bytes = raw_body.encode("utf-8")
    elif payload is not None:
        body_bytes = json.dumps(payload).encode("utf-8")
    else:
        body_bytes = None

    request = urllib.request.Request(
        url=url,
        data=body_bytes,
        method=method,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            status_code = response.getcode()
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        status_code = error.code
        body = error.read().decode("utf-8")

    parsed = json.loads(body) if body else {}
    return status_code, parsed


class TestRegistrationsApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.environ.get("API_URL"):
            raise unittest.SkipTest("API_URL environment variable is required for integration tests.")

    def setUp(self):
        self.event_id = f"itest-{uuid.uuid4().hex}"

    def test_register_two_participants_and_get_count(self):
        status, first_response = _api_request(
            "POST",
            f"/registrations/{self.event_id}",
            payload={"email": "first@example.com", "name": "First User"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(first_response.get("message"), "Created")

        status, second_response = _api_request(
            "POST",
            f"/registrations/{self.event_id}",
            payload={"email": "second@example.com", "name": "Second User"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(second_response.get("message"), "Created")

        status, count_response = _api_request("GET", f"/registrations/{self.event_id}/count")
        self.assertEqual(status, 200)
        self.assertEqual(count_response.get("count"), 2)

    def test_duplicate_participant_id_returns_conflict(self):
        participant_id = f"participant-{uuid.uuid4().hex}"
        request_payload = {
            "participant_id": participant_id,
            "email": "dup@example.com",
            "name": "Duplicate Test",
        }

        status, _ = _api_request("POST", f"/registrations/{self.event_id}", payload=request_payload)
        self.assertEqual(status, 201)

        status, response = _api_request("POST", f"/registrations/{self.event_id}", payload=request_payload)
        self.assertEqual(status, 409)
        self.assertIn("already registered", response.get("message", ""))

    def test_invalid_email_returns_bad_request(self):
        status, response = _api_request(
            "POST",
            f"/registrations/{self.event_id}",
            payload={"email": "not-an-email", "name": "Invalid Email"},
        )
        self.assertEqual(status, 400)
        self.assertIn("email", response.get("message", ""))

    def test_invalid_json_returns_bad_request(self):
        status, response = _api_request(
            "POST",
            f"/registrations/{self.event_id}",
            raw_body='{"email":"broken@example.com",',
        )
        self.assertEqual(status, 400)
        self.assertEqual(response.get("message"), "Invalid JSON payload.")

    def test_language_analysis_endpoint_and_count_consistency(self):
        status, _ = _api_request(
            "POST",
            f"/registrations/{self.event_id}",
            payload={"email": "one@example.com", "name": "Оксана Коваленко"},
        )
        self.assertEqual(status, 201)

        status, _ = _api_request(
            "POST",
            f"/registrations/{self.event_id}",
            payload={"email": "two@example.com", "name": "Taras Melnyk"},
        )
        self.assertEqual(status, 201)

        status, language_response = _api_request("GET", f"/registrations/{self.event_id}/lang")
        self.assertEqual(status, 200)
        self.assertEqual(language_response.get("event_id"), self.event_id)
        self.assertIn("detected_language", language_response)
        self.assertGreaterEqual(language_response.get("source_registrations_count", 0), 2)

        status, count_response = _api_request("GET", f"/registrations/{self.event_id}/count")
        self.assertEqual(status, 200)
        self.assertEqual(count_response.get("count"), 2)

    def test_language_analysis_returns_not_found_for_unknown_registration_group(self):
        status, response = _api_request("GET", f"/registrations/{self.event_id}/lang")
        self.assertEqual(status, 404)
        self.assertIn("No registrations found", response.get("message", ""))


if __name__ == "__main__":
    unittest.main()
