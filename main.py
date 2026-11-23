"""Kochbuch – Flask-Webanwendung.

Starten mit:  python main.py
Dann im Browser öffnen:  http://127.0.0.1:5000
"""

from flask import Flask, abort, redirect, render_template, request, url_for

import models
from models import Rezept, Zutat

app = Flask(__name__)


@app.route("/")
def menue():
    return render_template("menü.html", rezepte=models.alle_rezepte())


@app.route("/rezept")
def rezept_auswaehlen():
    """Wird vom Auswahl-Formular im Menü aufgerufen (?rezept_id=...)."""
    rezept_id = request.args.get("rezept_id", type=int)
    if rezept_id is None:
        return redirect(url_for("menue"))
    return redirect(url_for("rezept_anzeigen", rezept_id=rezept_id))


@app.route("/rezept/<int:rezept_id>")
def rezept_anzeigen(rezept_id):
    rezept = models.rezept_laden(rezept_id)
    if rezept is None:
        abort(404)
    return render_template("rezept_ansicht.html", rezept=rezept)


@app.route("/rezept/neu", methods=["GET", "POST"])
def rezept_neu():
    if request.method == "POST":
        rezept = rezept_aus_formular()
        rezept_id = models.rezept_speichern(rezept)
        return redirect(url_for("rezept_anzeigen", rezept_id=rezept_id))
    return render_template("rezept_anlegen.html", rezept=None, kategorien=models.KATEGORIEN)


@app.route("/rezept/<int:rezept_id>/bearbeiten", methods=["GET", "POST"])
def rezept_bearbeiten(rezept_id):
    rezept = models.rezept_laden(rezept_id)
    if rezept is None:
        abort(404)
    if request.method == "POST":
        neues_rezept = rezept_aus_formular()
        neues_rezept.id = rezept_id
        models.rezept_speichern(neues_rezept)
        return redirect(url_for("rezept_anzeigen", rezept_id=rezept_id))
    return render_template("rezept_anlegen.html", rezept=rezept, kategorien=models.KATEGORIEN)


@app.route("/rezept/<int:rezept_id>/loeschen", methods=["POST"])
def rezept_loeschen(rezept_id):
    models.rezept_loeschen(rezept_id)
    return redirect(url_for("menue"))


def rezept_aus_formular():
    """Baut aus den Formulardaten ein Rezept-Objekt (noch ohne ID)."""
    titel = request.form["titel"].strip()
    kategorie = request.form.get("kategorie", "")
    dauer = request.form.get("dauer", type=int)  # None, wenn leer
    anleitung = request.form.get("anleitung", "").strip()

    # Alle Zutaten-Zeilen haben dieselben Feldnamen -> wir bekommen Listen.
    # Der i-te Eintrag jeder Liste gehört zur selben Zutat.
    mengen = request.form.getlist("menge")
    einheiten = request.form.getlist("einheit")
    bezeichnungen = request.form.getlist("bezeichnung")

    zutaten = []
    for menge, einheit, bezeichnung in zip(mengen, einheiten, bezeichnungen):
        if not bezeichnung.strip():
            continue  # leere Zeilen überspringen
        zutaten.append(Zutat(
            menge=float(menge.replace(",", ".")) if menge.strip() else None,
            einheit=einheit.strip(),
            bezeichnung=bezeichnung.strip(),
        ))

    return Rezept(titel=titel, kategorie=kategorie, dauer=dauer,
                  anleitung=anleitung, zutaten=zutaten)


if __name__ == "__main__":
    models.datenbank_anlegen()
    app.run(debug=True)
