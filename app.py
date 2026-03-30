import aws_cdk as cdk

from cdk.lmjm_stack import LmjmStack

app = cdk.App()
LmjmStack(app, "LmjmStack")
app.synth()
