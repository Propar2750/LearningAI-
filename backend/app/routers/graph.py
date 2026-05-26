"""Graph endpoints — serve the signed-in user's graph in the frontend's shape.

DB -> frontend mapping: nodes.input_prompt -> turn.user, nodes.ai_output ->
turn.assistant, nodes.kind -> kind. Edges collapse to links {source, target};
edge_type is stored but not yet consumed by the frontend.

Every endpoint is scoped to the authenticated user: nodes/edges belong to a
``graph``, which carries ``user_id``, so we only ever return data the caller owns.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import CurrentUser, get_current_user
from ..db import get_session
from ..models import Edge, Graph, Node
from ..schemas import Graph as GraphSchema
from ..schemas import GLink, GNode, GraphSummary, Turn

router = APIRouter(prefix="/api", tags=["graph"])


def _to_gnode(n: Node) -> GNode:
    return GNode(
        id=str(n.id),
        label=n.heading,
        kind=n.kind,
        graphId=str(n.graph_id),
        turn=Turn(user=n.input_prompt, assistant=n.ai_output),
    )


@router.get("/graphs", response_model=list[GraphSummary])
async def list_graphs(
    session: AsyncSession = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> list[GraphSummary]:
    graphs = (
        await session.execute(
            select(Graph)
            .where(Graph.user_id == user.id)
            .order_by(Graph.created_at.desc())
        )
    ).scalars().all()
    return [GraphSummary(id=str(g.id), goal=g.goal) for g in graphs]


@router.get("/graph", response_model=GraphSchema)
async def get_graph(
    session: AsyncSession = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> GraphSchema:
    graph_ids = (
        await session.execute(select(Graph.id).where(Graph.user_id == user.id))
    ).scalars().all()
    if not graph_ids:
        # A user with no graph yet: empty is a valid graph, not an error.
        return GraphSchema(nodes=[], links=[])

    nodes = (
        await session.execute(select(Node).where(Node.graph_id.in_(graph_ids)))
    ).scalars().all()
    edges = (
        await session.execute(select(Edge).where(Edge.graph_id.in_(graph_ids)))
    ).scalars().all()
    return GraphSchema(
        nodes=[_to_gnode(n) for n in nodes],
        links=[GLink(source=str(e.source_id), target=str(e.target_id)) for e in edges],
    )


@router.get("/nodes/{node_id}", response_model=GNode)
async def get_node(
    node_id: str,
    session: AsyncSession = Depends(get_session),
    user: CurrentUser = Depends(get_current_user),
) -> GNode:
    node = await session.get(Node, node_id)
    if node is not None:
        graph = await session.get(Graph, node.graph_id)
    # Treat "not yours" the same as "not found" so we don't leak existence.
    if node is None or graph is None or graph.user_id != user.id:
        raise HTTPException(status_code=404, detail=f"unknown node: {node_id}")
    return _to_gnode(node)
