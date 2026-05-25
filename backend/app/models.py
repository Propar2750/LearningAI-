"""SQLAlchemy ORM models.

Schema is richer than the frontend contract (it carries edge types, a per-graph
goal, and per-node summaries from DESIGN.md); the API layer collapses it down to
the frontend's Graph/GNode/GLink shapes. Nodes are immutable once written.
"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NODE_KINDS = ("trunk", "side", "prereq")
EDGE_TYPES = ("subtopic", "prerequisite", "see-also", "side-question")


class Base(DeclarativeBase):
    pass


class Graph(Base):
    __tablename__ = "graphs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True)  # Supabase auth uid later
    goal: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    graph_id: Mapped[str] = mapped_column(
        ForeignKey("graphs.id", ondelete="CASCADE"), index=True
    )
    heading: Mapped[str] = mapped_column(String)  # ~5 words; frontend `label`
    kind: Mapped[str] = mapped_column(String)
    input_prompt: Mapped[str] = mapped_column(Text)  # frontend `turn.user`
    ai_output: Mapped[str] = mapped_column(Text)  # frontend `turn.assistant`
    # Context to inject when this node is the focus (node-scoped). Nullable.
    edge_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)  # ~100 words
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)  # ~20 words
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(f"kind IN {NODE_KINDS}", name="ck_nodes_kind"),
    )


class Edge(Base):
    __tablename__ = "edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    graph_id: Mapped[str] = mapped_column(
        ForeignKey("graphs.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[str] = mapped_column(
        ForeignKey("nodes.id", ondelete="CASCADE"), index=True
    )
    target_id: Mapped[str] = mapped_column(
        ForeignKey("nodes.id", ondelete="CASCADE"), index=True
    )
    edge_type: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(f"edge_type IN {EDGE_TYPES}", name="ck_edges_edge_type"),
        UniqueConstraint(
            "source_id", "target_id", "edge_type", name="uq_edges_src_tgt_type"
        ),
    )
