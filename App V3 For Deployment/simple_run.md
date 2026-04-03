# Quick reference — App V3 For Deployment

- **Full deployment guide:** [`README.md`](README.md) (Connect vars, deploy order, scripts).
- **Feature overview and screenshots:** [`../App V3 Local Run/README.md`](../App%20V3%20Local%20Run/README.md).

**Install:** `pip install -r requirements.txt` — copy `.env.example` to `.env`.

**Publish (from this folder):**

```bash
python scripts/deploy_mcp_http_bridge.py
python scripts/deploy_shiny.py
```

Set **`CONNECT_SHINY_APP_ID`** in `.env` to the Shiny content GUID (from the Connect URL) so `deploy_shiny.py` updates that same app. Omit it and use **`--new`** only when creating a brand-new Shiny content item.

**Local Shiny:** `python app/run_me.py` — set `SHINY_RELOAD=1` to mimic old auto-reload behavior.

**Local HTTP tool bridge (for testing `MCP_BASE_URL`):**  
`python -m uvicorn mcp_server.http_bridge:app --host 127.0.0.1 --port 8766`
