"""Invoke the Bedrock Agent from the command line."""
import boto3
import sys

AGENT_ID = "BIJDR9FDGL"
AGENT_ALIAS_ID = "TSTALIASID"
SESSION_ID = "test-session-001"

input_text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Hello, my name is Alice"

client = boto3.client("bedrock-agent-runtime", region_name="eu-west-1")

response = client.invoke_agent(
    agentId=AGENT_ID,
    agentAliasId=AGENT_ALIAS_ID,
    sessionId=SESSION_ID,
    inputText=input_text,
    enableTrace=True,
)

# The response is an event stream — collect the chunks
completion = ""
for event in response["completion"]:
    if "chunk" in event:
        chunk_bytes = event["chunk"]["bytes"]
        completion += chunk_bytes.decode("utf-8")

print(f"\nUser: {input_text}")
print(f"Agent: {completion}")
