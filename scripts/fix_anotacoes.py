import boto3

dynamodb = boto3.resource("dynamodb", region_name="sa-east-1")
table = dynamodb.Table("gado")


def flatten(value):
    result = []
    for item in value:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(str(item))
    return result


def main():
    scan_kwargs = {
        "FilterExpression": "sk = :sk",
        "ExpressionAttributeValues": {":sk": "Animal"},
    }

    while True:
        response = table.scan(**scan_kwargs)
        for item in response["Items"]:
            pk = item["pk"]
            anotacoes = item.get("anotacoes")
            if anotacoes is None:
                continue

            flattened = flatten(anotacoes)
            if flattened != anotacoes:
                print(f"Fixing brinco={item.get('brinco', '?')} pk={pk}")
                table.update_item(
                    Key={"pk": pk, "sk": "Animal"},
                    UpdateExpression="SET anotacoes = :a",
                    ExpressionAttributeValues={":a": flattened},
                )

        if "LastEvaluatedKey" not in response:
            break
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    print("Done")


if __name__ == "__main__":
    main()
