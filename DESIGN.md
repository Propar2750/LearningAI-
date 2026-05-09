# Learning.AI — Design Notes

A framework that lets an LLM answer questions across a graph of conversation
nodes, so studying a topic can move fluidly between deep-dives and the bigger
picture (Prezi-style navigation, Obsidian-style graph).

Secondary benefit: by feeding only the relevant slice of the graph to the LLM
on each turn, token usage stays bounded instead of growing with full history.

---

## Core concept

- A normal-feeling chat interface on top of a graph of past turns.
- After each user prompt, a router decides whether the new turn extends the
  current "trunk" or forks a side branch.
- The user can zoom out to a graph view, jump to any node, and continue from
  there.
- Prompts are designed for tutoring: the goal is correct-on-the-first-go
  answers, with side questions branching off without polluting the trunk.

---

## Locked decisions

### Nodes
- One node = one user prompt + one LLM reply.
- Nodes are **immutable** once written.

### Graph
- Directed acyclic graph. A node can have **multiple parents**.
- Edge types (stored on the edge):
  - `subtopic`
  - `prerequisite`
  - `see-also`
  - `side-question`

### Goal
- One goal per graph.
- Set once at session start, immutable except via an explicit user command.
- Stored as **metadata** (not as a node), consulted by every routing decision.

### Routing
- After each reply, the system decides `{parent_node_id, edge_type}`.
- The LLM's routing decision is **final** — no user override at decision time.
  (User can still navigate the graph manually afterwards.)

### Summaries
- Each node stores a compressed summary, used when it appears as context for
  some other node rather than as the focus.

### MVP shape
- UI-first. This is meant to be a tool the user actually uses, not a terminal
  experiment.
- Build the backbone (UI + graph storage + basic routing) before tuning the
  intelligence.

---

## Open questions / TBD

Deliberately deferred — placeholders are fine for v0, decide later.

### Context selection scheme
Starter proposal (not adopted yet):
- Always include: goal.
- Ancestor chain: full text for the last 1–2 turns, summaries for older.
- Prerequisite-edge neighbors: summaries.
- Sibling summaries under the same parent (so the model knows what's covered).
- Auto-linked "see-also" nodes: summaries when match is strong.
- Drop the subtree below the current node.
- Possibly re-summarize on demand using the current question for better
  fidelity at higher token cost.

### Correctness / critic pass
- Whether to run a critic pass on trunk nodes (cost ~2× tokens) to enforce
  "correct first go." Side-question nodes likely single-pass.

### Auto-linking mechanics
- How a new prompt finds and links to an existing distant node.
- Candidates: embedding similarity over node summaries, LLM-as-judge over a
  shortlist, or embed-to-shortlist + LLM-to-pick.
- When auto-link fires: jump to that node, or stay put and just draw a
  cross-link edge?

---

## Pending UI / stack questions

To answer before building v0:

1. Web app vs desktop (Electron/Tauri).
2. Frontend framework (React / Svelte / other).
3. Backend language (Python FastAPI / Node) and LLM provider.
4. Storage (SQLite vs JSON files vs Postgres).
5. Two-pane (chat + graph always visible) vs toggle (chat default, zoom out
   to graph).
6. Graph library (React Flow, Cytoscape, D3, vis-network).
7. Behavior when zooming into a node from the graph: scroll chat to it, or
   open a focused view of node + ancestors.
8. Multiple graphs per user (sidebar list) vs one-graph-at-a-time.

---

## Proposed v0 backbone

- Single graph, single goal set at creation.
- Linear chat. After each LLM reply, a "router" LLM call returns
  `{parent_node_id, edge_type}`. Stub implementation: always trunk.
- Graph view shows nodes as boxes titled with the prompt, edges colored by
  type.
- Clicking a node focuses the chat there; the next prompt continues from that
  node.
- SQLite stores nodes, edges, summaries, goal.
- Summarization runs async after each reply.
