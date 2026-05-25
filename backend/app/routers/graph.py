"""Graph endpoints — serve the stored graph in the frontend's Graph shape.

DB -> frontend mapping: nodes.user_text -> turn.user, nodes.assistant_text ->
turn.assistant, nodes.kind -> kind. Edges collapse to links {source, target};
edge_type is stored but not yet consumed by the frontend.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import Edge, Node
from ..schemas import Graph, GLink, GNode, Turn

router = APIRouter(prefix="/api", tags=["graph"])


def _to_gnode(n: Node) -> GNode:
    return GNode(
        id=str(n.id),
        label=n.heading,
        kind=n.kind,
        turn=Turn(user=n.input_prompt, assistant=n.ai_output),
    )


@router.get("/graph", response_model=Graph)
async def get_graph(session: AsyncSession = Depends(get_session)) -> Graph:
    nodes = (await session.execute(select(Node))).scalars().all()
    edges = (await session.execute(select(Edge))).scalars().all()
    return Graph(
        nodes=[_to_gnode(n) for n in nodes],
        links=[GLink(source=str(e.source_id), target=str(e.target_id)) for e in edges],
    )


@router.get("/nodes/{node_id}", response_model=GNode)
async def get_node(
    node_id: str, session: AsyncSession = Depends(get_session)
) -> GNode:
    node = await session.get(Node, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail=f"unknown node: {node_id}")
    return _to_gnode(node)
