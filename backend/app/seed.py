"""Idempotent dev seed: a tiny 3-node / 2-edge graph mirroring the frontend mock.

Run with: python -m app.seed   (from the backend/ directory)
"""

import asyncio

from .db import SessionLocal, engine
from .models import Edge, Graph, Node

GRAPH_ID = "g1"


async def seed() -> None:
    await _seed_g1()
    await _seed_g2()


async def _seed_g1() -> None:
    async with SessionLocal() as session:
        if await session.get(Graph, GRAPH_ID) is not None:
            print("seed: graph already present, skipping")
            return

        session.add(
            Graph(
                id=GRAPH_ID,
                user_id="dev-user",
                goal="Understand the basics of derivatives in calculus",
            )
        )
        await session.flush()  # ensure graph exists before nodes/edges reference it
        session.add_all(
            [
                Node(
                    id="n1",
                    graph_id=GRAPH_ID,
                    kind="trunk",
                    heading="What is a derivative?",
                    input_prompt="What is a derivative?",
                    ai_output=(
                        "A derivative measures the instantaneous rate of change of a "
                        "function — the slope of its graph at a single point."
                    ),
                    summary="Derivative = instantaneous rate of change (slope at a point).",
                    description=(
                        "The derivative of a function at a point is the slope of the "
                        "tangent line there, formalizing instantaneous rate of change."
                    ),
                    edge_value="Root concept; assume no prior calculus.",
                ),
                Node(
                    id="n2",
                    graph_id=GRAPH_ID,
                    kind="trunk",
                    heading="The power rule",
                    input_prompt="How do I differentiate x^n?",
                    ai_output=(
                        "Use the power rule: d/dx[x^n] = n * x^(n-1)."
                    ),
                ),
                Node(
                    id="n3",
                    graph_id=GRAPH_ID,
                    kind="side",
                    heading="Limit definition",
                    input_prompt="Where does the derivative actually come from?",
                    ai_output=(
                        "From the limit of the difference quotient: "
                        "f'(x) = lim(h->0) [f(x+h) - f(x)] / h."
                    ),
                ),
            ]
        )
        await session.flush()  # nodes must exist before edges reference them
        session.add_all(
            [
                Edge(graph_id=GRAPH_ID, source_id="n1", target_id="n2", edge_type="subtopic"),
                Edge(graph_id=GRAPH_ID, source_id="n1", target_id="n3", edge_type="side-question"),
            ]
        )
        await session.commit()
        print("seed: inserted graph g1 with 3 nodes / 2 edges")


GRAPH_ID_2 = "g2"


async def _seed_g2() -> None:
    """A second graph for the same dev user, so the multi-graph picker has
    something to switch between. Idempotent like the g1 seed above."""
    async with SessionLocal() as session:
        if await session.get(Graph, GRAPH_ID_2) is not None:
            print("seed: graph g2 already present, skipping")
            return

        session.add(
            Graph(
                id=GRAPH_ID_2,
                user_id="dev-user",
                goal="Learn the fundamentals of neural networks",
            )
        )
        await session.flush()
        session.add_all(
            [
                Node(
                    id="m1",
                    graph_id=GRAPH_ID_2,
                    kind="trunk",
                    heading="What is a neuron?",
                    input_prompt="What is an artificial neuron?",
                    ai_output=(
                        "An artificial neuron computes a weighted sum of its inputs, "
                        "adds a bias, and passes the result through an activation "
                        "function."
                    ),
                    summary="Neuron = weighted sum + bias, then activation.",
                    edge_value="Root concept; assume basic linear algebra.",
                ),
                Node(
                    id="m2",
                    graph_id=GRAPH_ID_2,
                    kind="trunk",
                    heading="Activation functions",
                    input_prompt="Why do we need activation functions?",
                    ai_output=(
                        "They introduce non-linearity so the network can model "
                        "relationships a stack of linear layers cannot."
                    ),
                ),
                Node(
                    id="m3",
                    graph_id=GRAPH_ID_2,
                    kind="side",
                    heading="Backpropagation",
                    input_prompt="How does a network learn?",
                    ai_output=(
                        "Backpropagation uses the chain rule to compute gradients of "
                        "the loss w.r.t. each weight, which gradient descent then "
                        "updates."
                    ),
                ),
            ]
        )
        await session.flush()
        session.add_all(
            [
                Edge(graph_id=GRAPH_ID_2, source_id="m1", target_id="m2", edge_type="subtopic"),
                Edge(graph_id=GRAPH_ID_2, source_id="m1", target_id="m3", edge_type="side-question"),
            ]
        )
        await session.commit()
        print("seed: inserted graph g2 with 3 nodes / 2 edges")


async def _main() -> None:
    await seed()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_main())
