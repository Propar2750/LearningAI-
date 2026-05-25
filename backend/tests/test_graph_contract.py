async def test_graph_shape(client):
    r = await client.get("/api/graph")
    assert r.status_code == 200
    data = r.json()
    assert set(data.keys()) == {"nodes", "links"}

    ids = {n["id"] for n in data["nodes"]}
    assert {"n1", "n2", "n3"} <= ids

    for n in data["nodes"]:
        assert set(n.keys()) == {"id", "label", "kind", "turn"}
        assert n["kind"] in {"trunk", "side", "prereq"}
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
