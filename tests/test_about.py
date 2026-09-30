import pytest

from tests.helpers import TODAY, add_puzzle

PAGES = [
    "/",
    "/arsiv",
    "/nasil-oynanir",
    "/muamma-nedir",
    "/gizlilik",
    "/istatistik",
    "/boyle-bir-sayfa-yok",
]


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr("muamma.clock.today", lambda: TODAY)


@pytest.fixture
def about_html(client):
    return client.get("/muamma-nedir").get_data(as_text=True)


def test_the_comparison_page_is_gone(client):
    assert client.get("/minute-cryptic-turkce").status_code == 404


def test_the_other_product_is_not_named_anywhere(client):
    add_puzzle()
    practice = add_puzzle(kind="practice", publish_date=None)

    for path in [*PAGES, f"/tadimlik/{practice.id}"]:
        html = client.get(path, follow_redirects=True).get_data(as_text=True)
        assert "minute cryptic" not in html.lower(), path

    body = client.get("/sitemap.xml").get_data(as_text=True)
    assert "minute" not in body.lower()


def test_about_page_opens_with_the_story(about_html):
    assert "Mühürlü bir kelimenin hikâyesi" in about_html
    assert "Bu bilmecelerin adı" in about_html
    assert "yüzyıllık bir kelime geleneğinin bugünkü hali" in about_html


def test_about_page_has_every_section(about_html):
    for heading in (
        "Her gün bir mühür, her mühürde bir sır",
        "Her gece yarısı yeni bir muamma mühürlenir",
        "Bir de kedimiz var",
    ):
        assert heading in about_html


def test_removed_sections_are_gone(about_html):
    for heading in ("Sade ve sana ait", "Sık sorulanlar"):
        assert heading not in about_html
    assert "<summary>" not in about_html
    assert "iletisim@muamma.test" not in about_html


def test_about_page_cards_and_rhythm(about_html):
    for card in ("Tek ipucu", "İki yol, bir cevap", "Harflerle düşün"):
        assert card in about_html
    for item in ("Günün muamması", "Seri", "Haftanın çetin muamması", "Tadımlık ve arşiv"):
        assert item in about_html
    assert about_html.count('class="about-card"') == 3


def test_about_page_closes_with_the_puzzle(about_html):
    assert "Mühür seni bekliyor." in about_html
    assert "Bugünün muammasını çöz" in about_html


def test_about_page_is_linked_and_listed(client):
    html = client.get("/").get_data(as_text=True)

    nav = html[html.index('class="site-nav"') : html.index("</nav>", html.index('class="site-nav"'))]
    assert 'href="/muamma-nedir"' in nav

    menu = html[html.index('class="nav-menu-panel"') : html.index("</details>")]
    assert 'href="/muamma-nedir"' in menu

    footer = html[html.index('class="site-footer"') :]
    assert 'href="/muamma-nedir"' in footer

    body = client.get("/sitemap.xml").get_data(as_text=True)
    assert "<loc>https://muamma.test/muamma-nedir</loc>" in body


def test_guide_points_at_the_story_instead_of_telling_it(client):
    html = client.get("/nasil-oynanir").get_data(as_text=True)
    assert "İsim nereden geliyor?" not in html
    assert "Adı nereden geliyor?" in html
    assert 'href="/muamma-nedir"' in html


def test_top_nav_marks_the_current_page(client):
    html = client.get("/muamma-nedir").get_data(as_text=True)
    nav = html[html.index('class="site-nav"') : html.index("</nav>", html.index('class="site-nav"'))]
    assert 'href="/muamma-nedir" aria-current="page"' in nav


def test_privacy_drops_the_account_section_but_keeps_the_facts(client):
    html = client.get("/gizlilik").get_data(as_text=True)

    assert "Hesap açmadan oynarsın" not in html
    cookies = html[html.index("Hangi çerezler var?") : html.index("Hangi verileri")]
    assert "ilk tahminini yaptığında" in cookies
    assert "serini ve istatistiklerini hatırlamak" in cookies
    assert "hiçbir bilgi içermez" in cookies
