# frontend

Two-mode app for Learning.AI: a force-directed knowledge graph and a chat view
that shows the conversation behind a graph node.

## Run

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
npm run build    # tsc + vite build
```

## Stack

- Vite + React 18 + TypeScript
- **react-force-graph-2d** (canvas + d3-force) — Obsidian-like graph
- **zustand** — tiny global store (mode, selected node, graph)
- tailwindcss

## Modes

- **Graph mode** (default): full-screen force graph. Hover highlights the
  1-hop neighborhood. Drag pins a node. Click a node to switch to chat mode
  with that node selected.
- **Chat mode**: shows the selected node's single user-message + assistant
  response. If nothing is selected, shows an empty-state hint.
- Toggle between modes with the **top-right button** (always visible).

## File map

```
src/
├── main.tsx              # React entry
├── App.tsx               # picks GraphView or ChatView based on store.mode
├── index.css             # tailwind directives
├── types.ts              # GNode, GLink, Graph, Turn, NodeKind, ViewMode
├── store.ts              # zustand store: mode, selectedNodeId, graph
├── mock/
│   └── graph.ts          # 9-node sample (derivatives)
├── api/
│   └── client.ts         # getGraph / selectNode stubs — the backend seam
├── views/
│   ├── GraphView.tsx     # ForceGraph2D canvas + hover/drag/click logic
│   └── ChatView.tsx      # selected-node Q&A or empty state
└── components/
    └── ModeToggle.tsx    # top-right button
```

## Backend swap

When a real backend exists, replace `src/api/client.ts` only — the function
shapes (`getGraph`, `selectNode`) are the contract. The store currently
seeds itself from the mock synchronously; switch it to call `getGraph()` on
mount once the network round-trip exists.

## Deferred

- Multi-turn conversations per node (data shape is 1:1 user→assistant for now)
- "First prompt seeds the graph" flow — empty state hints at it
- Persistence (refresh resets selection)
- Animation between modes (intentional — separate screens per design)
- Teacher/student split, auth
