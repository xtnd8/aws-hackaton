"""CDK Stack that deploys an Amazon Bedrock Agent with a simple action group."""

import json
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_bedrock as bedrock,
)
from constructs import Construct


# OpenAPI schema describing the agent's action group API
ACTION_GROUP_SCHEMA = {
    "openapi": "3.0.0",
    "info": {
        "title": "Greeting API",
        "version": "1.0.0",
        "description": "A simple greeting action group for the Bedrock Agent.",
    },
    "paths": {
        "/greet": {
            "get": {
                "summary": "Greet a user by name",
                "description": "Returns a personalized greeting message for the given name.",
                "operationId": "greetUser",
                "parameters": [
                    {
                        "name": "name",
                        "in": "path",
                        "description": "The name of the person to greet",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Successful greeting",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "message": {
                                            "type": "string",
                                            "description": "The greeting message",
                                        }
                                    },
                                }
                            }
                        },
                    }
                },
            }
        }
    },
}


class BedrockAgentStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # --- IAM Role for the Bedrock Agent ---
        agent_role = iam.Role(
            self,
            "BedrockAgentRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description="Role assumed by the Bedrock Agent",
        )

        # Allow the agent to invoke the foundation model (via inference profile)
        agent_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                    "bedrock:GetInferenceProfile",
                    "bedrock:GetFoundationModel",
                ],
                resources=["*"],
            )
        )

        # --- Lambda for the Action Group ---
        action_lambda = _lambda.Function(
            self,
            "ActionGroupLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="action_group.handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=cdk.Duration.seconds(30),
        )

        # Allow Bedrock to invoke the Lambda
        action_lambda.add_permission(
            "AllowBedrockInvoke",
            principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
            action="lambda:InvokeFunction",
        )

        # Ensure the IAM policy is fully propagated before creating the agent
        agent_policy = agent_role.node.find_child("DefaultPolicy")

        # --- Bedrock Agent ---
        agent = bedrock.CfnAgent(
            self,
            "BedrockAgent",
            agent_name="SimpleGreetingAgent",
            agent_resource_role_arn=agent_role.role_arn,
            foundation_model="eu.anthropic.claude-sonnet-4-5-20250929-v1:0",
            instruction=(
                "You are a friendly greeting assistant. When a user asks to be greeted "
                "or says hello, use the greet action to respond with a personalized greeting. "
                "Always ask for the user's name if they haven't provided one."
            ),
            idle_session_ttl_in_seconds=600,
            action_groups=[
                bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="GreetingActions",
                    action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=action_lambda.function_arn,
                    ),
                    api_schema=bedrock.CfnAgent.APISchemaProperty(
                        payload=json.dumps(ACTION_GROUP_SCHEMA),
                    ),
                    description="Actions for greeting users",
                )
            ],
            auto_prepare=True,
        )

        # Explicit dependency: agent must wait for IAM policy
        agent.node.add_dependency(agent_policy)

        # --- Outputs ---
        cdk.CfnOutput(self, "AgentId", value=agent.attr_agent_id)
        cdk.CfnOutput(self, "AgentName", value="SimpleGreetingAgent")
        cdk.CfnOutput(self, "LambdaFunctionName", value=action_lambda.function_name)
