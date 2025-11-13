from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import io
import json
from typing import Dict

from .models import GraphModel
from .graph import DAG
from . import health as healthlib
from pathlib import Path


app = FastAPI(title="DAG Health API", version="1.0.0")

# open up CORS just to make it easy to hit from a browser or tool
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
def index():
    # simple landing page so anyone hitting the root knows the key endpoints
    return """
    <h3>DAG Health API</h3>
    <ul>
      <li>POST <code>/health/raw</code> — JSON in, JSON out (per-node results)</li>
      <li>POST <code>/health/overall</code> — JSON in, HTML table of full system health</li>
      <li>GET <code>/health/table</code> — quick browser-friendly HTML table using sample_dag.json</li>
      <li>POST <code>/graph/image</code> — JSON in, PNG image of DAG (optional)</li>
    </ul>
    """


@app.post("/health/raw")
async def health_raw(graph: GraphModel):
    # validate and build the DAG structure
    dag = DAG.from_json(json.loads(graph.model_dump_json(by_alias=True)))

    # get nodes arranged by dependency "layers"
    levels = dag.bfs_levels()

    # walk level-by-level, but check nodes inside a level in parallel
    all_results: Dict[str, Dict] = {}
    for lvl in levels:
        level_results = await healthlib.level_health(lvl, dag)
        all_results.update(level_results)

    # overall is healthy only if every node passes
    overall = "healthy" if all(r["status"] == "healthy" for r in all_results.values()) else "unhealthy"

    return {
        "overall": overall,
        "levels": levels,
        "results": all_results,
    }


@app.post("/health/overall", response_class=HTMLResponse)
async def health_overall(graph: GraphModel):
    # reuse the core logic and just change how we present the result
    result = await health_raw(graph)

    rows = "".join(
        f"<tr><td>{nid}</td><td>{r['status']}</td><td>{r['latency_ms']} ms</td><td>{r.get('error','')}</td></tr>"
        for nid, r in sorted(result["results"].items())
    )

    html = f"""
    <h3>Overall system: {result['overall']}</h3>
    <table border="1" cellpadding="6" cellspacing="0">
      <thead>
        <tr>
          <th>Component</th>
          <th>Status</th>
          <th>Latency</th>
          <th>Error</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
    """
    return HTMLResponse(content=html)


@app.post("/graph/image")
async def graph_image(graph: GraphModel):
    # plotting is optional; if libs are missing, I fail fast with a clear message
    try:
        import networkx as nx
        import matplotlib.pyplot as plt
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"plotting dependencies missing: {e}")

    dag = DAG.from_json(json.loads(graph.model_dump_json(by_alias=True)))
    levels = dag.bfs_levels()

    # run the same health logic so we can color nodes by status
    all_results: Dict[str, Dict] = {}
    for lvl in levels:
        level_results = await healthlib.level_health(lvl, dag)
        all_results.update(level_results)

    G = nx.DiGraph()
    for n in dag.nodes:
        G.add_node(n)
    for s, outs in dag.edges.items():
        for t in outs:
            G.add_edge(s, t)

    # keeping it simple here: spring layout works without extra system deps
    pos = nx.spring_layout(G, seed=42)


    # unhealthy nodes pop out in red; healthy ones stay green-ish
    node_colors = [
        "red" if all_results[n]["status"] != "healthy" else "lightgreen"
        for n in G.nodes()
    ]

    fig = plt.figure(figsize=(8, 4.5))
    nx.draw(G, pos, with_labels=True, node_color=node_colors, arrows=True)

    buf = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")

@app.get("/health/table", response_class=HTMLResponse)
async def health_table_view():
    """
    Convenience endpoint that loads sample_dag.json and renders the same HTML table
    as /health/overall. This is only for easy viewing in a browser (GET instead of POST).
    """
    import json
    from pathlib import Path

    sample_path = Path("sample_dag.json")
    if not sample_path.exists():
        return HTMLResponse("<h3>Error: sample_dag.json not found.</h3>", status_code=500)

    # Load sample DAG
    data = json.loads(sample_path.read_text())
    graph = GraphModel(**data)

    # Use THE SAME LOGIC as /health/overall
    result = await health_raw(graph)

    # Build the table rows
    rows = "".join(
        f"<tr><td>{nid}</td><td>{r['status']}</td><td>{r['latency_ms']} ms</td><td>{r.get('error','')}</td></tr>"
        for nid, r in sorted(result["results"].items())
    )

    html = f"""
    <h3>Overall system: {result['overall']}</h3>
    <table border="1" cellpadding="6" cellspacing="0">
      <thead>
        <tr>
          <th>Component</th>
          <th>Status</th>
          <th>Latency</th>
          <th>Error</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
    """

    return HTMLResponse(html)
