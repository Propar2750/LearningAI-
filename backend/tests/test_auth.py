"""Auth + ownership-isolation tests for the graph endpoints."""


async def test_graph_requires_auth(anon_client):
    r = await anon_client.get("/api/graph")
    assert r.status_code == 401


async def test_node_requires_auth(anon_client):
    r = await anon_client.get("/api/nodes/n1")
    assert r.status_code == 401


async def test_other_user_sees_empty_graph(auth_as):
    from tests.conftest import _client

    auth_as("some-other-user")
    async with _client() as c:
        r = await c.get("/api/graph")
    assert r.status_code == 200
    assert r.json() == {"nodes": [], "links": []}


async def test_other_user_cannot_read_owned_node(auth_as):
    from tests.conftest import _client

    auth_as("some-other-user")
    async with _client() as c:
        r = await c.get("/api/nodes/n1")  # n1 belongs to dev-user's seed graph
    assert r.status_code == 404
