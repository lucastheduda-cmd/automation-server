"""
Example job: fetch a URL and return its status code and page title.

Usage:
  POST /jobs
  { "job": "fetch_url", "params": { "url": "https://example.com" } }
"""
import re
import urllib.request


def run(url: str = "https://example.com") -> dict:
    with urllib.request.urlopen(url, timeout=10) as resp:
        html = resp.read().decode("utf-8", errors="ignore")
        status = resp.status

    title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    title = title_match.group(1).strip() if title_match else "(no title)"

    return {"url": url, "status_code": status, "title": title}
