# AVDV Cyclomatic Complexity Agent

An AI agent that analyzes cyclomatic complexity of code snippets and GitHub repositories. Built with Amazon Bedrock Agents and deployed via AWS CDK.

## Architecture

- **Bedrock Agent** — orchestrates conversation using Claude Sonnet 4.5 (eu-west-1 cross-region inference)
- **Action Group Lambda** — computes McCabe's cyclomatic complexity for code snippets and fetches/analyzes GitHub repos
- **UI Lambda** — serves a chat web interface via Lambda Function URL, proxies requests to the Bedrock Agent

## Features

- Analyze cyclomatic complexity of pasted code snippets
- Analyze all Python files in a public GitHub repository
- Get explanations and refactoring suggestions
- Web-based chat UI (no auth required)

## Prerequisites

- Python 3.12+
- AWS CDK CLI (`npm install -g aws-cdk`)
- AWS credentials configured
- Bedrock model access enabled for `eu.anthropic.claude-sonnet-4-5-20250929-v1:0` in eu-west-1

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

## Deploy

```bash
cdk bootstrap   # first time only
cdk deploy
```

After deploy, the UI URL is printed in the outputs.

## Test (CLI)

```bash
python invoke_agent.py "Analyze this repo: https://github.com/xtnd8/aws-hackaton"
```

## Clean Up

```bash
cdk destroy
```
