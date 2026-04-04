"""Migrate all data from gado table (Portuguese) to lmjm table (English).

Source table: gado (profile: lucasam+appsec-test-Admin)
Destination table: lmjm (env credentials)
Region: sa-east-1

Field mapping:
  Animal:
    brinco        → ear_tag
    raca          → breed
    sexo          → sex
    nascimento    → birth_date
    mae           → mother
    lote          → batch
    situacao      → status
    prenhe        → pregnant
    implantada    → implanted
    inseminada    → inseminated
    lactante      → lactating
    transferida   → transferred
    anotacoes     → notes
    tags          → tags
    + species = "cattle"

  Inseminacao → Insemination:
    sk: Inseminacao|YYYYMMDD → Insemination|YYYYMMDD
    data_inseminacao → insemination_date
    semen → semen

  Diagnostico → Diagnostic:
    sk: Diagnostico|YYYYMMDD → Diagnostic|YYYYMMDD
    data_diagnostico → diagnostic_date
    prenhe → pregnant
    data_cobertura → breeding_date
    previsao_parto → expected_delivery_date
    semen → semen

  Peso → Weight (Peso| sk prefix preserved):
    sk: Peso|YYYYMMDD (unchanged)
    peso → weight_kg
    data_pesagem → weighing_date

Usage:
    python scripts/migrate_gado_to_lmjm.py
"""

from decimal import Decimal

import boto3

REGION = "sa-east-1"
SOURCE_TABLE = "gado"
DEST_TABLE = "lmjm"

# Both tables use environment credentials, both in sa-east-1
session = boto3.Session(region_name=REGION)
source_table = session.resource("dynamodb").Table(SOURCE_TABLE)
dest_table = session.resource("dynamodb").Table(DEST_TABLE)


def scan_all(table):
    """Scan all items from a DynamoDB table with pagination."""
    items = []
    response = table.scan()
    items.extend(response["Items"])
    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response["Items"])
    return items


def to_str(val):
    """Convert DynamoDB value to string, handling None/NULL."""
    if val is None or (isinstance(val, dict) and val.get("NULL")):
        return None
    if isinstance(val, str):
        return val if val else None
    return str(val)


def to_bool(val):
    """Convert DynamoDB value to bool, handling None."""
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    return None


def to_list(val):
    """Convert DynamoDB list to Python list of strings."""
    if val is None or (isinstance(val, dict) and val.get("NULL")):
        return None
    if isinstance(val, list):
        result = [str(v) for v in val if v is not None]
        return result if result else None
    return None


def migrate_animal(item):
    """Convert a gado Animal record to lmjm Animal format."""
    migrated = {
        "pk": item["pk"],
        "sk": "Animal",
        "species": "cattle",
        "ear_tag": to_str(item.get("brinco")),
        "breed": to_str(item.get("raca")),
        "sex": to_str(item.get("sexo")),
        "birth_date": to_str(item.get("nascimento")),
        "mother": to_str(item.get("mae")),
        "batch": to_str(item.get("lote")),
        "status": to_str(item.get("situacao")),
        "pregnant": to_bool(item.get("prenhe")),
        "implanted": to_bool(item.get("implantada")),
        "inseminated": to_bool(item.get("inseminada")),
        "lactating": to_bool(item.get("lactante")),
        "transferred": to_bool(item.get("transferida")),
        "notes": to_list(item.get("anotacoes")),
        "tags": to_list(item.get("tags")),
    }
    # Remove None values (skip_none_values pattern)
    return {k: v for k, v in migrated.items() if v is not None}


def migrate_insemination(item):
    """Convert a gado Inseminacao record to lmjm Insemination format."""
    old_sk = item["sk"]  # Inseminacao|YYYYMMDD
    date_part = old_sk.split("|")[1]
    return {
        "pk": item["pk"],
        "sk": f"Insemination|{date_part}",
        "insemination_date": to_str(item.get("data_inseminacao")) or "",
        "semen": to_str(item.get("semen")) or "",
    }


def migrate_diagnostic(item):
    """Convert a gado Diagnostico record to lmjm Diagnostic format."""
    old_sk = item["sk"]  # Diagnostico|YYYYMMDD
    date_part = old_sk.split("|")[1]
    migrated = {
        "pk": item["pk"],
        "sk": f"Diagnostic|{date_part}",
        "diagnostic_date": to_str(item.get("data_diagnostico")) or "",
        "pregnant": to_bool(item.get("prenhe")) or False,
        "breeding_date": to_str(item.get("data_cobertura")),
        "expected_delivery_date": to_str(item.get("previsao_parto")),
        "semen": to_str(item.get("semen")),
    }
    return {k: v for k, v in migrated.items() if v is not None}


def migrate_weight(item):
    """Convert a gado Peso record to lmjm Weight format (sk prefix preserved)."""
    peso_val = item.get("peso", 0)
    if isinstance(peso_val, Decimal):
        peso_val = int(peso_val)
    return {
        "pk": item["pk"],
        "sk": item["sk"],  # Peso|YYYYMMDD — preserved
        "weight_kg": peso_val,
        "weighing_date": to_str(item.get("data_pesagem")) or "",
    }


def main():
    print(f"Scanning source table '{SOURCE_TABLE}'...")
    all_items = scan_all(source_table)
    print(f"  Total records: {len(all_items)}")

    animals = []
    inseminations = []
    diagnostics = []
    weights = []
    skipped = []

    for item in all_items:
        sk = item.get("sk", "")
        if sk == "Animal":
            animals.append(migrate_animal(item))
        elif sk.startswith("Inseminacao|"):
            inseminations.append(migrate_insemination(item))
        elif sk.startswith("Diagnostico|"):
            diagnostics.append(migrate_diagnostic(item))
        elif sk.startswith("Peso|"):
            weights.append(migrate_weight(item))
        else:
            skipped.append(sk)

    print(f"\nMigration summary:")
    print(f"  Animals:       {len(animals)}")
    print(f"  Inseminations: {len(inseminations)}")
    print(f"  Diagnostics:   {len(diagnostics)}")
    print(f"  Weights:       {len(weights)}")
    print(f"  Skipped:       {len(skipped)}")

    if skipped:
        unique_skipped = set(skipped[:10])
        print(f"  Skipped sk samples: {unique_skipped}")

    total = len(animals) + len(inseminations) + len(diagnostics) + len(weights)
    print(f"\nWriting {total} records to '{DEST_TABLE}'...")

    with dest_table.batch_writer() as batch:
        for item in animals:
            batch.put_item(Item=item)
        for item in inseminations:
            batch.put_item(Item=item)
        for item in diagnostics:
            batch.put_item(Item=item)
        for item in weights:
            batch.put_item(Item=item)

    print(f"Migration complete. {total} records written to '{DEST_TABLE}'.")


if __name__ == "__main__":
    main()
