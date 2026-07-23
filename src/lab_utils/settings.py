"""Environment-backed lab settings."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

LAB_MODEL = os.getenv("LAB_MODEL", "openai/gpt-5.4")
FIRECRAWL_MCP_URL = os.getenv(
    "FIRECRAWL_MCP_URL", "https://mcp.firecrawl.dev/v2/mcp"
).strip()
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "").strip()
LINEAR_MCP_URL = os.getenv("LINEAR_MCP_URL", "https://mcp.linear.app/mcp").strip()
LINEAR_API_KEY = os.getenv("LINEAR_API_KEY", "").strip()
LINEAR_TEAM = os.getenv("LINEAR_TEAM", "").strip()
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "crewAIInc").strip()
GITHUB_REPO = os.getenv("GITHUB_REPO", "crewAI").strip()
