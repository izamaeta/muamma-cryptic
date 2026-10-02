import json
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from muamma.extensions import db
from muamma.models import Event, Play, Player, Puzzle
from tests.helpers import TODAY, add_puzzle

START = date(2026, 11, 1)


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


def written(tmp_path, records):
    path = tmp_path / "bulmacalar.json"
    path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    return str(path)


def record(**overrides):
    fields = {
        "kind": "daily",
        "status": "ready",
        "clue": "Bozuk kalem, söz demek",
        "definition": "söz",
        "answer": "KELAM",
        "enumeration": "5",
        "hints": ["Bozuk, harflerin karışacağını söylüyor."],
        "explanation": "KALEM karışınca KELAM olur.",
        "technique": "anagram",
        "difficulty": 2,
        "publish_date": "2026-01-01",
    }
    fields.update(overrides)
    return fields


def dailies_by_day():
    rows = db.session.execute(
        select(Puzzle.publish_date, Puzzle.answer).where(Puzzle.kind == "daily")
    ).all()
    return {day: answer for day, answer in rows}


def test_export_writes_every_puzzle(runner, tmp_path):
    add_puzzle(answer="ARI")
    add_puzzle(kind="practice", answer="ELMA", publish_date=None, clue="Tadımlık")

    path = tmp_path / "cikti.json"
    result = runner.invoke(args=["export-puzzles", str(path)])

    assert result.exit_code == 0, result.output
    records = json.loads(path.read_text(encoding="utf-8"))
    assert {entry["answer"] for entry in records} == {"ARI", "ELMA"}
    assert "2 bulmaca yazıldı" in result.output


def test_export_leaves_players_behind(runner, tmp_path):
    """A puzzle travels; who played it does not."""
    puzzle = add_puzzle()
    player = Player(current_streak=3)
    db.session.add(player)
    db.session.flush()
    db.session.add(Play(player=player, puzzle=puzzle, status="solved"))
    db.session.add(
        Event(player_id=player.id, puzzle_id=puzzle.id, type="guess", data={"guess": "ODAK"})
    )
    db.session.commit()

    path = tmp_path / "cikti.json"
    runner.invoke(args=["export-puzzles", str(path)])
    text = path.read_text(encoding="utf-8")

    assert str(player.id) not in text
    assert "ODAK" not in text
    for forbidden in ("player", "plays", "event", "solved"):
        assert forbidden not in text


def test_import_fills_free_days_from_the_start(runner, tmp_path):
    path = written(
        tmp_path,
        [
            record(answer="KELAM", clue="Bir"),
            record(answer="ODAK", clue="İki"),
            record(answer="SAKAL", clue="Üç"),
        ],
    )

    result = runner.invoke(args=["import-puzzles", path, "--start", START.isoformat()])

    assert result.exit_code == 0, result.output
    assert dailies_by_day() == {
        START: "KELAM",
        START + timedelta(days=1): "ODAK",
        START + timedelta(days=2): "SAKAL",
    }


def test_import_steps_over_days_that_are_taken(runner, tmp_path):
    add_puzzle(answer="ARI", publish_date=START + timedelta(days=1))
    path = written(
        tmp_path,
        [record(answer="KELAM", clue="Bir"), record(answer="ODAK", clue="İki")],
    )

    runner.invoke(args=["import-puzzles", path, "--start", START.isoformat()])

    assert dailies_by_day() == {
        START: "KELAM",
        START + timedelta(days=1): "ARI",
        START + timedelta(days=2): "ODAK",
    }


def test_import_ignores_the_dates_in_the_file(runner, tmp_path):
    path = written(tmp_path, [record(publish_date="2020-05-05")])

    runner.invoke(args=["import-puzzles", path, "--start", START.isoformat()])

    assert dailies_by_day() == {START: "KELAM"}


def test_practice_puzzles_arrive_without_a_date(runner, tmp_path):
    path = written(
        tmp_path,
        [
            record(kind="practice", answer="ODAK", clue="Tadımlık", publish_date=None),
            record(answer="KELAM", clue="Günlük"),
        ],
    )

    runner.invoke(args=["import-puzzles", path, "--start", START.isoformat()])

    practice = db.session.scalar(select(Puzzle).where(Puzzle.kind == "practice"))
    assert practice.publish_date is None
    assert dailies_by_day() == {START: "KELAM"}


def test_the_same_puzzle_is_not_added_twice(runner, tmp_path):
    path = written(tmp_path, [record(), record(answer="ODAK", clue="İki")])

    first = runner.invoke(args=["import-puzzles", path, "--start", START.isoformat()])
    second = runner.invoke(args=["import-puzzles", path, "--start", START.isoformat()])

    assert "2 bulmaca eklendi, 0 atlandı" in first.output
    assert "0 bulmaca eklendi, 2 atlandı" in second.output
    assert db.session.scalar(select(db.func.count()).select_from(Puzzle)) == 2


def test_a_file_that_repeats_itself_adds_one_puzzle(runner, tmp_path):
    # Same clue, written with different spacing and a lower case answer.
    path = written(
        tmp_path,
        [record(), record(clue="Bozuk  kalem,  söz   demek", answer="kelam")],
    )

    runner.invoke(args=["import-puzzles", path, "--start", START.isoformat()])

    assert db.session.scalar(select(db.func.count()).select_from(Puzzle)) == 1


def test_dry_run_changes_nothing(runner, tmp_path):
    path = written(tmp_path, [record(), record(answer="ODAK", clue="İki")])

    result = runner.invoke(
        args=["import-puzzles", path, "--start", START.isoformat(), "--dry-run"]
    )

    assert result.exit_code == 0, result.output
    assert "Deneme: 2 bulmaca eklenecek" in result.output
    assert START.isoformat() in result.output
    assert db.session.scalar(select(db.func.count()).select_from(Puzzle)) == 0


def test_import_warns_about_a_guide_example(runner, tmp_path):
    path = written(tmp_path, [record(answer="ARI", clue="Karıncada saklı bal yapıcı")])

    result = runner.invoke(args=["import-puzzles", path, "--start", START.isoformat()])

    assert "uyarı" in result.output
    assert "rehber sayfasında" in result.output
    # A warning, not a refusal.
    assert db.session.scalar(select(db.func.count()).select_from(Puzzle)) == 1


def test_import_says_nothing_about_an_unused_answer(runner, tmp_path):
    path = written(tmp_path, [record()])

    result = runner.invoke(args=["import-puzzles", path, "--start", START.isoformat()])

    assert "uyarı" not in result.output


def test_a_broken_date_is_refused(runner, tmp_path):
    path = written(tmp_path, [record()])

    result = runner.invoke(args=["import-puzzles", path, "--start", "1 Kasım"])

    assert result.exit_code != 0
    assert "YYYY-MM-DD" in result.output
    assert db.session.scalar(select(db.func.count()).select_from(Puzzle)) == 0


@pytest.mark.parametrize(
    ("records", "message"),
    [
        ([{"kind": "daily"}], "eksik alanlar"),
        ([record(kind="haftalık")], "türü tanınmıyor"),
        ({"kind": "daily"}, "bulmaca listesi"),
    ],
)
def test_a_file_that_makes_no_sense_is_refused(runner, tmp_path, records, message):
    result = runner.invoke(
        args=["import-puzzles", written(tmp_path, records), "--start", START.isoformat()]
    )

    assert result.exit_code != 0
    assert message in result.output
    assert db.session.scalar(select(db.func.count()).select_from(Puzzle)) == 0


def test_export_and_import_make_the_same_puzzles(runner, tmp_path):
    """The round trip: what comes back is what went out, on new dates."""
    add_puzzle(answer="ARI", publish_date=TODAY)
    add_puzzle(
        kind="practice", answer="ELMA", publish_date=None, clue="Tadımlık ipucu"
    )
    path = tmp_path / "ara.json"
    runner.invoke(args=["export-puzzles", str(path)])

    for puzzle in db.session.scalars(select(Puzzle)):
        db.session.delete(puzzle)
    db.session.commit()

    runner.invoke(args=["import-puzzles", str(path), "--start", START.isoformat()])

    puzzles = {p.answer: p for p in db.session.scalars(select(Puzzle))}
    assert set(puzzles) == {"ARI", "ELMA"}
    assert puzzles["ARI"].publish_date == START
    assert puzzles["ARI"].technique == "hidden"
    assert puzzles["ELMA"].publish_date is None
