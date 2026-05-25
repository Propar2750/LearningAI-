"""Pydantic response models — mirror the frontend contract in
``frontend/src/types.ts`` exactly (Graph / GNode / GLink / Turn)."""

from pydantic import BaseModel


class Turn(BaseModel):
    user: str
    assistant: str


class GNode(BaseModel):
    id: str
    label: str
    kind: str
    turn: Turn


class GLink(BaseModel):
    source: str
    target: str


class Graph(BaseModel):
    nodes: list[GNode]
    links: list[GLink]
