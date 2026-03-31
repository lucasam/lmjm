from aws_cdk import Stack, Stage
from aws_cdk import aws_codebuild as codebuild
from aws_cdk import pipelines
from constructs import Construct

from cdk.lmjm_stack import LmjmStack


class LmjmPipelineStage(Stage):
    """Deploy stage that provisions the LmjmStack."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        super().__init__(scope, construct_id, **kwargs)
        LmjmStack(self, "LmjmStack")


class PipelineStack(Stack):
    """Self-mutating CDK Pipeline that builds, tests, and deploys the LMJM application."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        super().__init__(scope, construct_id, **kwargs)

        # GitHub source via CodeStar Connections
        source = pipelines.CodePipelineSource.connection(
            repo_string="OWNER/REPO",
            branch="main",
            connection_arn="arn:aws:codeconnections:sa-east-1:123456789012:connection/PLACEHOLDER-CONNECTION-ID",
        )

        # Synth step: backend build + frontend build + cdk synth
        synth_step = pipelines.ShellStep(
            "Synth",
            input=source,
            install_commands=[
                "pip install -r requirements.txt",
                "cd frontend && npm ci && cd ..",
            ],
            commands=[
                "tox",
                "cd frontend && npm run build && cd ..",
                "npx cdk synth",
            ],
        )

        pipeline = pipelines.CodePipeline(
            self,
            "LmjmPipeline",
            pipeline_name="LmjmPipeline",
            synth=synth_step,
            self_mutation=True,
            code_build_defaults=pipelines.CodeBuildOptions(
                build_environment=codebuild.BuildEnvironment(
                    build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                    compute_type=codebuild.ComputeType.MEDIUM,
                ),
            ),
        )

        # Deploy stage
        pipeline.add_stage(LmjmPipelineStage(self, "Deploy"))
