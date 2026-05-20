"""Invoke the Bedrock Agent from the command line."""
import boto3
import sys

AGENT_ID = "2CVKKHMWQD"  # Updated after deploy
AGENT_ALIAS_ID = "TSTALIASID"
SESSION_ID = "test-session-001"
REGION = "eu-west-1"

input_text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Hello, what can you do?"

client = boto3.client("bedrock-agent-runtime", region_name=REGION)

response = client.invoke_agent(
    agentId=AGENT_ID,
    agentAliasId=AGENT_ALIAS_ID,
    sessionId=SESSION_ID,
    inputText=input_text,
    enableTrace=True,
)

completion = ""
for event in response["completion"]:
    if "chunk" in event:
        chunk_bytes = event["chunk"]["bytes"]
        completion += chunk_bytes.decode("utf-8")

print(f"\nUser: {input_text}")
print(f"Agent: {completion}")
