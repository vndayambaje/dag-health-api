# DAG Health API

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-backend-009688)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/tests-pytest-green)](https://docs.pytest.org/)

<p align="center">
    <!--FASTAPI-->
    <img src="https://user-images.githubusercontent.com/1393562/190876570-16dff98d-ccea-4a57-86ef-a161539074d6.svg" width="12%" alt="FastAPI">
    <!--PLUS-->
    <span style="font-size:80px; font-weight:bold; margin: 0 20px;">+</span>
    <!--PYTHON-->
    <img src="https://www.python.org/static/community_logos/python-logo.png" width="20%" alt="Python">
    <!--PLUS-->
    <span style="font-size:80px; font-weight:bold; margin: 0 20px;">+</span>
     <!-- NetworkX Logo -->
    <img src="https://avatars.githubusercontent.com/u/388785?s=200&v=4" 
        width="120" alt="NetworkX Logo"/>
    <!-- PLUS -->
    <span style="font-size:80px; font-weight:bold; margin: 0 20px;">+</span>
    <!-- PLUS -->
    <!-- DAG Icon -->
    <img src="https://miro.medium.com/v2/resize:fit:140/format:webp/1*JVNNslvkfBHazu-Wnx1vSg.png"/>
</p>

---

- [DAG Health API](#dag-health-api)
  - [Overview](#overview)
  - [Features](#features)
  - [System Overview](#system-overview)
  - [Installation \& Setup](#installation--setup)
  - [Running the API](#running-the-api)
  - [Available Endpoints](#available-endpoints)
  - [Testing With Pytest](#testing-with-pytest)
  - [Command Reference](#command-reference)
  - [Notes \& Potential Improvements](#notes--potential-improvements)

---

## Overview

The **DAG Health API** checks the health of system components arranged as a **Directed Acyclic Graph (DAG)**.

At a high level, the API:

- Loads a DAG definition from JSON
- Validates node and edge relationships
- Groups nodes into dependency “levels” (topological / BFS-style)
- Runs asynchronous health checks for each node
- Aggregates the results into JSON, HTML, and a PNG DAG diagram

The focus is on clear structure over clever tricks so the code is easy to review.

---

## Features

-  DAG definition via JSON (`nodes` + `edges`)
-  Validation that all edges reference existing nodes
-  Level-based traversal so dependencies are checked first
-  Async health checks with simulated latency
-  JSON endpoint for programmatic consumers
-  HTML endpoint for quick manual inspection
-  PNG graph endpoint with colored nodes (healthy/unhealthy)
-  Minimal but useful pytest-based test

---

## System Overview

The API follows a pretty straightforward path. The client sends in a JSON description of the system, which is basically a list of nodes and edges forming a DAG. FastAPI handles the request and hands things off to a small internal layer where the real work happens.

First, I run the input through a couple of Pydantic models just to make sure the structure is sane; things like missing fields or invalid links get caught early. Once the JSON validates, I use NetworkX to build the actual directed graph. I’m not doing anything fancy here; NetworkX just saves me from re-implementing adjacency lists and topological traversal logic.

The health check part is asynchronous on purpose. Each node simulates a “service check,” and I run them in parallel using asyncio.gather so the whole graph doesn’t get blocked waiting on one slow component. Even though the checks are fake (no real services), the pattern is the same as what you’d do in production: fire off async probes and aggregate the results.

When everything completes, the API exposes multiple output formats depending on the endpoint:

- JSON for programmatic use,

- a basic HTML table for readability,

- and optionally a PNG version of the DAG with failed nodes highlighted in red.
The graph rendering uses NetworkX plus Matplotlib, but I keep it minimal.

All work is done in memory, no database, and no caching because the assignment doesn’t need persistence. The whole thing is structured to match the requirements: load a DAG, traverse it breadth-first, run async health checks, and surface the final system state in different formats.

## Installation & Setup
This project uses Poetry to manage dependencies.

1. Install dependencies

```poetry install```

2. Run the API

```poetry run uvicorn app.main:app --reload```

Then open:

http://127.0.0.1:8000

Interactive documentation:

http://127.0.0.1:8000/docs

## Running the API

Keep the server running with:

```poetry run uvicorn app.main:app --reload```

Then you can exercise the endpoints via:

- ```curl```

- a browser

- Postman / Thunder Client

- the built-in /docs Swagger UI

Example Input (```sample_dag.json```)

```sample_dag.json``` describes a simple 4-node DAG:

```json
{
  "nodes": [
    {"id": "A", "health_url": null},
    {"id": "B", "health_url": null},
    {"id": "C", "health_url": null},
    {"id": "D", "health_url": null}
  ],
  "edges": [
    {"from": "A", "to": "B"},
    {"from": "A", "to": "C"},
    {"from": "B", "to": "D"},
    {"from": "C", "to": "D"}
  ]
}
```
- nodes are system components

- edges define “depends on” relationships: from → to

## Available Endpoints

**POST** ```/health/raw```

Returns a JSON summary:

- ```levels```: DAG nodes grouped by dependency level

- ```results```: per-node status + simulated latency

- ```overall```: ```"healthy"``` if all nodes are healthy, otherwise ```"unhealthy"```

Example:

```bash

curl -X POST http://127.0.0.1:8000/health/raw \
  -H "Content-Type: application/json" \
  -d @sample_dag.json
```

**Example response (values vary)**:

```json
{
  "overall": "healthy",
  "levels": [["A"], ["B", "C"], ["D"]],
  "results": {
    "A": {"status": "healthy", "latency_ms": 42},
    "B": {"status": "healthy", "latency_ms": 63},
    "C": {"status": "healthy", "latency_ms": 55},
    "D": {"status": "healthy", "latency_ms": 71}
  }
}
```
**POST** ```/health/overall```

Returns the same information rendered as an HTML table.

**Example**:

```bash
curl -X POST http://127.0.0.1:8000/health/overall \
  -H "Content-Type: application/json" \
  -d @sample_dag.json
```
In a browser, this shows a simple table with:

- Component name

- Status (healthy/unhealthy)

- Latency in milliseconds

- Error text (if any)

**POST** ```/graph/image```

Generates a PNG image of the DAG:

- Nodes are positioned using a spring layout

- Healthy nodes are drawn in green

- Unhealthy nodes are drawn in red

- Edges show the direction of dependency

Example:

```bash
curl -X POST http://127.0.0.1:8000/graph/image \
  -H "Content-Type: application/json" \
  -d @sample_dag.json --output dag.png
```

A valid PNG usually falls in the **40–150 KB** range.
A very small file (like ~20 bytes) often means an error response (e.g. wrong HTTP method).

**GET** ```/health/table```

Renders a browser-friendly HTML table using ```sample_dag.json```.

This endpoint exists so you can quickly view the system-health output without crafting a POST request.

It uses the same logic as /health/overall, but loads the sample DAG automatically.

**Example (just open in a browser):**

http://127.0.0.1:8000/health/table


**Example rendered output (layout varies):**

**Overall system: healthy**
| Component	| Status	| Latency	| Error |
|-----------|---------|---------|-------|
| Step 1	| healthy	| 19 ms | 	
| Step 10	| healthy	| 101 ms |	
| Step 11	| healthy	| 94 ms |
| Step 2	| healthy	| 115 ms |
| Step 3	| healthy	| 43 ms |	
| Step 4	| healthy	| 101 ms |	
| Step 5	| healthy	| 29 ms	 |
| Step 6	| healthy	| 106 ms |	
| Step 7	| healthy	| 90 ms |	
| Step 8	| healthy	| 96 ms |	
| Step 9	| healthy	| 59 ms |	



## Testing With Pytest

Tests live under tests/.

Run the test suite with:

```bash
poetry run pytest -q
```
Expected output:

```text
1 passed in 1.23s
```
If ```sample_dag.json``` is missing or malformed, or if the app import fails, pytest will report an error during collection or test execution.

## Command Reference
| **Task**              | **Command**	                              | **Result**                       |
|-----------------------|---------------------------------------------|----------------------------------|
| Install dependencies  | ```poetry install```                        | Creates virtualenv and installs packages | 
| Run API server        | ```poetry run uvicorn app.main:app --reload```| Serves API at http://127.0.0.1:8000 | 
| JSON health summary   | ```curl -X POST http://127.0.0.1:8000/health/raw -d @sample_dag.json```| JSON with levels, statuses, and overall result | 
| HTML health table     | 	```curl -X POST http://127.0.0.1:8000/health/overall -d @sample_dag.json```	| HTML table output | 
| DAG PNG diagram       | ```curl -X POST http://127.0.0.1:8000/graph/image -d @sample_dag.json --output dag.png```	| PNG diagram of DAG | 
| Run tests	            | ```poetry run pytest -q```	| Runs tests; should report “1 passed”

## Notes & Potential Improvements
Some obvious next steps if this were extended beyond the coding exercise:

- Replace simulated health checks with actual HTTP calls using health_url

- Add per-node retry/backoff behavior and configurable thresholds

- Attach more metrics (e.g., percentiles, error rates)

- Persist historical health runs for trend analysis

- Add authentication / authorization if exposed publicly

- Build a small UI dashboard on top of the existing endpoints

For the purposes of this challenge, the core pipeline is in place:

**Parse DAG → validate → compute levels → run async health checks → expose JSON / HTML / PNG.**