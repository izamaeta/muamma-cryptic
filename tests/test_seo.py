def test_robots_txt(client):
    body = client.get("/robots.txt").get_data(as_text=True)
    assert "Disallow: /admin/" in body
    assert "Disallow: /api/" in body
    assert "Sitemap: https://muamma.test/sitemap.xml" in body


def test_sitemap_lists_pages(client):
    response = client.get("/sitemap.xml")
    assert response.mimetype == "application/xml"
    assert "<loc>https://muamma.test/nasil-oynanir</loc>" in response.get_data(as_text=True)


def test_sitemap_lists_the_new_pages(client):
    body = client.get("/sitemap.xml").get_data(as_text=True)
    assert "<loc>https://muamma.test/arsiv</loc>" in body
    assert "<loc>https://muamma.test/minute-cryptic-turkce</loc>" in body


def test_comparison_page_is_honest_and_disclaims_the_brand(client):
    html = client.get("/minute-cryptic-turkce").get_data(as_text=True)
    assert "Türkçe bir sürümü bulunmuyor" in html
    assert "Muamma, Minute Cryptic ile bağlantılı değildir." in html
    assert "Minute Cryptic adı ve markası sahiplerine aittir." in html


def test_phone_menu_holds_the_main_links(client):
    html = client.get("/").get_data(as_text=True)
    menu = html[html.index('class="nav-menu-panel"') : html.index("</details>")]
    for target in ("/tadimlik", "/arsiv", "/nasil-oynanir"):
        assert f'href="{target}"' in menu
    assert 'class="stats-open"' in menu


def test_footer_keeps_its_links(client):
    html = client.get("/").get_data(as_text=True)
    footer = html[html.index('class="site-footer"') :]
    for target in ("/tadimlik", "/arsiv", "/nasil-oynanir", "/minute-cryptic-turkce", "/gizlilik"):
        assert f'href="{target}"' in footer


def test_pages_have_canonical_and_share_tags(client):
    html = client.get("/nasil-oynanir").get_data(as_text=True)
    assert '<link rel="canonical" href="https://muamma.test/nasil-oynanir">' in html
    assert '<meta property="og:title" content="Muamma nasıl çözülür? Cryptic bulmaca rehberi">' in html


def test_personal_pages_are_not_indexed(client):
    html = client.get("/tadimlik").get_data(as_text=True)
    assert '<meta name="robots" content="noindex, follow">' in html


def test_the_stats_page_moved_into_the_window(client):
    response = client.get("/istatistik")
    assert response.status_code == 301
    assert response.headers["Location"] == "/"


def test_missing_page_uses_custom_404(client):
    response = client.get("/boyle-bir-sayfa-yok")
    assert response.status_code == 404
    assert "Bu sayfa bir muamma" in response.get_data(as_text=True)


def test_privacy_page_shows_contact(client):
    html = client.get("/gizlilik").get_data(as_text=True)
    assert "iletisim@muamma.test" in html