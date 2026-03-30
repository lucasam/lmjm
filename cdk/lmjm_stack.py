from aws_cdk import Stack, aws_dynamodb as dynamodb, aws_lambda as _lambda
from constructs import Construct


class LmjmStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        _lambda.Function(
            self,
            "LmjmFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lmjm.handler.lambda_handler",
            code=_lambda.Code.from_asset("src"),
        )

        table = dynamodb.Table.from_table_name(self, "GadoTable", "gado")

        post_diagnostic = _lambda.Function(
            self,
            "PostDiagnosticFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lmjm.post_diagnostic.lambda_handler",
            code=_lambda.Code.from_asset("src"),
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(post_diagnostic)

        post_insemination = _lambda.Function(
            self,
            "PostInseminationFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lmjm.post_insemination.lambda_handler",
            code=_lambda.Code.from_asset("src"),
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(post_insemination)
