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
comprehend = boto3.client("comprehend")
table = dynamodb.Table(TABLE_NAME)
COUNT_ROUTE_PATTERN = re.compile(r"^/registrations/(?P<event_id>[^/]+)/count/?$")
LANGUAGE_ROUTE_PATTERN = re.compile(r"^/registrations/(?P<event_id>[^/]+)/lang/?$")
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


def _build_registration_text(body: dict) -> str:
    parts = [
        str(body.get("name", "")).strip(),
        str(body.get("email", "")).strip(),
        str(body.get("note", "")).strip(),
    ]
    return " ".join(part for part in parts if part)


def _detect_dominant_language(text: str) -> tuple[str | None, list[dict], str | None]:
    normalized_text = text.strip()
    if not normalized_text:
        return None, [], "No text to analyze."

    try:
        response = comprehend.detect_dominant_language(Text=normalized_text[:5000])
    except ClientError as exc:
        print(f"Comprehend detect_dominant_language failed: {exc}")
        return None, [], "Comprehend request failed."

    languages = response.get("Languages", [])
    dominant_language = languages[0].get("LanguageCode") if languages else None
    return dominant_language, languages, None


def _serialize_languages_for_storage(languages: list[dict]) -> list[dict]:
    serialized = []
    for language in languages:
        language_code = language.get("LanguageCode")
        if not language_code:
            continue

        score = language.get("Score")
        serialized.append(
            {
                "language_code": str(language_code),
                "score": f"{float(score):.6f}" if score is not None else "0.000000",
            }
        )
    return serialized


def _build_notification_message(
    event_id: str,
    participant_email: str,
    participant_id: str,
    language_code: str | None,
) -> tuple[str, str]:
    if language_code == "uk":
        subject = f"Підтвердження реєстрації на подію {event_id}"
        message = (
            f"Учасника {participant_email} успішно зареєстровано на подію {event_id}. "
            f"Ідентифікатор реєстрації: {participant_id}."
        )
        return subject, message

    subject = f"Registration confirmed for event {event_id}"
    message = (
        f"Participant {participant_email} has been registered for event {event_id}. "
        f"Registration ID: {participant_id}."
    )
    return subject, message


def _query_event_items(event_id: str) -> list[dict]:
    items = []
    query_kwargs: dict = {"KeyConditionExpression": Key("event_id").eq(event_id)}

    while True:
        result = table.query(**query_kwargs)
        items.extend(result.get("Items", []))
        last_evaluated_key = result.get("LastEvaluatedKey")
        if not last_evaluated_key:
            break
        query_kwargs["ExclusiveStartKey"] = last_evaluated_key

    return items


def _registration_items(event_id: str) -> list[dict]:
    items = _query_event_items(event_id)
    return [item for item in items if item.get("record_type", "registration") == "registration"]


def _register_participant(event_id: str, body: dict) -> dict:
    email = body.get("email")
    if not _validate_email(email):
        return _response(400, {"message": "Field 'email' is required and must be valid."})

    language_text = _build_registration_text(body)
    dominant_language, languages, language_error = _detect_dominant_language(language_text)
    participant_id = str(body.get("participant_id") or uuid.uuid4())
    item = {
        "event_id": event_id,
        "participant_id": participant_id,
        "record_type": "registration",
        "email": email,
        "name": body.get("name", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "detected_language": dominant_language or "unknown",
        "language_candidates": _serialize_languages_for_storage(languages[:3]),
    }
    if language_error:
        item["language_error"] = language_error

    subject, message = _build_notification_message(event_id, item["email"], participant_id, dominant_language)

    try:
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(event_id) AND attribute_not_exists(participant_id)",
        )
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=message,
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
        registrations = _registration_items(event_id)
    except ClientError as exc:
        print(f"AWS client error during count query: {exc}")
        return _response(500, {"message": "Internal Server Error"})

    return _response(200, {"count": len(registrations)})


def _analyze_registration_language(event_id: str) -> dict:
    try:
        registrations = _registration_items(event_id)
    except ClientError as exc:
        print(f"AWS client error during language query: {exc}")
        return _response(500, {"message": "Internal Server Error"})

    if not registrations:
        return _response(404, {"message": "No registrations found for this id."})

    text_parts = []
    for item in registrations:
        name = str(item.get("name", "")).strip()
        email = str(item.get("email", "")).strip()
        participant_text = " ".join(part for part in [name, email] if part)
        if participant_text:
            text_parts.append(participant_text)

    analysis_text = " ".join(text_parts).strip()
    dominant_language, languages, language_error = _detect_dominant_language(analysis_text)
    analysis_record_id = f"ai-analysis-{uuid.uuid4().hex}"

    analysis_item = {
        "event_id": event_id,
        "participant_id": analysis_record_id,
        "record_type": "ai_analysis",
        "analysis_type": "detect_dominant_language",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_registrations_count": len(registrations),
        "text_sample": analysis_text[:250],
        "detected_language": dominant_language or "unknown",
        "language_candidates": _serialize_languages_for_storage(languages[:5]),
    }
    if language_error:
        analysis_item["language_error"] = language_error

    persistence_error = None
    try:
        table.put_item(Item=analysis_item)
    except ClientError as exc:
        persistence_error = str(exc)
        print(f"AWS client error during AI analysis persistence: {exc}")

    payload = {
        "event_id": event_id,
        "source_registrations_count": len(registrations),
        "detected_language": dominant_language or "unknown",
        "language_candidates": languages[:5],
        "analysis_record_id": analysis_record_id if not persistence_error else None,
        "analysis_status": "ok" if not language_error else "degraded",
    }
    if language_error:
        payload["warning"] = language_error
    if persistence_error:
        payload["persistence_warning"] = "Analysis computed but could not be saved."

    return _response(200, payload)


def _resolve_route(event: dict) -> tuple[str | None, str | None]:
    request_context = event.get("requestContext") or {}
    http_context = request_context.get("http") or {}
    method = http_context.get("method") or request_context.get("httpMethod")
    raw_path = event.get("rawPath") or event.get("path") or ""

    count_match = COUNT_ROUTE_PATTERN.fullmatch(raw_path)
    if method == "GET" and count_match:
        return "count", count_match.group("event_id")

    language_match = LANGUAGE_ROUTE_PATTERN.fullmatch(raw_path)
    if method == "GET" and language_match:
        return "language", language_match.group("event_id")

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

        if action == "language":
            return _analyze_registration_language(event_id)

        return _response(404, {"message": "Not Found"})
    except json.JSONDecodeError:
        return _response(400, {"message": "Invalid JSON payload."})
    except Exception as exc:  # noqa: BLE001
        print(f"Unexpected error: {exc}")
        return _response(500, {"message": "Internal Server Error"})
