from pydantic import BaseModel, Field
from typing import List, Optional, Dict


class NodeModel(BaseModel):
    # minimal shape for a component in the system
    id: str = Field(..., description="unique id for the node")
    health_url: Optional[str] = Field(None)
    metadata: Dict = Field(default_factory=dict)


class EdgeModel(BaseModel):
    # using alias so JSON uses "from" but we don't shadow the keyword in Python
    source: str = Field(..., alias="from")
    to: str


class GraphModel(BaseModel):
    # whole system description: nodes plus directed edges
    nodes: List[NodeModel]
    edges: List[EdgeModel]
