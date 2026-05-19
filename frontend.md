# Frontend — Implementation Log (v0)

This file is the map of the v0 frontend: what was built, where each piece
lives, and why. Read this first before changing anything under `frontend/`.

The plan that drove this work is at
`~/.claude/plans/clever-squishing-aho.md`. Design source of truth is
`DESIGN.md` at the repo root and the drawio sketch `Overall.drawio`.

---

## Status

Code is written but **not verified to build** — this machine has no `node`/`npm`
installed. Before first run:

```bash
# install node (e.g. nvm)
cd frontend
npm install
npm run dev          # http://localhost:5173
npm run build        # tsc + vite build
```

If something doesn't compile, check this file first — the names below should
match the files on disk.

---

## Stack

- **Vite** + **React 18** + **TypeScript**
- **React Flow** (`reactflow`) — graph canvas
- **d3-force** — force-directed layout sim
- **framer-motion** — shared-element animation (chat card ↔ graph node)
  via `layoutId`, plus `AnimatePresence` for view switches
- **zustand** — single in-memory store
- **tailwindcss** — styling

Config files: `package.json`, `vite.config.ts`, `tsconfig.json`,
`tsconfig.node.json`, `tailwind.config.js`, `postcss.config.js`, `index.html`.

---

## Locked design decisions (from planning session)

1. **Layout mode:** toggle (chat default), not two-pane.
2. **Graph layout:** force-directed (Obsidian-like). Trunk nodes are **pinned**
   on a vertical spine; non-trunk nodes re-simulate on each new node, using
   previous positions as seeds so existing nodes don't jump.
3. **Graph interaction:** single-click highlights ancestor chain (dim
   non-ancestors to 30%); double-click focuses node and switches to chat view.
4. **Chat view:** no breadcrumb / no branch indicator. Reads identically
   regardless of where you are in the graph.
5. **Prompt input:** floating, visible in both views. In chat mode it shows
   "continuing: <node summary>". In graph mode it shows "auto (router
   decides)" — the backend owns parent selection.
6. **Backend:** mocked entirely in the frontend behind a stable API surface so
   swapping to a real backend is a one-file change.
7. **Routing:** the frontend never picks a parent. The router (currently a
   stub in `api/client.ts`) returns `{node, edge}` and the frontend renders
   what it gets.

---

## File map

```
frontend/
├── package.json
├── vite.config.ts
├── tsconfig.json / tsconfig.node.json
├── tailwind.config.js / postcss.config.js
├── index.html
└── src/
    ├── main.tsx                       # React entry; imports reactflow css
    ├── App.tsx                        # AnimatePresence host, view toggle, hotkeys
    ├── index.css                      # tailwind directives
    ├── types.ts                       # GraphNode, GraphEdge, EdgeType, Goal, Graph, ViewMode
    ├── store.ts                       # zustand store (graph, positions, mode, focus, highlight)
    ├── mock/
    │   └── graph.ts                   # seed graph: trunk of 4 + 3 side qs + 1 prereq
    ├── api/
    │   └── client.ts                  # getGraph, postPrompt (stub router)
    ├── graph/
    │   ├── trunk.ts                   # trunkNodes, trunkTip, isTrunkEdge
    │   ├── ancestors.ts               # getAncestorChain, getAllAncestors
    │   └── layout.ts                  # recompute(graph, prevPositions) → positions
    ├── views/
    │   ├── ChatView.tsx               # ancestor-chain stack of cards
    │   └── GraphView.tsx              # React Flow canvas, CardNode, click handlers
    └── components/
        ├── GoalBanner.tsx             # fixed top banner (goal text)
        └── PromptInput.tsx            # fixed bottom input with target indicator
```

---

## How the pieces fit together

### Data flow

1. `mock/graph.ts` exports `mockGraph`. `api/client.ts` keeps an in-memory
   `state` initialized from it; `getGraph()` returns a deep clone.
2. `store.ts` calls `recompute()` once at module load to seed `positions`.
3. User submits via `PromptInput` → `store.submitPrompt(prompt)`.
4. `submitPrompt` calls `api.postPrompt({prompt, focusedNodeId})`, refetches
   the graph, re-runs `recompute(graph, prevPositions)`, and in chat mode
   moves focus to the newly returned node.

### Stub router (`api/client.ts` → `postPrompt`)

- If `focusedNodeId` is on the trunk tip → new node continues the trunk
  (`isTrunk: true`, edge type `subtopic`).
- Otherwise → new node attaches under the focused node (or trunk tip if no
  focus) as a `side-question`.
- This is intentionally dumb. The real backend's router LLM (DESIGN.md
  §"Routing") replaces this whole function — and only this function. The
  `PostPromptInput` / `PostPromptResult` shapes are the contract.

### Layout (`graph/layout.ts`)

- Trunk nodes get `fx`/`fy` at `(0, i * 160)`, pinning them.
- Non-trunk nodes: seeded near their first parent if new, otherwise reused
  from `prev` map. d3-force runs 200 ticks with link/charge/collide/center
  forces, then writes back final positions.
- `recompute` is called from `store.ts` at init and after every
  `submitPrompt`. It's pure: takes `(graph, prev)`, returns a new map.

### Views

- **ChatView**: picks an anchor (`focusedNodeId` ?? trunk tip ?? first node),
  walks `getAncestorChain` (first-parent path), renders each as a card. Each
  card has `layoutId={node.id}`.
- **GraphView**: React Flow with a custom `CardNode` type. Same
  `layoutId={node.id}` on the visible card, so Framer Motion can morph
  between the chat-card layout and the graph-node layout when `mode` changes.
  Edges styled per type via `EDGE_STYLE` map. Single-click → `highlightNode`;
  double-click → `focusNode` + `setMode('chat')`; pane click → clear
  highlight.
- Highlight effect: when `highlightedNodeId` is set, `getAllAncestors` is
  computed and any node outside that set has its `opacity` animated to 0.3.

### App-level concerns

- `App.tsx` owns the view toggle button, the `cmd/ctrl + \`` hotkey, and the
  `esc` shortcut (chat → graph).
- `GoalBanner` and `PromptInput` are rendered outside `AnimatePresence` so
  they persist across mode switches.

---

## Adding a new feature — where to look

| Task | Touch |
| --- | --- |
| Replace mock with real backend | `src/api/client.ts` only — keep the function signatures |
| New edge type | `src/types.ts` (`EdgeType`), `src/views/GraphView.tsx` (`EDGE_STYLE`) |
| Change graph layout (e.g. dagre) | `src/graph/layout.ts` (`recompute` is the only consumer) |
| Change how chat picks its anchor | `src/views/ChatView.tsx` (the `anchor` line) |
| Different highlight rule | `src/graph/ancestors.ts` (`getAllAncestors`) + GraphView's `ancestorSet` memo |
| Tweak trunk pinning | `src/graph/layout.ts` (`TRUNK_X`, `TRUNK_SPACING`) |
| Router behavior (until backend exists) | `src/api/client.ts` (`postPrompt`) |
| New hotkey / toggle behavior | `src/App.tsx` `useEffect` |
| Persist across reloads | currently in-memory only; would wrap `api/client.ts` over localStorage or fetch |

---

## Known gaps / deferred

- No tests yet.
- No persistence — refresh loses any user-added nodes.
- Force sim runs synchronously on the main thread (200 ticks). Fine for
  small graphs; move to a worker if it gets sluggish past ~100 nodes.
- `getAncestorChain` follows only the first parent. Multi-parent DAGs render
  fine in graph view but chat view shows just one path.
- No teacher/student split, no multi-graph sidebar, no auth (drawio v1+).
- Build not verified on this machine (no node/npm here). First contributor
  to install node should run `npm install && npm run build` and fix any
  version drift in `package.json`.
