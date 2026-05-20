#!/usr/bin/env python3
import aws_cdk as cdk
from stack import BedrockAgentStack

app = cdk.App()
BedrockAgentStack(app, "BedrockAgentStack")
app.synth()
