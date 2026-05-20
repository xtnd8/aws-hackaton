"""
Lambda function backing the Bedrock Agent action group.
The agent invokes this when a user request matches one of the defined actions.
"""


def handler(event, context):
    """Handle action group invocations from the Bedrock Agent."""

    api_path = event.get("apiPath")
    http_method = event.get("httpMethod")
    parameters = event.get("parameters", [])

    # Extract named parameters into a dict for convenience
    params = {p["name"]: p["value"] for p in parameters}

    # Route to the appropriate action
    if api_path == "/greet" and http_method == "GET":
        name = params.get("name", "World")
        body = {"message": f"Hello, {name}! I'm your Bedrock Agent."}
    else:
        body = {"message": f"Unknown action: {http_method} {api_path}"}

    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event.get("actionGroup"),
            "apiPath": api_path,
            "httpMethod": http_method,
            "httpStatusCode": 200,
            "responseBody": {
                "application/json": {
                    "body": str(body)
                }
            },
        },
    }
