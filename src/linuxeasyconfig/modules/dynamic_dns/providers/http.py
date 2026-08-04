from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


def request_json(
    *,
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    payload: Any = None,
    timeout: int = 30,
) -> Any:
    data = None

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    request_headers = {
        "Accept": "application/json",
        "User-Agent": "LinuxEasyConfig/1.0.0",
    }

    if headers:
        request_headers.update(headers)

    if data is not None:
        request_headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers=request_headers,
    )

    retryable_statuses = {
        429,
        500,
        502,
        503,
        504,
    }
    attempts = 4
    body = ""

    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(
                request,
                timeout=timeout,
            ) as response:
                body = response.read().decode(
                    "utf-8",
                    errors="replace",
                )
            break
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(
                "utf-8",
                errors="replace",
            )

            if (
                exc.code not in retryable_statuses
                or attempt == attempts - 1
            ):
                raise RuntimeError(
                    f"Provider API returned HTTP {exc.code}: "
                    f"{body or exc.reason}"
                ) from exc

            retry_after = exc.headers.get(
                "Retry-After",
                "",
            ).strip()

            try:
                delay = float(retry_after)
            except ValueError:
                delay = 2 ** attempt

            time.sleep(
                min(max(delay, 1.0), 30.0)
            )
        except urllib.error.URLError as exc:
            if attempt == attempts - 1:
                raise RuntimeError(
                    "Could not reach provider API: "
                    f"{exc.reason}"
                ) from exc

            time.sleep(2 ** attempt)

    if not body.strip():
        return None

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Provider API returned invalid JSON."
        ) from exc


def query_string(values: dict[str, str]) -> str:
    return urllib.parse.urlencode(values)
