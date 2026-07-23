"""Least-privilege remote MCP configurations used by the lab."""

from __future__ import annotations

from collections.abc import Sequence

from crewai.mcp import MCPServerHTTP
from crewai.mcp.filters import create_static_tool_filter

from lab_utils.settings import (
    FIRECRAWL_API_KEY,
    FIRECRAWL_MCP_URL,
    LINEAR_API_KEY,
    LINEAR_MCP_URL,
)

FIRECRAWL_ALLOWED_TOOLS = ("firecrawl_search", "firecrawl_scrape")
LINEAR_ALLOWED_TOOLS = ("save_issue",)


def build_firecrawl_mcp(
    *,
    url: str = FIRECRAWL_MCP_URL,
    api_key: str = FIRECRAWL_API_KEY,
    allowed_tools: Sequence[str] | None = None,
) -> MCPServerHTTP:
    """Build a least-privilege Firecrawl Streamable HTTP connection.

    Firecrawl's hosted endpoint supports a rate-limited keyless tier. When a
    key is provided, CrewAI sends it as a bearer token without placing it in
    the URL or agent prompt.
    """
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else None
    tool_names = list(allowed_tools or FIRECRAWL_ALLOWED_TOOLS)
    return MCPServerHTTP(
        url=url,
        headers=headers,
        streamable=True,
        tool_filter=create_static_tool_filter(allowed_tool_names=tool_names),
        cache_tools_list=True,
    )


def build_linear_mcp(
    *,
    url: str = LINEAR_MCP_URL,
    api_key: str = LINEAR_API_KEY,
    allowed_tools: Sequence[str] | None = None,
) -> MCPServerHTTP:
    """Build the authenticated Linear Streamable HTTP connection.

    Linear supports interactive OAuth, OAuth access tokens, and API keys. The
    lab uses a bearer API key so a standalone Python process can authenticate
    without an interactive browser callback.
    """
    if not api_key:
        raise ValueError(
            "LINEAR_API_KEY is required to use the Linear MCP write endpoint. "
            "Create a scoped key and add it to .env."
        )

    tool_names = list(allowed_tools or LINEAR_ALLOWED_TOOLS)
    return MCPServerHTTP(
        url=url,
        headers={"Authorization": f"Bearer {api_key}"},
        streamable=True,
        tool_filter=create_static_tool_filter(allowed_tool_names=tool_names),
        cache_tools_list=True,
    )
