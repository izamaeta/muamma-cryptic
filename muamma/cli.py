import json
from datetime import date, timedelta
from pathlib import Path

import click
from flask.cli import with_appcontext
from sqlalchemy import select

from muamma import clock
from muamma.extensions import db
from muamma.models import Admin, Puzzle
from muamma.puzzles import guide_example_warning
from muamma.security import hash_password
from muamma.text import normalize_answer

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

MIN_PASSWORD_LENGTH = 12

@click.command("create-admin")
@click.argument("email")
@click.password_option()
@with_appcontext
def create_admin(email, password):
    """Create an admin account."""
    email = email.strip().lower()
    if len(password) < MIN_PASSWORD_LENGTH:
        raise click.ClickException(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        )
    if db.session.scalar(select(Admin.id).where(Admin.email == email)):
        raise click.ClickException("An admin with this email already exists.")

    db.session.add(Admin(email=email, password_hash=hash_password(password)))
    db.session.commit()
    click.echo(f"Created admin {email}.")

# Everything a puzzle is, and nothing about who played it: plays, events and
# players stay in the database they were made in.
TRANSFER_FIELDS = (
    "kind",
    "status",
    "clue",
    "definition",
    "answer",
    "enumeration",
    "hints",
    "explanation",
    "technique",
    "difficulty",
)


def puzzle_record(puzzle: Puzzle) -> dict:
    record = {name: getattr(puzzle, name) for name in TRANSFER_FIELDS}
    # Kept for the reader's benefit. The import decides the dates itself.
    record["publish_date"] = (
        puzzle.publish_date.isoformat() if puzzle.publish_date else None
    )
    return record


def puzzle_fingerprint(kind: str, clue: str, answer: str) -> tuple[str, str, str]:
    """What makes two puzzles the same puzzle: the clue and its answer."""
    return (kind, " ".join(clue.split()).casefold(), normalize_answer(answer))


@click.command("export-puzzles")
@click.argument("path", type=click.Path(dir_okay=False, writable=True))
@with_appcontext
def export_puzzles(path):
    """Write every puzzle to a JSON file."""
    puzzles = db.session.scalars(
        select(Puzzle).order_by(Puzzle.kind, Puzzle.publish_date, Puzzle.id)
    )
    records = [puzzle_record(puzzle) for puzzle in puzzles]
    Path(path).write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    dailies = sum(1 for record in records if record["kind"] == "daily")
    click.echo(
        f"{len(records)} bulmaca yazıldı: {dailies} günlük, "
        f"{len(records) - dailies} tadımlık. Dosya: {path}"
    )


def read_records(path: str) -> list[dict]:
    try:
        records = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise click.ClickException(f"Dosya okunamadı: {error}") from error
    if not isinstance(records, list):
        raise click.ClickException("Dosyanın en üstünde bir bulmaca listesi bekleniyor.")

    required = set(TRANSFER_FIELDS) - {"definition", "status", "hints", "difficulty"}
    for number, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise click.ClickException(f"{number}. kayıt bir nesne değil.")
        missing = sorted(required - set(record))
        if missing:
            raise click.ClickException(
                f"{number}. kayıtta eksik alanlar: {', '.join(missing)}"
            )
        if record["kind"] not in ("daily", "practice"):
            raise click.ClickException(
                f"{number}. kaydın türü tanınmıyor: {record['kind']}"
            )
    return records


def free_days_from(first_day: date):
    """Days with no puzzle on them, starting at first_day."""
    taken = set(
        db.session.scalars(
            select(Puzzle.publish_date).where(Puzzle.publish_date >= first_day)
        )
    )
    day = first_day
    while True:
        if day not in taken:
            yield day
        day += timedelta(days=1)


@click.command("import-puzzles")
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--start",
    required=True,
    metavar="YYYY-MM-DD",
    help="Günlükler bu tarihten itibaren boş günlere yerleşir.",
)
@click.option("--dry-run", is_flag=True, help="Ne olacağını yaz, hiçbir şey kaydetme.")
@with_appcontext
def import_puzzles(path, start, dry_run):
    """Add puzzles from a JSON file written by export-puzzles."""
    try:
        first_day = date.fromisoformat(start)
    except ValueError:
        raise click.BadParameter(
            "YYYY-MM-DD biçiminde bir tarih ver.", param_hint="--start"
        ) from None

    records = read_records(path)
    seen = {
        puzzle_fingerprint(kind, clue, answer)
        for kind, clue, answer in db.session.execute(
            select(Puzzle.kind, Puzzle.clue, Puzzle.answer)
        ).all()
    }
    days = free_days_from(first_day)

    added = skipped = 0
    for record in records:
        fingerprint = puzzle_fingerprint(
            record["kind"], record["clue"], record["answer"]
        )
        if fingerprint in seen:
            skipped += 1
            click.echo(f"  atlandı (zaten var): {record['answer']} – {record['clue']}")
            continue
        seen.add(fingerprint)

        fields = {name: record.get(name) for name in TRANSFER_FIELDS}
        fields["status"] = record.get("status") or "draft"
        fields["hints"] = record.get("hints") or []
        fields["difficulty"] = record.get("difficulty") or 2
        if record["kind"] == "daily":
            fields["publish_date"] = next(days)
            where = fields["publish_date"].isoformat()
        else:
            fields["publish_date"] = None
            where = "tadımlık"

        db.session.add(Puzzle(**fields))
        added += 1
        click.echo(f"  {where}: {record['answer']} – {record['clue']}")

        warning = guide_example_warning(record["answer"])
        if warning:
            click.echo(f"    uyarı: {warning}")

    if dry_run:
        db.session.rollback()
        click.echo(f"Deneme: {added} bulmaca eklenecek, {skipped} atlanacak.")
        return

    db.session.commit()
    click.echo(f"{added} bulmaca eklendi, {skipped} atlandı.")
