import aws_cdk as cdk

from cdk.lmjm_stack import LmjmStack
from cdk.pipeline_stack import PipelineStack

app = cdk.App()
LmjmStack(app, "LmjmStack")
PipelineStack(app, "PipelineStack")
app.synth()
