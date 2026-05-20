"""Lambda handler serving the chat UI and proxying requests to the Bedrock Agent."""

import json
import os
import boto3
import base64


AGENT_ID = os.environ["AGENT_ID"]
AGENT_ALIAS_ID = "TSTALIASID"
REGION = os.environ.get("AWS_REGION", "eu-west-1")


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cyclomatic Complexity Agent</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #1a1a2e; color: #eee; height: 100vh; display: flex; flex-direction: column; }
header { background: #16213e; padding: 1rem 1.5rem; border-bottom: 1px solid #0f3460; }
header h1 { font-size: 1.3rem; color: #e94560; }
header p { font-size: 0.8rem; color: #888; margin-top: 0.25rem; }
#chat { flex: 1; overflow-y: auto; padding: 1.5rem; display: flex; flex-direction: column; gap: 1rem; }
.msg { max-width: 80%; padding: 0.75rem 1rem; border-radius: 12px; line-height: 1.5; white-space: pre-wrap; word-wrap: break-word; }
.msg.user { align-self: flex-end; background: #0f3460; color: #fff; }
.msg.assistant { align-self: flex-start; background: #222; color: #ddd; border: 1px solid #333; }
#input-area { display: flex; gap: 0.5rem; padding: 1rem 1.5rem; background: #16213e; border-top: 1px solid #0f3460; }
#prompt { flex: 1; padding: 0.75rem 1rem; border: 1px solid #0f3460; border-radius: 8px; background: #1a1a2e; color: #eee; font-size: 0.95rem; resize: none; min-height: 44px; max-height: 200px; font-family: inherit; }
#prompt:focus { outline: none; border-color: #e94560; }
#send { padding: 0.75rem 1.5rem; background: #e94560; color: #fff; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 0.95rem; }
#send:hover { background: #c73e54; }
#send:disabled { background: #555; cursor: not-allowed; }
.typing { color: #888; font-style: italic; }
.examples { padding: 0.5rem 1.5rem; display: flex; gap: 0.5rem; flex-wrap: wrap; }
.examples button { background: #0f3460; border: 1px solid #1a4080; color: #aaa; padding: 0.4rem 0.8rem; border-radius: 6px; cursor: pointer; font-size: 0.8rem; }
.examples button:hover { background: #1a4080; color: #fff; }
</style>
</head>
<body>
<header>
  <h1>&#128269; Cyclomatic Complexity Agent</h1>
  <p>Powered by Amazon Bedrock Agent + Claude Sonnet 4.5 | Analyze snippets or entire repos</p>
</header>
<div class="examples">
  <button onclick="sendExample('What is cyclomatic complexity?')">What is cyclomatic complexity?</button>
  <button onclick="sendExample('Analyze this repo: https://github.com/xtnd8/aws-hackaton')">Analyze this repo</button>
  <button onclick="sendExample('Analyze this code:\\ndef foo(x):\\n    if x > 0:\\n        return x\\n    else:\\n        return -x')">Simple snippet</button>
  <button onclick="sendExample('Analyze this code:\\ndef parse(data):\\n    if not data:\\n        return None\\n    result = {}\\n    for key, val in data.items():\\n        if isinstance(val, dict):\\n            for k, v in val.items():\\n                if v is not None:\\n                    result[key + k] = v\\n        elif isinstance(val, list):\\n            for i, item in enumerate(val):\\n                if item:\\n                    result[key + str(i)] = item\\n        else:\\n            result[key] = val\\n    return result')">Complex snippet</button>
</div>
<div id="chat"></div>
<div id="input-area">
  <textarea id="prompt" placeholder="Paste code, a GitHub repo URL, or ask about complexity..." rows="1"></textarea>
  <button id="send" onclick="send()">Send</button>
</div>
<script>
const chat = document.getElementById('chat');
const input = document.getElementById('prompt');
const btn = document.getElementById('send');
let sessionId = 'session-' + Math.random().toString(36).substr(2, 9);

input.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
});
input.addEventListener('input', () => {
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 200) + 'px';
});

function addMsg(role, text) {
  const div = document.createElement('div');
  div.className = 'msg ' + role;
  div.textContent = text;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

function sendExample(text) {
  input.value = text;
  send();
}

async function send() {
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  input.style.height = 'auto';
  addMsg('user', text);
  btn.disabled = true;
  const typing = addMsg('assistant', 'Thinking... (repo analysis may take up to 60s)');
  typing.classList.add('typing');
  try {
    const res = await fetch(window.location.href, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({prompt: text, session_id: sessionId})
    });
    const data = await res.json();
    typing.remove();
    addMsg('assistant', data.response || data.error || 'No response');
  } catch(err) {
    typing.remove();
    addMsg('assistant', 'Error: ' + err.message);
  }
  btn.disabled = false;
  input.focus();
}
</script>
</body>
</html>"""


def _invoke_bedrock_agent(prompt: str, session_id: str) -> str:
    """Invoke the Bedrock Agent and collect the response."""
    client = boto3.client("bedrock-agent-runtime", region_name=REGION)

    response = client.invoke_agent(
        agentId=AGENT_ID,
        agentAliasId=AGENT_ALIAS_ID,
        sessionId=session_id,
        inputText=prompt,
    )

    completion = ""
    for event in response["completion"]:
        if "chunk" in event:
            completion += event["chunk"]["bytes"].decode("utf-8")

    return completion


def handler(event, _context):
    """Lambda entry point - serves UI (GET) and proxies to agent (POST)."""

    request_context = event.get("requestContext", {})
    http_info = request_context.get("http", {})
    method = http_info.get("method", "").upper()

    if method == "GET":
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "text/html"},
            "body": HTML_PAGE,
        }

    if method == "POST":
        body = event.get("body", "{}")
        if event.get("isBase64Encoded"):
            body = base64.b64decode(body).decode("utf-8")
        payload = json.loads(body)
        prompt = payload.get("prompt", "Hello!")
        session_id = payload.get("session_id", "default-session")

        try:
            result = _invoke_bedrock_agent(prompt, session_id)
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"response": result}),
            }
        except Exception as e:
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": str(e)}),
            }

    return {
        "statusCode": 400,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": "Unsupported request"}),
    }
