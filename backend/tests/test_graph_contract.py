async def test_graph_shape(client):
    r = await client.get("/api/graph")
    assert r.status_code == 200
    data = r.json()
    assert set(data.keys()) == {"nodes", "links"}

    ids = {n["id"] for n in data["nodes"]}
    assert {"n1", "n2", "n3"} <= ids

    for n in data["nodes"]:
        assert set(n.keys()) == {"id", "label", "kind", "graphId", "turn"}
        assert n["kind"] in {"trunk", "side", "prereq"}
        assert n["graphId"]  # every node names its owning graph
        assert set(n["turn"].keys()) == {"user", "assistant"}

    assert len(data["links"]) >= 2
    for link in data["links"]:
        assert set(link.keys()) == {"source", "target"}
        # edges collapse to links; endpoints must be real nodes
        assert link["source"] in ids
        assert link["target"] in ids


async def test_get_node(client):
    r = await client.get("/api/nodes/n1")
    assert r.status_code == 200
    n = r.json()
    assert n["id"] == "n1"
    assert n["kind"] == "trunk"
    assert n["turn"]["user"]
    assert n["turn"]["assistant"]


async def test_get_node_404(client):
    r = await client.get("/api/nodes/does-not-exist")
    assert r.status_code == 404


async def test_list_graphs(client):
    r = await client.get("/api/graphs")
    assert r.status_code == 200
    graphs = r.json()
    by_id = {g["id"]: g for g in graphs}
    # dev-user owns both seeded graphs
    assert {"g1", "g2"} <= set(by_id)
    for g in graphs:
        assert set(g.keys()) == {"id", "goal"}
        assert g["goal"]


async def test_list_graphs_requires_auth(anon_client):
    r = await anon_client.get("/api/graphs")
    assert r.status_code == 401


async def test_list_graphs_scoped_to_user(auth_as):
    from tests.conftest import _client

    auth_as("someone-else")  # a user who owns no graphs
    async with _client() as c:
        r = await c.get("/api/graphs")
    assert r.status_code == 200
    assert r.json() == []
