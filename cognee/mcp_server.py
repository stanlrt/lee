"""Cognee MCP server — exposes knowledge graph tools over SSE for NanoClaw agent containers."""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load project .env first to inherit shared keys (e.g. GEMINI_API_KEY),
# then cognee/.env to allow cognee-specific overrides.
_project_root = Path(__file__).parent.parent
load_dotenv(_project_root / ".env")
load_dotenv(Path(__file__).parent / ".env", override=True)

# Map shared provider keys to cognee's expected LLM_API_KEY / EMBEDDING_API_KEY
_gemini_key = os.environ.get("GEMINI_API_KEY", "")
os.environ.setdefault("LLM_API_KEY", _gemini_key)
os.environ.setdefault("EMBEDDING_API_KEY", _gemini_key)

# Redirect storage out of the venv
_data_dir = Path(__file__).parent / "data"
os.environ.setdefault("DATA_ROOT_DIRECTORY", str(_data_dir / "cognee_data"))
os.environ.setdefault("SYSTEM_ROOT_DIRECTORY", str(_data_dir / "cognee_system"))
os.environ.setdefault("TELEMETRY_DISABLED", "true")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import cognee  # noqa: E402 — must come after env setup

mcp = FastMCP(
    "cognee",
    host="0.0.0.0",
    port=8765,
)


@mcp.tool()
async def cognee_add(text: str, dataset_name: str = "main") -> str:
    """Add text to the Cognee knowledge graph dataset."""
    await cognee.add(text, dataset_name=dataset_name)
    return f"Added to dataset '{dataset_name}'."


@mcp.tool()
async def cognee_cognify(dataset_name: str = "main") -> str:
    """Process ingested data into the knowledge graph. Call after cognee_add."""
    await cognee.cognify(datasets=[dataset_name])
    return f"Knowledge graph built for dataset '{dataset_name}'."


@mcp.tool()
async def cognee_search(
    query: str,
    search_type: str = "GRAPH_COMPLETION",
    dataset_name: str = "main",
    top_k: int = 10,
) -> str:
    """Search the Cognee knowledge graph.

    search_type options: GRAPH_COMPLETION, RAG_COMPLETION, CHUNKS, SUMMARIES, CODE, FEELING_LUCKY
    """
    st = cognee.SearchType[search_type]
    results = await cognee.search(
        query,
        query_type=st,
        datasets=[dataset_name],
        top_k=top_k,
    )
    if not results:
        return "No results found."
    return "\n\n".join(str(r) for r in results)


if __name__ == "__main__":
    mcp.run(transport="sse")
