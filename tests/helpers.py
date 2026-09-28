from datetime import date

from muamma.extensions import db
from muamma.models import Puzzle

TODAY = date(2026, 10, 10)


def add_puzzle(**overrides):
    fields = {
        "kind": "daily",
        "status": "ready",
        "clue": "Karıncanın içinde saklanan bal yapıcı",
        "definition": "bal yapıcı",
        "answer": "ARI",
        "enumeration": "3",
        "explanation": "k-ARI-nca",
        "technique": "hidden",
        "publish_date": TODAY,
    }
    fields.update(overrides)
    puzzle = Puzzle(**fields)
    db.session.add(puzzle)
    db.session.commit()
    return puzzle