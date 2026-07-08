#!/usr/bin/env python3
"""One-off script to batch-add pig mortalities via the prod API.

Reads the authorization header from the AUTH_TOKEN environment variable so the
secret is never written to disk. Usage:

    AUTH_TOKEN="Bearer eyJ..." python scripts/batch_add_mortalities.py
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

ENDPOINT = (
    "https://nr80rppekj.execute-api.sa-east-1.amazonaws.com/prod/pigs/batches/"
    "a067b5e3-4fe4-498f-b1af-adbd8124cf0d/mortalities"
)

DEATH_REASONS = {
    "0": "Subita",
    "9": "Artrite",
    "11": "Diarréia",
    "13": "Pneumonia",
    "19": "Ulcera",
    "22": "Ruptura de Hérnia",
    "28": "Briga",
    "32": "Refugagem:Artrite",
    "35": "Refugagem:Pneumonia",
}

SEX = {"M": "Male", "F": "Female"}

# date (DD/MM/YYYY); sex; death_reason code
RAW_DATA = """
01/06/2026;F;22
01/06/2026;M;35
01/06/2026;M;19
02/06/2026;F;13
03/06/2026;M;9
04/06/2026;M;13
05/06/2026;F;0
05/06/2026;M;0
07/06/2026;M;32
09/06/2026;F;19
09/06/2026;F;13
15/06/2026;M;32
15/06/2026;F;19
17/06/2026;M;28
17/06/2026;M;0
17/06/2026;F;0
17/06/2026;M;0
17/06/2026;M;0
26/06/2026;M;13
26/06/2026;M;11
28/06/2026;M;13
29/06/2026;M;19
30/06/2026;F;0
30/06/2026;M;13
"""


def build_payloads() -> list[dict]:
    payloads = []
    for line in RAW_DATA.strip().splitlines():
        date_str, sex_code, reason_code = [p.strip() for p in line.split(";")]
        day, month, year = date_str.split("/")
        mortality_date = f"{year}{month}{day}"  # YYYYMMDD
        if reason_code not in DEATH_REASONS:
            raise ValueError(f"Unknown death_reason code: {reason_code}")
        if sex_code not in SEX:
            raise ValueError(f"Unknown sex code: {sex_code}")
        payloads.append(
            {
                "mortality_date": mortality_date,
                "sex": SEX[sex_code],
                "origin": "1",
                "death_reason": reason_code,
                "death_reason_description": DEATH_REASONS[reason_code],
                "reported_by": "Lucas Machado",
            }
        )
    return payloads


def post(payload: dict, auth: str) -> tuple[int, str]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(ENDPOINT, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", auth)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


def main() -> int:
    auth = os.environ.get("AUTH_TOKEN")
    payloads = build_payloads()

    if "--dry-run" in sys.argv or not auth:
        if not auth:
            print("AUTH_TOKEN not set -- dry run only.\n")
        for i, p in enumerate(payloads, 1):
            print(f"{i:2d}. {json.dumps(p, ensure_ascii=False)}")
        print(f"\nTotal: {len(payloads)} records")
        return 0 if auth else 1

    ok, failed = 0, 0
    for i, p in enumerate(payloads, 1):
        status, body = post(p, auth)
        label = f"{p['mortality_date']} {p['sex']:6s} {p['death_reason_description']}"
        if 200 <= status < 300:
            ok += 1
            print(f"[{i:2d}/{len(payloads)}] OK  {status}  {label}")
        else:
            failed += 1
            print(f"[{i:2d}/{len(payloads)}] ERR {status}  {label}  -> {body}")
        time.sleep(0.2)

    print(f"\nDone. {ok} succeeded, {failed} failed.")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
