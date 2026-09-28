def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_index(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Muamma" in response.get_data(as_text=True)