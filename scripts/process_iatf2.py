import csv
import json
import os
import sys

os.environ["TABLE_NAME"] = "gado"

from lmjm.post_diagnostico import lambda_handler as diagnostico_handler
from lmjm.post_inseminacao import lambda_handler as inseminacao_handler

CSV_PATH = os.path.join(os.path.dirname(__file__), "IATF2-07-01-2026.csv")
DATA_DIAGNOSTICO = "20260107"
DATA_INSEMINACAO = "20260118"


def build_event(brinco, body):
    return {"pathParameters": {"animal_id": brinco}, "body": json.dumps(body)}


def main():
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter=";")
        for row in reader:
            brinco = row[0].strip()
            resultado = row[1].strip() if len(row) > 1 else ""

            if not resultado:
                print(f"Brinco {brinco}: sem resultado, pulando")
                continue

            prenhe = resultado == "PC"

            event = build_event(brinco, {"data_diagnostico": DATA_DIAGNOSTICO, "prenhe": prenhe})
            resp = diagnostico_handler(event, None)
            print(f"Brinco {brinco}: diagnostico -> {resp['statusCode']}")

            if resultado == "IMPLANTE":
                semen = row[2].strip() if len(row) > 2 else ""
                event = build_event(brinco, {"data_inseminacao": DATA_INSEMINACAO, "semen": semen, "tags": "IA1-2025"})
                resp = inseminacao_handler(event, None)
                print(f"Brinco {brinco}: inseminacao -> {resp['statusCode']}")


if __name__ == "__main__":
    main()
