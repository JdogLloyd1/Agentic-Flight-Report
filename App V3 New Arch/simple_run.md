# Run the App V3 stack locally

Use these steps from the **`App V3 New Arch`** folder (the directory that contains `app/` and `mcp_server/`).

## 1. One-time setup

1. Create a virtual environment (recommended) and install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and set at least **Ollama** credentials if you use Ollama Cloud (`OLLAMA_API_KEY`, and `OLLAMA_HOST` if not the default). For a local Ollama server, point `OLLAMA_HOST` at it (for example `http://127.0.0.1:11434`) and you can leave the API key unset.

3. Optional — build the RAG index so Agent 2 has document search (otherwise the UI may show empty reference excerpts):

   ```bash
   python -m app.rag.ingest
   ```

## 2. Run the Shiny app (main way to test)

From **`App V3 New Arch`**:

```bash
python app/run_me.py
```

Then open a browser at **http://127.0.0.1:8000** (default). You should see the flight form and can run the multi-agent workflow.

- Change host or port with environment variables: `SHINY_HOST`, `SHINY_PORT` (defaults: `127.0.0.1`, `8000`).
- The script enables **reload** so edits to Python files restart the server.

## 3. Run the MCP server (optional)

By default, **Agent 1** calls tools **in process** when `MCP_BASE_URL` is not set in `.env`, so you do **not** need a separate MCP process to test the Shiny app.

To run the MCP HTTP/SSE server anyway (for example to test integrations that expect a remote MCP):

From **`App V3 New Arch`**:

```bash
python mcp_server/run_me.py
```

The server listens on **http://127.0.0.1:8765** by default (SSE path is **`/sse`** per FastMCP). Override with `MCP_HOST` and `MCP_PORT` if needed.

To force the Shiny workflow to call tools over HTTP instead of in-process, set **`MCP_BASE_URL`** in `.env` to match whatever URL your deployment exposes for tool calls (this repo’s in-process path does not require it for local testing).

## 4. Quick checklist

| What | Command | Browser / URL |
|------|---------|----------------|
| Web UI | `python app/run_me.py` | http://127.0.0.1:8000 |
| MCP (optional) | `python mcp_server/run_me.py` | http://127.0.0.1:8765/sse (SSE) |

Stop either process with **Ctrl+C** in its terminal.
