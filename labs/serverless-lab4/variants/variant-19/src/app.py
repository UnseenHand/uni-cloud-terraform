import json
import os
import re
import uuid
from base64 import b64decode
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

TABLE_NAME = os.environ["TABLE_NAME"]
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")
table = dynamodb.Table(TABLE_NAME)
COUNT_ROUTE_PATTERN = re.compile(r"^/registrations/(?P<event_id>[^/]+)/count/?$")
REGISTER_ROUTE_PATTERN = re.compile(r"^/registrations/(?P<event_id>[^/]+)/?$")


def _response(status_code: int, payload: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload),
    }


def _parse_json_body(event: dict) -> dict:
    raw_body = event.get("body")
    if not raw_body:
        return {}

    if event.get("isBase64Encoded"):
        raw_body = b64decode(raw_body).decode("utf-8")

    return json.loads(raw_body)


def _validate_email(email: str | None) -> bool:
    return bool(email and "@" in email and "." in email)


def _register_participant(event_id: str, body: dict) -> dict:
    email = body.get("email")
    if not _validate_email(email):
        return _response(400, {"message": "Field 'email' is required and must be valid."})

    participant_id = str(body.get("participant_id") or uuid.uuid4())
    item = {
        "event_id": event_id,
        "participant_id": participant_id,
        "email": email,
        "name": body.get("name", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(event_id) AND attribute_not_exists(participant_id)",
        )
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f"Registration confirmed for event {event_id}",
            Message=(
                f"Participant {item['email']} has been registered for event {event_id}. "
                f"Registration ID: {participant_id}"
            ),
        )
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code == "ConditionalCheckFailedException":
            return _response(409, {"message": "Participant with this ID is already registered for this event."})
        print(f"AWS client error during registration: {exc}")
        return _response(500, {"message": "Internal Server Error"})

    return _response(201, {"message": "Created", "item": item})


def _get_participants_count(event_id: str) -> dict:
    try:
        result = table.query(
            KeyConditionExpression=Key("event_id").eq(event_id),
            Select="COUNT",
        )
    except ClientError as exc:
        print(f"AWS client error during count query: {exc}")
        return _response(500, {"message": "Internal Server Error"})

    return _response(200, {"count": result.get("Count", 0)})


def _resolve_route(event: dict) -> tuple[str | None, str | None]:
    request_context = event.get("requestContext") or {}
    http_context = request_context.get("http") or {}
    method = http_context.get("method") or request_context.get("httpMethod")
    raw_path = event.get("rawPath") or event.get("path") or ""

    count_match = COUNT_ROUTE_PATTERN.fullmatch(raw_path)
    if method == "GET" and count_match:
        return "count", count_match.group("event_id")

    register_match = REGISTER_ROUTE_PATTERN.fullmatch(raw_path)
    if method == "POST" and register_match:
        return "register", register_match.group("event_id")

    return None, None


def handler(event, context):
    action, event_id = _resolve_route(event)

    if not event_id:
        return _response(404, {"message": "Not Found"})

    try:
        if action == "register":
            body = _parse_json_body(event)
            return _register_participant(event_id, body)

        if action == "count":
            return _get_participants_count(event_id)

        return _response(404, {"message": "Not Found"})
    except json.JSONDecodeError:
        return _response(400, {"message": "Invalid JSON payload."})
    except Exception as exc:  # noqa: BLE001
        print(f"Unexpected error: {exc}")
        return _response(500, {"message": "Internal Server Error"})
