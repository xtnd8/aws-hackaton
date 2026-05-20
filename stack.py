"""CDK Stack: Bedrock Agent for cyclomatic complexity analysis + UI Lambda."""

import json
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_bedrock as bedrock,
)
from constructs import Construct


# OpenAPI schema for the complexity analysis action group
ACTION_GROUP_SCHEMA = {
    "openapi": "3.0.0",
    "info": {
        "title": "Cyclomatic Complexity API",
        "version": "1.0.0",
        "description": "Analyze cyclomatic complexity of code snippets and GitHub repositories.",
    },
    "paths": {
        "/analyze-snippet": {
            "post": {
                "summary": "Analyze cyclomatic complexity of a code snippet",
                "description": "Computes McCabe's cyclomatic complexity for the provided source code.",
                "operationId": "analyzeSnippet",
                "parameters": [
                    {
                        "name": "code",
                        "in": "query",
                        "description": "The source code to analyze",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Complexity analysis result",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "complexity": {"type": "integer"},
                                        "rating": {"type": "string"},
                                        "details": {"type": "string"},
                                    },
                                }
                            }
                        },
                    }
                },
            }
        },
        "/analyze-repo": {
            "post": {
                "summary": "Analyze cyclomatic complexity of a GitHub repository",
                "description": "Fetches all Python files from a public GitHub repo and computes complexity for each.",
                "operationId": "analyzeRepo",
                "parameters": [
                    {
                        "name": "repo_url",
                        "in": "query",
                        "description": "The GitHub repository URL (e.g. https://github.com/owner/repo)",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Repository complexity report",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "repo": {"type": "string"},
                                        "files_analyzed": {"type": "integer"},
                                        "total_complexity": {"type": "integer"},
                                        "average_complexity": {"type": "number"},
                                        "per_file_results": {"type": "array"},
                                    },
                                }
                            }
                        },
                    }
                },
            }
        },
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

        # --- Action Group Lambda ---
        action_lambda = _lambda.Function(
            self,
            "ActionGroupLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="action_group.handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=cdk.Duration.seconds(120),
            memory_size=256,
        )

        action_lambda.add_permission(
            "AllowBedrockInvoke",
            principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
            action="lambda:InvokeFunction",
        )

        # Ensure IAM policy propagates before agent creation
        agent_policy = agent_role.node.find_child("DefaultPolicy")

        # --- Bedrock Agent ---
        agent = bedrock.CfnAgent(
            self,
            "BedrockAgent",
            agent_name="AVDV-cyclomatic-complexity-agent",
            agent_resource_role_arn=agent_role.role_arn,
            foundation_model="eu.anthropic.claude-sonnet-4-5-20250929-v1:0",
            instruction=(
                "You are a cyclomatic complexity analysis assistant. You help users understand "
                "and improve their code quality by analyzing cyclomatic complexity.\n\n"
                "When a user provides a code snippet, use the analyzeSnippet action to compute its complexity.\n"
                "When a user provides a GitHub repository URL, use the analyzeRepo action to analyze all Python files.\n\n"
                "After receiving results, provide:\n"
                "1. A clear summary of the complexity scores\n"
                "2. An explanation of what the scores mean\n"
                "3. Specific suggestions for reducing complexity if scores are high (>10)\n\n"
                "You can also answer general questions about cyclomatic complexity, code quality metrics, "
                "and software engineering best practices."
            ),
            idle_session_ttl_in_seconds=600,
            action_groups=[
                bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="ComplexityAnalysis",
                    action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=action_lambda.function_arn,
                    ),
                    api_schema=bedrock.CfnAgent.APISchemaProperty(
                        payload=json.dumps(ACTION_GROUP_SCHEMA),
                    ),
                    description="Actions for analyzing cyclomatic complexity of code and repos",
                )
            ],
            auto_prepare=True,
        )

        agent.node.add_dependency(agent_policy)

        # --- UI Lambda with Function URL ---
        ui_lambda = _lambda.Function(
            self,
            "UILambda",
            function_name="AVDV-complexity-ui",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="ui_handler.handler",
            code=_lambda.Code.from_asset("lambda_ui"),
            timeout=cdk.Duration.seconds(120),
            memory_size=256,
            environment={
                "AGENT_ID": agent.attr_agent_id,
            },
        )

        # UI Lambda needs permission to invoke the Bedrock Agent
        ui_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeAgent"],
                resources=["*"],
            )
        )

        # Function URL (public)
        fn_url = ui_lambda.add_function_url(
            auth_type=_lambda.FunctionUrlAuthType.NONE,
        )

        # Required since Oct 2025 for public Function URLs
        ui_lambda.add_permission(
            "PublicInvoke",
            principal=iam.AnyPrincipal(),
            action="lambda:InvokeFunctionUrl",
            function_url_auth_type=_lambda.FunctionUrlAuthType.NONE,
        )

        # --- Outputs ---
        cdk.CfnOutput(self, "AgentId", value=agent.attr_agent_id)
        cdk.CfnOutput(self, "AgentName", value="AVDV-cyclomatic-complexity-agent")
        cdk.CfnOutput(self, "ActionLambda", value=action_lambda.function_name)
        cdk.CfnOutput(self, "UIUrl", value=fn_url.url)
