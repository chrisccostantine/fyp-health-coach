import os
import sys

import requests


def main() -> int:
    backend_url = os.environ.get("BACKEND_URL", "").strip().rstrip("/")
    cron_secret = os.environ.get("NUDGE_CRON_SECRET", "").strip()

    if not backend_url:
        print("Missing BACKEND_URL environment variable.", file=sys.stderr)
        return 1
    if not cron_secret:
        print("Missing NUDGE_CRON_SECRET environment variable.", file=sys.stderr)
        return 1

    url = f"{backend_url}/nudge/run-scheduled"
    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {cron_secret}"},
        timeout=30,
    )

    print(f"POST {url} -> {response.status_code}")
    try:
        print(response.json())
    except ValueError:
        print(response.text)

    return 0 if response.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
