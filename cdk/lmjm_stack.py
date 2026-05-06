import subprocess

import aws_cdk as cdk
import jsii
from aws_cdk import (
    BundlingOptions,
    CfnOutput,
    Duration,
    SecretValue,
    Stack,
)
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_route53_targets as targets
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_deployment as s3deploy
from aws_cdk import aws_ses as ses
from aws_cdk import aws_ses_actions as ses_actions
from aws_cdk import aws_ssm as ssm
from constructs import Construct


@jsii.implements(cdk.ILocalBundling)
class _BundleLambdaCode:
    """Local bundling: pip install runtime deps + copy source into the output directory."""

    def try_bundle(self, output_dir: str, *, image: cdk.DockerImage) -> bool:
        subprocess.check_call(["pip", "install", "-r", "src/requirements.txt", "-t", output_dir, "--quiet"])
        subprocess.check_call(["cp", "-r", "src/lmjm", f"{output_dir}/lmjm"])
        # Remove type-stub packages not needed at runtime
        for pkg in [
            "mypy_boto3_dynamodb",
            "mypy_boto3_lambda",
            "boto3_stubs",
            "botocore_stubs",
            "types_awscrt",
            "types_s3transfer",
            "mypy_extensions",
        ]:
            subprocess.call(["rm", "-rf", f"{output_dir}/{pkg}"])
        return True


class LmjmStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Shared Lambda code asset with runtime dependencies bundled
        lambda_code = _lambda.Code.from_asset(
            "src",
            bundling=BundlingOptions(
                image=_lambda.Runtime.PYTHON_3_12.bundling_image,
                command=[
                    "bash",
                    "-c",
                    "pip install -r requirements.txt -t /asset-output"
                    " && cp -r . /asset-output/"
                    " && find /asset-output -name '*.pyc' -delete"
                    " && rm -rf /asset-output/mypy_boto3_dynamodb /asset-output/mypy_boto3_lambda"
                    " /asset-output/boto3_stubs /asset-output/botocore_stubs"
                    " /asset-output/types_awscrt /asset-output/types_s3transfer"
                    " /asset-output/mypy_extensions",
                ],
                local=_BundleLambdaCode(),
            ),
        )

        _lambda.Function(
            self,
            "LmjmFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.handler.lambda_handler",
            code=lambda_code,
        )

        table = dynamodb.Table(
            self,
            "LmjmTable",
            table_name="lmjm",
            partition_key=dynamodb.Attribute(name="pk", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="sk", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
        )
        table.add_global_secondary_index(
            index_name="ear_tag-sk-index",
            partition_key=dynamodb.Attribute(name="ear_tag", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="sk", type=dynamodb.AttributeType.STRING),
        )

        # --- S3 + CloudFront for frontend hosting ---

        frontend_bucket = s3.Bucket(
            self,
            "FrontendBucket",
            bucket_name=f"lmjm-frontend-{Stack.of(self).account}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        # Custom domain: app.lmjm.net
        custom_domain = "app.lmjm.net"

        hosted_zone = route53.HostedZone.from_hosted_zone_attributes(
            self,
            "LmjmHostedZone",
            hosted_zone_id="Z07927451E0NMAX1HPNFR",
            zone_name="lmjm.net",
        )

        # ACM certificate must be in us-east-1 for CloudFront
        certificate = acm.DnsValidatedCertificate(
            self,
            "AppCertificate",
            domain_name=custom_domain,
            hosted_zone=hosted_zone,
            region="us-east-1",
        )

        distribution = cloudfront.Distribution(
            self,
            "FrontendDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(frontend_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            domain_names=[custom_domain],
            certificate=certificate,
            default_root_object="index.html",
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),
                ),
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),
                ),
            ],
        )

        # DNS A record pointing app.lmjm.net → CloudFront
        route53.ARecord(
            self,
            "AppAliasRecord",
            zone=hosted_zone,
            record_name="app",
            target=route53.RecordTarget.from_alias(targets.CloudFrontTarget(distribution)),
        )

        s3deploy.BucketDeployment(
            self,
            "FrontendDeployment",
            sources=[s3deploy.Source.asset("frontend/dist")],
            destination_bucket=frontend_bucket,
            distribution=distribution,
            prune=False,
        )

        CfnOutput(
            self,
            "CloudFrontDomainName",
            value=distribution.distribution_domain_name,
            description="CloudFront distribution domain name for the frontend",
        )

        # --- Cognito User Pool with Google IdP ---

        pre_signup_lambda = _lambda.Function(
            self,
            "PreSignupFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.pre_signup.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_data(pre_signup_lambda)

        user_pool = cognito.UserPool(
            self,
            "LmjmUserPool",
            self_sign_up_enabled=False,
            lambda_triggers=cognito.UserPoolTriggers(
                pre_sign_up=pre_signup_lambda,
            ),
        )

        google_client_id = ssm.StringParameter.value_for_string_parameter(self, "/lmjm/google-oauth/client-id")
        google_client_secret_value = ssm.StringParameter.value_for_string_parameter(
            self, "/lmjm/google-oauth/client-secret"
        )

        google_idp = cognito.UserPoolIdentityProviderGoogle(
            self,
            "GoogleIdP",
            user_pool=user_pool,
            client_id=google_client_id,
            client_secret_value=SecretValue.unsafe_plain_text(google_client_secret_value),
            scopes=["openid", "email", "profile"],
            attribute_mapping=cognito.AttributeMapping(
                email=cognito.ProviderAttribute.GOOGLE_EMAIL,
                fullname=cognito.ProviderAttribute.GOOGLE_NAME,
            ),
        )

        user_pool_client = cognito.UserPoolClient(
            self,
            "LmjmUserPoolClient",
            user_pool=user_pool,
            generate_secret=False,
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(authorization_code_grant=True),
                scopes=[
                    cognito.OAuthScope.OPENID,
                    cognito.OAuthScope.EMAIL,
                    cognito.OAuthScope.PROFILE,
                ],
                callback_urls=[f"https://{custom_domain}/callback"],
                logout_urls=[f"https://{custom_domain}"],
            ),
            supported_identity_providers=[
                cognito.UserPoolClientIdentityProvider.GOOGLE,
            ],
            auth_flows=cognito.AuthFlow(user_srp=True),
            refresh_token_validity=Duration.days(30),
        )
        user_pool_client.node.add_dependency(google_idp)

        user_pool_domain = cognito.UserPoolDomain(
            self,
            "LmjmUserPoolDomain",
            user_pool=user_pool,
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix="lmjm",
            ),
        )

        CfnOutput(
            self,
            "UserPoolId",
            value=user_pool.user_pool_id,
            description="Cognito User Pool ID",
        )

        CfnOutput(
            self,
            "UserPoolClientId",
            value=user_pool_client.user_pool_client_id,
            description="Cognito User Pool Client ID",
        )

        CfnOutput(
            self,
            "UserPoolDomain",
            value=user_pool_domain.domain_name,
            description="Cognito User Pool Domain",
        )

        post_diagnostic = _lambda.Function(
            self,
            "PostDiagnosticFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.post_diagnostic.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(post_diagnostic)

        post_insemination = _lambda.Function(
            self,
            "PostInseminationFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.post_insemination.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(post_insemination)

        # --- API Gateway REST API with Cognito Authorizer ---

        cloudfront_origin = f"https://{custom_domain}"

        api = apigw.RestApi(
            self,
            "LmjmApi",
            rest_api_name="LMJM API",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=[cloudfront_origin],
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization"],
            ),
        )

        cfn_authorizer = apigw.CfnAuthorizer(
            self,
            "LmjmCognitoAuthorizer",
            name="LmjmCognitoAuthorizer",
            rest_api_id=api.rest_api_id,
            type="COGNITO_USER_POOLS",
            identity_source="method.request.header.Authorization",
            provider_arns=[user_pool.user_pool_arn],
        )

        # Add CORS headers to gateway error responses (authorizer rejections don't go through Lambda)
        for response_type in [
            apigw.ResponseType.UNAUTHORIZED,
            apigw.ResponseType.ACCESS_DENIED,
            apigw.ResponseType.DEFAULT_4_XX,
        ]:
            api.add_gateway_response(
                f"GatewayResponse{response_type.response_type}",
                type=response_type,
                response_headers={
                    "Access-Control-Allow-Origin": f"'{cloudfront_origin}'",
                    "Access-Control-Allow-Headers": "'Content-Type,Authorization'",
                    "Access-Control-Allow-Methods": "'GET,POST,PUT,DELETE,OPTIONS'",
                },
            )

        # Create top-level resources for cattle and pig routes
        cattle_resource = api.root.add_resource("cattle")
        pigs_resource = api.root.add_resource("pigs")

        def add_cognito_method(
            resource: apigw.Resource,
            http_method: str,
            integration: apigw.LambdaIntegration,
        ) -> apigw.Method:
            """Add a method with CfnAuthorizer-based Cognito auth via property overrides."""
            method = resource.add_method(http_method, integration)
            method_resource = method.node.find_child("Resource")
            method_resource.add_property_override("AuthorizationType", "COGNITO_USER_POOLS")
            method_resource.add_property_override("AuthorizerId", {"Ref": cfn_authorizer.logical_id})
            return method

        # --- Cattle GET Lambdas ---

        get_cattle_animals = _lambda.Function(
            self,
            "GetCattleAnimalsLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.get_cattle_animals.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_data(get_cattle_animals)

        get_cattle_animal = _lambda.Function(
            self,
            "GetCattleAnimalLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.get_cattle_animal.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_data(get_cattle_animal)

        get_inseminations = _lambda.Function(
            self,
            "GetInseminationsLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.get_inseminations.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_data(get_inseminations)

        get_diagnostics_lambda = _lambda.Function(
            self,
            "GetDiagnosticsLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.get_diagnostics.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_data(get_diagnostics_lambda)

        # --- Cattle Weight Lambdas ---

        get_weights = _lambda.Function(
            self,
            "GetWeightsLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.get_weights.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_data(get_weights)

        post_weight = _lambda.Function(
            self,
            "PostWeightLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.post_weight.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(post_weight)

        # --- Cattle API Gateway Routes ---

        # /cattle/animals
        cattle_animals_resource = cattle_resource.add_resource("animals")
        add_cognito_method(cattle_animals_resource, "GET", apigw.LambdaIntegration(get_cattle_animals))

        # /cattle/animals/{animal_id}
        cattle_animal_resource = cattle_animals_resource.add_resource("{animal_id}")
        add_cognito_method(cattle_animal_resource, "GET", apigw.LambdaIntegration(get_cattle_animal))

        # /cattle/animals/{animal_id}/inseminations
        cattle_inseminations_resource = cattle_animal_resource.add_resource("inseminations")
        add_cognito_method(cattle_inseminations_resource, "GET", apigw.LambdaIntegration(get_inseminations))
        add_cognito_method(cattle_inseminations_resource, "POST", apigw.LambdaIntegration(post_insemination))

        # /cattle/animals/{animal_id}/diagnostics
        cattle_diagnostics_resource = cattle_animal_resource.add_resource("diagnostics")
        add_cognito_method(cattle_diagnostics_resource, "GET", apigw.LambdaIntegration(get_diagnostics_lambda))
        add_cognito_method(cattle_diagnostics_resource, "POST", apigw.LambdaIntegration(post_diagnostic))

        # /cattle/animals/{animal_id}/pesos
        cattle_pesos_resource = cattle_animal_resource.add_resource("pesos")
        add_cognito_method(cattle_pesos_resource, "GET", apigw.LambdaIntegration(get_weights))
        add_cognito_method(cattle_pesos_resource, "POST", apigw.LambdaIntegration(post_weight))

        # --- Cattle Procedure Lambdas ---

        post_procedure = _lambda.Function(
            self,
            "PostProcedureLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.post_procedure.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(post_procedure)

        get_procedures = _lambda.Function(
            self,
            "GetProceduresLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.get_procedures.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_data(get_procedures)

        get_procedure = _lambda.Function(
            self,
            "GetProcedureLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.get_procedure.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_data(get_procedure)

        post_procedure_action = _lambda.Function(
            self,
            "PostProcedureActionLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.post_procedure_action.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(post_procedure_action)

        delete_procedure_action = _lambda.Function(
            self,
            "DeleteProcedureActionLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.delete_procedure_action.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(delete_procedure_action)

        post_procedure_confirm = _lambda.Function(
            self,
            "PostProcedureConfirmLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(60),
            memory_size=2048,
            handler="lmjm.post_procedure_confirm.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(post_procedure_confirm)

        post_procedure_cancel = _lambda.Function(
            self,
            "PostProcedureCancelLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.post_procedure_cancel.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(post_procedure_cancel)

        # --- Cattle Procedure API Gateway Routes ---

        # /cattle/procedures
        cattle_procedures_resource = cattle_resource.add_resource("procedures")
        add_cognito_method(cattle_procedures_resource, "POST", apigw.LambdaIntegration(post_procedure))
        add_cognito_method(cattle_procedures_resource, "GET", apigw.LambdaIntegration(get_procedures))

        # /cattle/procedures/{procedure_id}
        cattle_procedure_resource = cattle_procedures_resource.add_resource("{procedure_id}")
        add_cognito_method(cattle_procedure_resource, "GET", apigw.LambdaIntegration(get_procedure))

        # /cattle/procedures/{procedure_id}/actions
        cattle_procedure_actions_resource = cattle_procedure_resource.add_resource("actions")
        add_cognito_method(cattle_procedure_actions_resource, "POST", apigw.LambdaIntegration(post_procedure_action))

        # /cattle/procedures/{procedure_id}/actions/{action_sk}
        cattle_procedure_action_resource = cattle_procedure_actions_resource.add_resource("{action_sk}")
        add_cognito_method(cattle_procedure_action_resource, "DELETE", apigw.LambdaIntegration(delete_procedure_action))

        # /cattle/procedures/{procedure_id}/confirm
        cattle_procedure_confirm_resource = cattle_procedure_resource.add_resource("confirm")
        add_cognito_method(cattle_procedure_confirm_resource, "POST", apigw.LambdaIntegration(post_procedure_confirm))

        # /cattle/procedures/{procedure_id}/cancel
        cattle_procedure_cancel_resource = cattle_procedure_resource.add_resource("cancel")
        add_cognito_method(cattle_procedure_cancel_resource, "POST", apigw.LambdaIntegration(post_procedure_cancel))

        # --- Pig Module Lambdas ---

        get_modules = _lambda.Function(
            self,
            "GetModulesLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.get_modules.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_data(get_modules)

        get_module = _lambda.Function(
            self,
            "GetModuleLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.get_module.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_data(get_module)

        put_module = _lambda.Function(
            self,
            "PutModuleLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.put_module.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(put_module)

        # --- Pig Batch Lambdas ---

        get_batches = _lambda.Function(
            self,
            "GetBatchesLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.get_batches.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_data(get_batches)

        get_batch = _lambda.Function(
            self,
            "GetBatchLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.get_batch.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_data(get_batch)

        post_batch = _lambda.Function(
            self,
            "PostBatchLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.post_batch.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(post_batch)

        put_batch = _lambda.Function(
            self,
            "PutBatchLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.put_batch.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(put_batch)

        # --- Pig Feed Lambdas ---

        post_feed_truck_arrival = _lambda.Function(
            self,
            "PostFeedTruckArrivalLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.post_feed_truck_arrival.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(post_feed_truck_arrival)

        get_feed_truck_arrivals = _lambda.Function(
            self,
            "GetFeedTruckArrivalsLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.get_feed_truck_arrivals.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_data(get_feed_truck_arrivals)

        get_feed_schedule = _lambda.Function(
            self,
            "GetFeedScheduleLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.get_feed_schedule.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_data(get_feed_schedule)

        put_feed_schedule = _lambda.Function(
            self,
            "PutFeedScheduleLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.put_feed_schedule.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(put_feed_schedule)

        # --- Pig Truck Arrival Lambdas ---

        post_pig_truck_arrival = _lambda.Function(
            self,
            "PostPigTruckArrivalLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.post_pig_truck_arrival.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(post_pig_truck_arrival)

        get_pig_truck_arrivals = _lambda.Function(
            self,
            "GetPigTruckArrivalsLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.get_pig_truck_arrivals.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_data(get_pig_truck_arrivals)

        put_pig_truck_arrival = _lambda.Function(
            self,
            "PutPigTruckArrivalLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.put_pig_truck_arrival.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(put_pig_truck_arrival)

        # --- Batch Start Summary Lambda ---

        post_batch_start_summary = _lambda.Function(
            self,
            "PostBatchStartSummaryLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.post_batch_start_summary.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(post_batch_start_summary)

        # --- Mortality Lambdas ---

        post_mortality = _lambda.Function(
            self,
            "PostMortalityLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.post_mortality.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(post_mortality)

        get_mortalities = _lambda.Function(
            self,
            "GetMortalitiesLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.get_mortalities.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_data(get_mortalities)

        # --- Medication Lambdas ---

        post_medication = _lambda.Function(
            self,
            "PostMedicationLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.post_medication.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(post_medication)

        get_medications = _lambda.Function(
            self,
            "GetMedicationsLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.get_medications.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_data(get_medications)

        post_medication_shot = _lambda.Function(
            self,
            "PostMedicationShotLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.post_medication_shot.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(post_medication_shot)

        get_medication_shots = _lambda.Function(
            self,
            "GetMedicationShotsLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.get_medication_shots.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_data(get_medication_shots)

        # --- Feed Consumption Plan Lambdas ---

        put_feed_consumption_plan = _lambda.Function(
            self,
            "PutFeedConsumptionPlanLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.put_feed_consumption_plan.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(put_feed_consumption_plan)

        get_feed_consumption_plan = _lambda.Function(
            self,
            "GetFeedConsumptionPlanLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.get_feed_consumption_plan.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_data(get_feed_consumption_plan)

        # --- Feed Consumption Template Lambdas ---

        get_feed_consumption_templates = _lambda.Function(
            self,
            "GetFeedConsumptionTemplatesLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.get_feed_consumption_templates.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_data(get_feed_consumption_templates)

        post_feed_consumption_template = _lambda.Function(
            self,
            "PostFeedConsumptionTemplateLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.post_feed_consumption_template.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(post_feed_consumption_template)

        # --- Generate Feed Plan Lambda ---

        post_generate_feed_plan = _lambda.Function(
            self,
            "PostGenerateFeedPlanLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.post_generate_feed_plan.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(post_generate_feed_plan)

        # --- Feed Schedule Suggestions Lambda ---

        post_feed_schedule_suggestions = _lambda.Function(
            self,
            "PostFeedScheduleSuggestionsLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(90),
            memory_size=2048,
            handler="lmjm.post_feed_schedule_suggestions.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_data(post_feed_schedule_suggestions)
        post_feed_schedule_suggestions.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=["*"],
            )
        )

        # --- Feed Balance Lambdas ---

        post_feed_balance = _lambda.Function(
            self,
            "PostFeedBalanceLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.post_feed_balance.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(post_feed_balance)

        get_feed_balances = _lambda.Function(
            self,
            "GetFeedBalancesLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.get_feed_balances.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_data(get_feed_balances)

        delete_feed_balance = _lambda.Function(
            self,
            "DeleteFeedBalanceLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.delete_feed_balance.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(delete_feed_balance)

        # --- Batch Financial Result Lambdas ---

        post_batch_financial_result = _lambda.Function(
            self,
            "PostBatchFinancialResultLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.post_batch_financial_result.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(post_batch_financial_result)

        get_batch_financial_results = _lambda.Function(
            self,
            "GetBatchFinancialResultsLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.get_batch_financial_results.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_data(get_batch_financial_results)

        # --- Integrator Weekly Data Lambdas ---

        post_integrator_weekly_data = _lambda.Function(
            self,
            "PostIntegratorWeeklyDataLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.post_integrator_weekly_data.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(post_integrator_weekly_data)

        get_integrator_weekly_data = _lambda.Function(
            self,
            "GetIntegratorWeeklyDataLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.get_integrator_weekly_data.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_data(get_integrator_weekly_data)

        # --- Fiscal Email Intake ---

        fiscal_email_bucket = s3.Bucket(
            self,
            "FiscalEmailBucket",
            bucket_name=f"lmjm-fiscal-emails-{Stack.of(self).account}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            lifecycle_rules=[s3.LifecycleRule(expiration=Duration.days(90))],
        )

        process_fiscal_email = _lambda.Function(
            self,
            "ProcessFiscalEmailLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(60),
            memory_size=2048,
            handler="lmjm.process_fiscal_email.lambda_handler",
            code=lambda_code,
            environment={
                "TABLE_NAME": table.table_name,
                "EMAIL_BUCKET": fiscal_email_bucket.bucket_name,
            },
        )
        table.grant_read_write_data(process_fiscal_email)
        fiscal_email_bucket.grant_read(process_fiscal_email)

        receipt_rule_set = ses.ReceiptRuleSet(self, "FiscalEmailRuleSet")
        receipt_rule_set.add_rule(
            "FiscalEmailRule",
            recipients=["fiscal@lmjm.net"],
            actions=[
                ses_actions.S3(bucket=fiscal_email_bucket),
                ses_actions.Lambda(function=process_fiscal_email),
            ],
        )

        route53.MxRecord(
            self,
            "FiscalMxRecord",
            zone=hosted_zone,
            values=[route53.MxRecordValue(host_name="inbound-smtp.sa-east-1.amazonaws.com", priority=10)],
        )

        # --- Fiscal Document API Lambdas ---

        get_fiscal_documents = _lambda.Function(
            self,
            "GetFiscalDocumentsLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.get_fiscal_documents.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_data(get_fiscal_documents)

        get_feed_schedule_fiscal_documents = _lambda.Function(
            self,
            "GetFeedScheduleFiscalDocsLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.get_feed_schedule_fiscal_documents.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_data(get_feed_schedule_fiscal_documents)

        get_raw_material_types = _lambda.Function(
            self,
            "GetRawMaterialTypesLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.get_raw_material_types.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_data(get_raw_material_types)

        post_raw_material_type = _lambda.Function(
            self,
            "PostRawMaterialTypeLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.post_raw_material_type.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_write_data(post_raw_material_type)

        # --- Pig API Gateway Routes ---

        # /pigs/modules
        modules_resource = pigs_resource.add_resource("modules")
        add_cognito_method(modules_resource, "GET", apigw.LambdaIntegration(get_modules))

        # /pigs/modules/{module_id}
        module_resource = modules_resource.add_resource("{module_id}")
        add_cognito_method(module_resource, "GET", apigw.LambdaIntegration(get_module))
        add_cognito_method(module_resource, "PUT", apigw.LambdaIntegration(put_module))

        # /pigs/batches
        batches_resource = pigs_resource.add_resource("batches")
        add_cognito_method(batches_resource, "GET", apigw.LambdaIntegration(get_batches))
        add_cognito_method(batches_resource, "POST", apigw.LambdaIntegration(post_batch))

        # /pigs/batches/{batch_id}
        batch_resource = batches_resource.add_resource("{batch_id}")
        add_cognito_method(batch_resource, "GET", apigw.LambdaIntegration(get_batch))
        add_cognito_method(batch_resource, "PUT", apigw.LambdaIntegration(put_batch))

        # /pigs/batches/{batch_id}/feed-truck-arrivals
        feed_truck_arrivals_resource = batch_resource.add_resource("feed-truck-arrivals")
        add_cognito_method(feed_truck_arrivals_resource, "POST", apigw.LambdaIntegration(post_feed_truck_arrival))
        add_cognito_method(feed_truck_arrivals_resource, "GET", apigw.LambdaIntegration(get_feed_truck_arrivals))

        # /pigs/batches/{batch_id}/feed-schedule
        feed_schedule_resource = batch_resource.add_resource("feed-schedule")
        add_cognito_method(feed_schedule_resource, "GET", apigw.LambdaIntegration(get_feed_schedule))
        add_cognito_method(feed_schedule_resource, "PUT", apigw.LambdaIntegration(put_feed_schedule))

        # /pigs/batches/{batch_id}/pig-truck-arrivals
        pig_truck_arrivals_resource = batch_resource.add_resource("pig-truck-arrivals")
        add_cognito_method(pig_truck_arrivals_resource, "POST", apigw.LambdaIntegration(post_pig_truck_arrival))
        add_cognito_method(pig_truck_arrivals_resource, "GET", apigw.LambdaIntegration(get_pig_truck_arrivals))

        # /pigs/batches/{batch_id}/pig-truck-arrivals/{arrival_sk}
        pig_truck_arrival_resource = pig_truck_arrivals_resource.add_resource("{arrival_sk}")
        add_cognito_method(pig_truck_arrival_resource, "PUT", apigw.LambdaIntegration(put_pig_truck_arrival))

        # /pigs/batches/{batch_id}/start-summary
        start_summary_resource = batch_resource.add_resource("start-summary")
        add_cognito_method(start_summary_resource, "POST", apigw.LambdaIntegration(post_batch_start_summary))

        # /pigs/batches/{batch_id}/mortalities
        mortalities_resource = batch_resource.add_resource("mortalities")
        add_cognito_method(mortalities_resource, "POST", apigw.LambdaIntegration(post_mortality))
        add_cognito_method(mortalities_resource, "GET", apigw.LambdaIntegration(get_mortalities))

        # /pigs/batches/{batch_id}/medications
        medications_resource = batch_resource.add_resource("medications")
        add_cognito_method(medications_resource, "POST", apigw.LambdaIntegration(post_medication))
        add_cognito_method(medications_resource, "GET", apigw.LambdaIntegration(get_medications))

        # /pigs/batches/{batch_id}/medication-shots
        medication_shots_resource = batch_resource.add_resource("medication-shots")
        add_cognito_method(medication_shots_resource, "POST", apigw.LambdaIntegration(post_medication_shot))
        add_cognito_method(medication_shots_resource, "GET", apigw.LambdaIntegration(get_medication_shots))

        # /pigs/batches/{batch_id}/feed-consumption-plan
        feed_consumption_plan_resource = batch_resource.add_resource("feed-consumption-plan")
        add_cognito_method(feed_consumption_plan_resource, "PUT", apigw.LambdaIntegration(put_feed_consumption_plan))
        add_cognito_method(feed_consumption_plan_resource, "GET", apigw.LambdaIntegration(get_feed_consumption_plan))

        # /pigs/batches/{batch_id}/generate-feed-plan
        generate_feed_plan_resource = batch_resource.add_resource("generate-feed-plan")
        add_cognito_method(generate_feed_plan_resource, "POST", apigw.LambdaIntegration(post_generate_feed_plan))

        # /pigs/batches/{batch_id}/feed-schedule-suggestions
        feed_schedule_suggestions_resource = batch_resource.add_resource("feed-schedule-suggestions")
        add_cognito_method(
            feed_schedule_suggestions_resource, "POST", apigw.LambdaIntegration(post_feed_schedule_suggestions)
        )

        # /pigs/batches/{batch_id}/feed-balances
        feed_balances_resource = batch_resource.add_resource("feed-balances")
        add_cognito_method(feed_balances_resource, "POST", apigw.LambdaIntegration(post_feed_balance))
        add_cognito_method(feed_balances_resource, "GET", apigw.LambdaIntegration(get_feed_balances))

        # /pigs/batches/{batch_id}/feed-balances/{balance_sk}
        feed_balance_resource = feed_balances_resource.add_resource("{balance_sk}")
        add_cognito_method(feed_balance_resource, "DELETE", apigw.LambdaIntegration(delete_feed_balance))

        # /pigs/batches/{batch_id}/financial-results
        financial_results_resource = batch_resource.add_resource("financial-results")
        add_cognito_method(financial_results_resource, "POST", apigw.LambdaIntegration(post_batch_financial_result))
        add_cognito_method(financial_results_resource, "GET", apigw.LambdaIntegration(get_batch_financial_results))

        # /pigs/batches/{batch_id}/fiscal-documents
        fiscal_documents_resource = batch_resource.add_resource("fiscal-documents")
        add_cognito_method(fiscal_documents_resource, "GET", apigw.LambdaIntegration(get_fiscal_documents))

        # /pigs/batches/{batch_id}/feed-schedule-fiscal-documents
        feed_schedule_fiscal_documents_resource = batch_resource.add_resource("feed-schedule-fiscal-documents")
        add_cognito_method(
            feed_schedule_fiscal_documents_resource, "GET", apigw.LambdaIntegration(get_feed_schedule_fiscal_documents)
        )

        # /pigs/integrator-weekly-data
        integrator_weekly_data_resource = pigs_resource.add_resource("integrator-weekly-data")
        add_cognito_method(
            integrator_weekly_data_resource, "POST", apigw.LambdaIntegration(post_integrator_weekly_data)
        )
        add_cognito_method(integrator_weekly_data_resource, "GET", apigw.LambdaIntegration(get_integrator_weekly_data))

        # /pigs/feed-consumption-templates
        feed_consumption_templates_resource = pigs_resource.add_resource("feed-consumption-templates")
        add_cognito_method(
            feed_consumption_templates_resource, "GET", apigw.LambdaIntegration(get_feed_consumption_templates)
        )
        add_cognito_method(
            feed_consumption_templates_resource, "POST", apigw.LambdaIntegration(post_feed_consumption_template)
        )

        # /raw-material-types (top-level, not under pigs)
        raw_material_types_resource = api.root.add_resource("raw-material-types")
        add_cognito_method(raw_material_types_resource, "GET", apigw.LambdaIntegration(get_raw_material_types))
        add_cognito_method(raw_material_types_resource, "POST", apigw.LambdaIntegration(post_raw_material_type))

        # --- All Fiscal Documents + Reprocess ---

        get_all_fiscal_documents = _lambda.Function(
            self,
            "GetAllFiscalDocumentsLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.get_all_fiscal_documents.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name},
        )
        table.grant_read_data(get_all_fiscal_documents)

        reprocess_fiscal_document = _lambda.Function(
            self,
            "ReprocessFiscalDocumentLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),
            memory_size=2048,
            handler="lmjm.reprocess_fiscal_document.lambda_handler",
            code=lambda_code,
            environment={"TABLE_NAME": table.table_name, "EMAIL_BUCKET": fiscal_email_bucket.bucket_name},
        )
        table.grant_read_write_data(reprocess_fiscal_document)

        # /fiscal-documents (top-level)
        all_fiscal_documents_resource = api.root.add_resource("fiscal-documents")
        add_cognito_method(all_fiscal_documents_resource, "GET", apigw.LambdaIntegration(get_all_fiscal_documents))

        # /fiscal-documents/reprocess
        reprocess_resource = all_fiscal_documents_resource.add_resource("reprocess")
        add_cognito_method(reprocess_resource, "POST", apigw.LambdaIntegration(reprocess_fiscal_document))

        CfnOutput(
            self,
            "ApiGatewayUrl",
            value=api.url,
            description="API Gateway REST API URL",
        )

        # --- Runtime config.json for frontend (Cognito + API values resolved at deploy time) ---

        cognito_hosted_ui_url = f"https://{user_pool_domain.domain_name}.auth.{self.region}.amazoncognito.com"
        cloudfront_url = f"https://{custom_domain}"

        s3deploy.BucketDeployment(
            self,
            "FrontendConfigDeployment",
            sources=[
                s3deploy.Source.json_data(
                    "config.json",
                    {
                        "cognitoDomain": cognito_hosted_ui_url,
                        "cognitoClientId": user_pool_client.user_pool_client_id,
                        "redirectUri": f"{cloudfront_url}/callback",
                        "apiUrl": api.url,
                    },
                )
            ],
            destination_bucket=frontend_bucket,
            distribution=distribution,
            distribution_paths=["/config.json"],
            prune=False,
        )
