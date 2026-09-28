from muamma import create_app
from muamma.config import TestConfig
from muamma.extensions import db
from tests.helpers import add_puzzle


class CsrfConfig(TestConfig):
    WTF_CSRF_ENABLED = True


def test_api_requires_csrf_token():
    app = create_app(CsrfConfig)
    with app.app_context():
        db.create_all()
        puzzle = add_puzzle()
        response = app.test_client().post(
            f"/api/puzzles/{puzzle.id}/guess", json={"guess": "arı"}
        )
        assert response.status_code == 400