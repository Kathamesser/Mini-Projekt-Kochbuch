"""Datenmodell und Datenbankzugriff für das Kochbuch.

Gespeichert wird in einer SQLite-Datei (kochbuch.db) mit zwei Tabellen:
- rezepte: ein Eintrag pro Rezept
- zutaten: ein Eintrag pro Zutat, verknüpft über rezept_id
"""

import sqlite3
from dataclasses import dataclass, field

DATENBANK = "kochbuch.db"

KATEGORIEN = ["Vorspeise", "Hauptgericht", "Dessert", "Backen", "Getränk", "Sonstiges"]


@dataclass
class Zutat:
    menge: float | None   # z. B. 500  (None, wenn keine Menge angegeben, z. B. "Salz")
    einheit: str          # z. B. "g"
    bezeichnung: str      # z. B. "Mehl"

    def als_text(self):
        """Gibt die Zutat lesbar zurück, z. B. '500 g Mehl'."""
        teile = []
        if self.menge is not None:
            # 500.0 -> "500", 0.5 -> "0.5"
            teile.append(f"{self.menge:g}")
        if self.einheit:
            teile.append(self.einheit)
        teile.append(self.bezeichnung)
        return " ".join(teile)


@dataclass
class Rezept:
    titel: str
    kategorie: str
    dauer: int | None
    anleitung: str
    zutaten: list[Zutat] = field(default_factory=list)
    id: int | None = None  # wird von der Datenbank vergeben


# ---------------------------------------------------------------------------
# Datenbank
# ---------------------------------------------------------------------------

def verbindung():
    con = sqlite3.connect(DATENBANK)
    con.row_factory = sqlite3.Row  # Zeilen wie Dictionaries ansprechen: zeile["titel"]
    con.execute("PRAGMA foreign_keys = ON")
    return con


def datenbank_anlegen():
    """Legt die Tabellen an, falls es sie noch nicht gibt."""
    with verbindung() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS rezepte (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                titel     TEXT NOT NULL,
                kategorie TEXT,
                dauer     INTEGER,
                anleitung TEXT
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS zutaten (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                rezept_id   INTEGER NOT NULL REFERENCES rezepte(id) ON DELETE CASCADE,
                position    INTEGER NOT NULL,
                menge       REAL,
                einheit     TEXT,
                bezeichnung TEXT NOT NULL
            )
        """)


def alle_rezepte():
    """Liefert alle Rezepte (ohne Zutaten), alphabetisch sortiert – für das Menü."""
    with verbindung() as con:
        zeilen = con.execute(
            "SELECT * FROM rezepte ORDER BY titel COLLATE NOCASE"
        ).fetchall()
    return [_rezept_aus_zeile(z) for z in zeilen]


def rezept_laden(rezept_id):
    """Liefert ein Rezept mit allen Zutaten oder None, wenn es die ID nicht gibt."""
    with verbindung() as con:
        zeile = con.execute("SELECT * FROM rezepte WHERE id = ?", (rezept_id,)).fetchone()
        if zeile is None:
            return None
        rezept = _rezept_aus_zeile(zeile)
        for z in con.execute(
            "SELECT * FROM zutaten WHERE rezept_id = ? ORDER BY position", (rezept_id,)
        ):
            rezept.zutaten.append(Zutat(z["menge"], z["einheit"], z["bezeichnung"]))
    return rezept


def rezept_speichern(rezept):
    """Speichert ein neues Rezept (id ist None) oder aktualisiert ein vorhandenes.

    Gibt die ID des Rezepts zurück.
    """
    with verbindung() as con:
        if rezept.id is None:
            cursor = con.execute(
                "INSERT INTO rezepte (titel, kategorie, dauer, anleitung) VALUES (?, ?, ?, ?)",
                (rezept.titel, rezept.kategorie, rezept.dauer, rezept.anleitung),
            )
            rezept.id = cursor.lastrowid
        else:
            con.execute(
                "UPDATE rezepte SET titel = ?, kategorie = ?, dauer = ?, anleitung = ? WHERE id = ?",
                (rezept.titel, rezept.kategorie, rezept.dauer, rezept.anleitung, rezept.id),
            )
            # Einfachster Weg: alte Zutaten löschen und alle neu eintragen.
            con.execute("DELETE FROM zutaten WHERE rezept_id = ?", (rezept.id,))

        for position, zutat in enumerate(rezept.zutaten):
            con.execute(
                "INSERT INTO zutaten (rezept_id, position, menge, einheit, bezeichnung) "
                "VALUES (?, ?, ?, ?, ?)",
                (rezept.id, position, zutat.menge, zutat.einheit, zutat.bezeichnung),
            )
    return rezept.id


def rezept_loeschen(rezept_id):
    """Löscht ein Rezept; die Zutaten werden über ON DELETE CASCADE mitgelöscht."""
    with verbindung() as con:
        con.execute("DELETE FROM rezepte WHERE id = ?", (rezept_id,))


def _rezept_aus_zeile(zeile):
    return Rezept(
        id=zeile["id"],
        titel=zeile["titel"],
        kategorie=zeile["kategorie"],
        dauer=zeile["dauer"],
        anleitung=zeile["anleitung"] or "",
    )
