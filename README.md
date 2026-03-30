
## CodeArtifact location
At project Universe we are using the amazon shared code artifact that needs to be referenced at deps.
CodeArtifact Domain: amazon
Account Owner: 149122183214

Login commands.
### pip
```
aws codeartifact login --tool pip --repository gbl-pypi --domain amazon --domain-owner 149122183214 --profile aws-project-universe-team+sourcecode-Backend --region us-west-2
```
### Twine
``` 
aws codeartifact login --tool twine --repository gbl-pypi --domain amazon --domain-owner 149122183214--profile aws-project-universe-team+sourcecode-Backend --region us-west-2
```

## Useful commands

```
# Run once to install dependencies after you create your virtualenv
./pu install

# Source code checks
./pu build

# Unit tests
./pu test

# Update your virtualenv when requirements.txt files are modified
./pu sync

# Compile requirements after you update requirements.in files
./pu compile-reqs
```

## DynamoDB table structure

Table name: gado
Hash Key: pk
Sort Key: sk

Index Name: ear_tag-sk-index
Hash Key: ear_tag

## DynamoDB record structure

sk: Animal
description: represents a single cattle animal
{
 "pk": "1fae9839-9c87-400a-ade9-358ceee85455",
 "sk": "Animal",
 "species": "cattle",
 "ear_tag": "6",
 "breed": "Nelore",
 "sex": "F",
 "birth_date": "2018-01-01",
 "mother": "",
 "batch": "3",
 "status": "Active",
 "pregnant": true,
 "implanted": false,
 "inseminated": false,
 "lactating": false,
 "transferred": false,
 "notes": [
  "2025-08-16: Pregnancy Confirmed. Invictus. EDD: 03-11-2025"
 ],
 "tags": [
  "IA2-2024"
 ]
}

sk: Insemination|YYYYMMDD
description: represents an insemination event for a cattle animal
{
 "pk": "1fae9839-9c87-400a-ade9-358ceee85455",
 "sk": "Insemination|20250114",
 "insemination_date": "2025-01-14",
 "semen": "Invictus"
}

sk: Diagnostic|YYYYMMDD
description: represents a pregnancy diagnostic for a cattle animal
{
 "pk": "1fae9839-9c87-400a-ade9-358ceee85455",
 "sk": "Diagnostic|20250816",
 "breeding_date": "2025-01-12",
 "diagnostic_date": "2025-08-16",
 "pregnant": true,
 "expected_delivery_date": "2025-11-03",
 "semen": "Invictus"
}

sk: PigAnimal
description: represents a single pig animal
{
 "pk": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
 "sk": "PigAnimal",
 "species": "pigs",
 "ear_tag": "P01",
 "breed": "Large White",
 "sex": "F",
 "birth_date": "2024-03-15",
 "mother": "",
 "batch": "1",
 "status": "Active",
 "current_weight": "120",
 "last_weight_date": "2025-03-01",
 "notes": [],
 "tags": []
}

sk: Breeding|YYYYMMDD
description: represents a breeding event for a pig
{
 "pk": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
 "sk": "Breeding|20250301",
 "breeding_date": "2025-03-01",
 "sire": "Boar-Alpha",
 "breeding_type": "Natural"
}

sk: Weighing|YYYYMMDD
description: represents a weight measurement for a pig
{
 "pk": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
 "sk": "Weighing|20250301",
 "weighing_date": "2025-03-01",
 "weight": "120"
}