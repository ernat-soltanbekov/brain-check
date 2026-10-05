#!/usr/bin/env python3
"""Bounded HTTP stress test against YOUR local development server only."""

import argparse
import concurrent.futures
import json
import secrets
import time
import uuid
from urllib.parse import urlparse

import httpx

parser = argparse.ArgumentParser()
parser.add_argument("--base-url", default="http://127.0.0.1:8000")
parser.add_argument("--output")
args = parser.parse_args()
if urlparse(args.base_url).hostname not in {"127.0.0.1", "localhost", "::1"}:
    raise SystemExit("This script is intentionally restricted to localhost.")
base = args.base_url.rstrip("/") + "/api"
started = time.monotonic()
with httpx.Client(timeout=60) as client:
    auth = client.post(
        base + "/auth/register/",
        json={"username": "stress_" + secrets.token_hex(4), "password": secrets.token_urlsafe(24)},
    )
    auth.raise_for_status()
    headers = {"Authorization": "Token " + auth.json()["token"]}
    material = client.post(
        base + "/material/",
        headers=headers,
        json={
            "topic": "stress checks",
            "title": "Bounded concurrency",
            "content": "A request key identifies one logical operation. Reusing a request key must not duplicate a stored operation. Transactions commit all writes together.",
        },
    )
    material.raise_for_status()
    generated = client.post(
        base + "/quizzes/generate/",
        headers=headers,
        json={"topic": "stress checks", "count": 2, "types": ["multiple_choice"]},
    )
    generated.raise_for_status()
    quiz = generated.json()
    saved = client.patch(
        f"{base}/quizzes/{quiz['id']}/",
        headers=headers,
        json={"version": quiz["version"], "status": "published"},
    )
    saved.raise_for_status()
    payload = {
        "quizId": quiz["id"],
        "answers": [
            {"questionId": q["id"], "selectedAnswer": q["expected"], "timeSpent": 1}
            for q in quiz["questions"]
        ],
    }
    headers["Idempotency-Key"] = str(uuid.uuid4())

    def send(_):
        result = client.post(f"{base}/quizzes/{quiz['id']}/submit/", headers=headers, json=payload)
        return result.status_code, result.json()

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(send, range(24)))
    assert all(code in (200, 201) for code, _ in responses), responses
    ids = {result["id"] for _, result in responses}
    assert len(ids) == 1, "Duplicate attempts were created."
    history = client.get(base + "/profile/history/", headers=headers).json()
    assert history["totalAttempts"] == 1, history
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        reads = list(
            pool.map(
                lambda _: client.get(base + "/quizzes/", headers=headers).status_code, range(40)
            )
        )
    assert all(code == 200 for code in reads), reads
report = {
    "duplicateSubmissions": 24,
    "concurrentWorkers": 8,
    "uniqueAttempts": len(ids),
    "successfulConcurrentReads": 40,
    "serverErrors": 0,
    "seconds": round(time.monotonic() - started, 3),
}
print(json.dumps(report, indent=2))
if args.output:
    from pathlib import Path

    Path(args.output).write_text(json.dumps(report, indent=2) + "\n")
