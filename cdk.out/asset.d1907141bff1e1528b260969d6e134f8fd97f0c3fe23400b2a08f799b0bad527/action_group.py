"""
Lambda function backing the Bedrock Agent action group.
Provides cyclomatic complexity analysis for code snippets and GitHub repos.
"""

import json
import urllib.request
import re


def _compute_complexity(code: str) -> int:
    """Compute cyclomatic complexity for a code string."""
    decision_keywords = [
        "if ", "elif ", "for ", "while ",
        " and ", " or ",
        "except ", "except:",
        "with ", "assert ",
    ]
    lines = code.split("\n")
    complexity = 1
    for line in lines:
        stripped = line.strip()
        for keyword in decision_keywords:
            complexity += stripped.count(keyword)
        if " if " in stripped and " else " in stripped and not stripped.startswith("if "):
            complexity += 1
    return complexity


def _get_rating(complexity: int) -> str:
    if complexity <= 5:
        return "Low complexity - simple, well-structured code"
    elif complexity <= 10:
        return "Moderate complexity - acceptable but consider simplifying"
    elif complexity <= 20:
        return "High complexity - consider refactoring"
    else:
        return "Very high complexity - strongly recommend refactoring"


def _analyze_snippet(code: str) -> str:
    """Analyze a single code snippet."""
    complexity = _compute_complexity(code)
    return json.dumps({
        "complexity": complexity,
        "rating": _get_rating(complexity),
        "details": f"Found {complexity} independent paths through the code."
    })


def _analyze_repo(repo_url: str) -> str:
    """Analyze all Python files in a GitHub repo via the GitHub API."""
    match = re.search(r"github\.com/([^/]+)/([^/\s]+)", repo_url)
    if not match:
        return json.dumps({"error": "Invalid GitHub URL. Expected: https://github.com/owner/repo"})

    owner, repo = match.group(1), match.group(2).rstrip(".git")

    # Fetch repo tree
    for branch in ("main", "master"):
        api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
        try:
            req = urllib.request.Request(api_url, headers={"User-Agent": "complexity-agent"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                tree_data = json.loads(resp.read().decode("utf-8"))
            break
        except Exception:
            tree_data = None

    if not tree_data:
        return json.dumps({"error": "Failed to fetch repo. Check the URL and ensure it's public."})

    # Filter Python files
    skip_dirs = {"__pycache__", ".venv", "venv", "node_modules", ".tox", "cdk.out", ".git"}
    py_files = []
    for item in tree_data.get("tree", []):
        if item["type"] != "blob" or not item["path"].endswith(".py"):
            continue
        parts = item["path"].split("/")
        if any(p in skip_dirs or p.startswith(".") for p in parts[:-1]):
            continue
        py_files.append(item["path"])

    if not py_files:
        return json.dumps({"error": "No Python files found in the repository."})

    # Analyze each file (limit 50)
    results = []
    total_complexity = 0

    for filepath in sorted(py_files)[:50]:
        for branch in ("main", "master"):
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{filepath}"
            try:
                req = urllib.request.Request(raw_url, headers={"User-Agent": "complexity-agent"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    code = resp.read().decode("utf-8", errors="ignore")
                break
            except Exception:
                code = None

        if not code:
            continue

        file_complexity = _compute_complexity(code)
        total_complexity += file_complexity
        loc = len([l for l in code.split("\n") if l.strip()])
        results.append({
            "file": filepath,
            "complexity": file_complexity,
            "loc": loc,
            "rating": _get_rating(file_complexity).split(" - ")[0],
        })

    if not results:
        return json.dumps({"error": "Could not read any Python files from the repository."})

    avg_complexity = total_complexity / len(results)
    high_complexity = [r for r in results if r["complexity"] > 10]

    return json.dumps({
        "repo": repo_url,
        "files_analyzed": len(results),
        "total_complexity": total_complexity,
        "average_complexity": round(avg_complexity, 1),
        "high_complexity_files": high_complexity,
        "per_file_results": sorted(results, key=lambda x: x["complexity"], reverse=True),
    })


def handler(event, context):
    """Handle action group invocations from the Bedrock Agent."""

    api_path = event.get("apiPath")
    http_method = event.get("httpMethod")
    parameters = event.get("parameters", [])

    params = {p["name"]: p["value"] for p in parameters}

    if api_path == "/analyze-snippet" and http_method == "POST":
        code = params.get("code", "")
        body = _analyze_snippet(code)
    elif api_path == "/analyze-repo" and http_method == "POST":
        repo_url = params.get("repo_url", "")
        body = _analyze_repo(repo_url)
    else:
        body = json.dumps({"error": f"Unknown action: {http_method} {api_path}"})

    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event.get("actionGroup"),
            "apiPath": api_path,
            "httpMethod": http_method,
            "httpStatusCode": 200,
            "responseBody": {
                "application/json": {
                    "body": body
                }
            },
        },
    }
