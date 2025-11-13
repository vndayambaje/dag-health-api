import asyncio
import random
from typing import Dict, Any, Tuple, Optional

import httpx

# small timeout so a slow dependency doesn't hang the whole check
DEFAULT_TIMEOUT = 2.0


async def check_single(
    node_id: str,
    health_url: Optional[str],
    seed: Optional[int] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Run one health check and return (node_id, result).
    Result is just a small dict with status / latency / optional error.
    """
    # manual timing so I can report how long each check took
    start = asyncio.get_event_loop().time()

    try:
        if health_url:
            # real health check: simple GET, 2xx means "healthy"
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                resp = await client.get(health_url)
                ok = 200 <= resp.status_code < 300
        else:
            # if the node doesn't expose a URL, I fake it in a controlled way
            # seed keeps the behavior somewhat stable between runs
            rnd = random.Random(seed if seed is not None else (hash(node_id) & 0xFFFFFFFF))
            await asyncio.sleep(rnd.uniform(0.01, 0.12))
            ok = rnd.random() > 0.01  # roughly 1% failure just to see some red

        status = "healthy" if ok else "unhealthy"

        return node_id, {
            "status": status,
            "latency_ms": int((asyncio.get_event_loop().time() - start) * 1000),
        }

    except Exception as ex:
        # if one node blows up, I still want a result instead of killing the whole run
        return node_id, {
            "status": "unhealthy",
            "latency_ms": int((asyncio.get_event_loop().time() - start) * 1000),
            "error": str(ex),
        }


async def level_health(level_nodes, dag, seed=None):
    """
    Kick off health checks for a whole level in parallel.
    The DAG is only used to grab health URLs; logic is kept simple here.
    """
    tasks = [check_single(n, dag.nodes[n].health_url, seed) for n in level_nodes]
    results = await asyncio.gather(*tasks)
    return dict(results)
