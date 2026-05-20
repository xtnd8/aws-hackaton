# Simple Amazon Bedrock Agent

A minimal, deployable Bedrock Agent built with AWS CDK (Python). The agent uses Claude 3 Haiku and has a single action group that greets users by name.

## Prerequisites

- Python 3.12+
- AWS CDK CLI (`npm install -g aws-cdk`)
- AWS credentials configured (profile or environment variables)
- Bedrock model access enabled for `anthropic.claude-3-haiku-20240307-v1:0` in your region

## Setup

```bash
cd bedrock-agent
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

## Deploy

```bash
cdk bootstrap   # first time only
cdk deploy
```

## Test

After deployment, go to the **Amazon Bedrock > Agents** console, find `SimpleGreetingAgent`, and use the built-in test chat to say "Hello, my name is Alice".

## Clean Up

```bash
cdk destroy
```

## Architecture

- **Bedrock Agent** — orchestrates conversation using Claude 3 Haiku
- **Action Group** — defines a `/greet` API backed by a Lambda function
- **Lambda** — returns a personalized greeting message
