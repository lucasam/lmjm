from datetime import date, datetime

import boto3
import openpyxl

dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table("gado")

STATUS_MAP = {
    "prenhe": "Prenhe",
    "implantada": "Implantada",
    "inseminada": "Inseminada",
    "lactante": "Lactante",
    "transferida": "Transferida",
}


def get_situacao(item):
    situacoes = []
    for attr, label in STATUS_MAP.items():
        if item.get(attr):
            situacoes.append(label)
            return label
    return " e ".join(situacoes)


def get_idade_meses(nascimento):
    if not nascimento:
        return ""
    nasc = datetime.strptime(nascimento, "%Y-%m-%d").date()
    today = date.today()
    return (today.year - nasc.year) * 12 + today.month - nasc.month


def scan_animals():
    items = []
    scan_kwargs = {
        "FilterExpression": "sk = :sk AND situacao = :situacao",
        "ExpressionAttributeValues": {":sk": "Animal", ":situacao": "Ativa"},
    }
    while True:
        response = table.scan(**scan_kwargs)
        items.extend(response["Items"])
        if "LastEvaluatedKey" not in response:
            break
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
    return items


def main():
    animals = scan_animals()
    animals.sort(key=lambda x: x.get("brinco", ""))

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Animais"
    ws.append(["Brinco", "Situação", "Anotações", "Tags", "Última Tag", "Idade (meses)"])

    for item in animals:
        brinco_raw = item.get("brinco", "")
        try:
            brinco = int(brinco_raw)
        except (ValueError, TypeError):
            brinco = brinco_raw
        situacao = get_situacao(item)
        anotacoes = "\n".join(item.get("anotacoes") or [])
        tags = "\n".join(item.get("tags") or [])
        ultima_tag = (item.get("tags") or [""])[-1]
        idade = get_idade_meses(item.get("nascimento"))

        ws.append([brinco, situacao, anotacoes, tags, ultima_tag, idade])

    ws.auto_filter.ref = ws.dimensions

    column_widths = {"A": 10, "B": 15, "C": 60, "D": 25, "E": 20, "F": 15}
    for col, width in column_widths.items():
        ws.column_dimensions[col].width = width

    output = "/Users/lucasam/Code/lmjm/scripts/animais.xlsx"
    wb.save(output)
    print(f"Arquivo salvo em {output}")


if __name__ == "__main__":
    main()
