def test_robots_txt(client):
    body = client.get("/robots.txt").get_data(as_text=True)
    assert "Disallow: /admin/" in body
    assert "Disallow: /api/" in body
    assert "Sitemap: https://muamma.test/sitemap.xml" in body


def test_sitemap_lists_pages(client):
    response = client.get("/sitemap.xml")
    assert response.mimetype == "application/xml"
    assert "<loc>https://muamma.test/nasil-oynanir</loc>" in response.get_data(as_text=True)


def test_pages_have_canonical_and_share_tags(client):
    html = client.get("/nasil-oynanir").get_data(as_text=True)
    assert '<link rel="canonical" href="https://muamma.test/nasil-oynanir">' in html
    assert '<meta property="og:title" content="Nasıl oynanır – Muamma">' in html


def test_personal_pages_are_not_indexed(client):
    html = client.get("/istatistik").get_data(as_text=True)
    assert '<meta name="robots" content="noindex, follow">' in html


def test_missing_page_uses_custom_404(client):
    response = client.get("/boyle-bir-sayfa-yok")
    assert response.status_code == 404
    assert "Bu sayfa bir muamma" in response.get_data(as_text=True)


def test_privacy_page_shows_contact(client):
    html = client.get("/gizlilik").get_data(as_text=True)
    assert "iletisim@muamma.test" in html