from datetime import timedelta

import click
from flask.cli import with_appcontext
from sqlalchemy import select

from muamma import clock
from muamma.extensions import db
from muamma.models import Puzzle

DEMO_DAILY = [
    (
        -1,
        {
            "clue": "Bozuk kalem, söz demek",
            "definition": "söz",
            "answer": "KELAM",
            "enumeration": "5",
            "hints": ["'Bozuk' kelimesi harflerin karışacağını işaret ediyor."],
            "explanation": "KALEM'in harfleri karışınca KELAM olur. Tanım: söz.",
            "technique": "anagram",
            "difficulty": 1,
        },
    ),
    (
        0,
        {
            "clue": "Karıncanın içinde saklanan bal yapıcı",
            "definition": "bal yapıcı",
            "answer": "ARI",
            "enumeration": "3",
            "hints": ["'İçinde saklanan' gizli bir kelimeye işaret ediyor."],
            "explanation": "kARInca kelimesinin içinde ARI saklı. Tanım: bal yapıcı.",
            "technique": "hidden",
            "difficulty": 1,
        },
    ),
    (
        1,
        {
            "clue": "Kaçamakta gizlenen ağaç",
            "definition": "ağaç",
            "answer": "ÇAM",
            "enumeration": "3",
            "hints": ["'Gizlenen' kelimesi cevabın ipucunun içinde olduğunu söylüyor."],
            "explanation": "kaÇAMakta kelimesinin içinde ÇAM saklı. Tanım: ağaç.",
            "technique": "hidden",
            "difficulty": 1,
        },
    ),
]

DEMO_PRACTICE = [
    {
        "clue": "Satıcıda saklı binek",
        "definition": "binek",
        "answer": "AT",
        "enumeration": "2",
        "hints": ["'Saklı' kelimesi gizli bir kelimeye işaret ediyor."],
        "explanation": "sATıcıda kelimesinin içinde AT saklı. Tanım: binek.",
        "technique": "hidden",
        "difficulty": 1,
    },
]


@click.command("seed-demo")
@with_appcontext
def seed_demo():
    """Insert demo puzzles around today's date."""
    today = clock.today()
    added = 0

    for offset, fields in DEMO_DAILY:
        day = today + timedelta(days=offset)
        if db.session.scalar(select(Puzzle.id).where(Puzzle.publish_date == day)):
            continue
        db.session.add(Puzzle(kind="daily", status="ready", publish_date=day, **fields))
        added += 1

    for fields in DEMO_PRACTICE:
        exists = db.session.scalar(
            select(Puzzle.id).where(Puzzle.kind == "practice", Puzzle.answer == fields["answer"])
        )
        if exists:
            continue
        db.session.add(Puzzle(kind="practice", status="ready", **fields))
        added += 1

    db.session.commit()
    click.echo(f"Added {added} demo puzzles.")