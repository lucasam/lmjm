import os

import aws_cdk as cdk

from cdk.lmjm_stack import LmjmStack
from cdk.pipeline_stack import PipelineStack

app = cdk.App()

env = cdk.Environment(
    account="155959776700",
    region="sa-east-1",
)

LmjmStack(app, "LmjmStack", env=env)
PipelineStack(app, "PipelineStack", env=env)
app.synth()
