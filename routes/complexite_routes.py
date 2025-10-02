from flask import Blueprint, render_template, request, redirect, url_for
from utils.db_utils import query_db, execute_db

complexite_bp = Blueprint("complexite", __name__ , url_prefix='/complexite')

# Liste avec pagination et recherche
@complexite_bp.route("/")
def liste_complexite():
    page = request.args.get("page", 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page
    search = request.args.get("q", "").strip()

    base_query = "SELECT * FROM complexite"
    args = []

    if search:
        base_query += " WHERE libelle LIKE ? OR CAST(ponderation AS TEXT) LIKE ?"
        args.extend([f"%{search}%", f"%{search}%"])

    total = query_db(f"SELECT COUNT(*) as count FROM ({base_query})", args, one=True)["count"]

    complexites = query_db(
        f"{base_query} ORDER BY idate DESC LIMIT ? OFFSET ?",
        args + [per_page, offset]
    )

    total_pages = (total // per_page) + (1 if total % per_page > 0 else 0)

    return render_template(
        "complexite_list.html",
        complexites=complexites,
        page=page,
        total_pages=total_pages
    )

# Ajouter une complexité
@complexite_bp.route("/ajouter", methods=["POST"])
def ajouter_complexite():
    libelle = request.form.get("libelle")
    type_libelle = request.form.get("type_libelle")
    valeur_libelle = request.form.get("valeur_libelle")
    ponderation = request.form.get("ponderation")

    execute_db(
        "INSERT INTO complexite (libelle, type_libelle, valeur_libelle, ponderation, idate, iuser) VALUES (?, ?, ?, ?, datetime('now'), 1)",
        (libelle, type_libelle, valeur_libelle, ponderation),
    )
    return redirect(url_for("complexite.liste_complexite"))

# Modifier une complexité
@complexite_bp.route("/modifier/<int:id>", methods=["POST"])
def modifier_complexite(id):
    type_libelle = request.form.get("type_libelle")
    valeur_libelle = request.form.get("valeur_libelle")
    ponderation = request.form.get("ponderation")

    execute_db(
        "UPDATE complexite SET type_libelle=?, valeur_libelle=?, ponderation=?, udate=datetime('now'), uuser=1 WHERE id=?",
        (type_libelle, valeur_libelle, ponderation, id),
    )
    return redirect(url_for("complexite.liste_complexite"))

# Supprimer une complexité
@complexite_bp.route("/supprimer/<int:id>", methods=["POST"])
def supprimer_complexite(id):
    execute_db("DELETE FROM complexite WHERE id=?", (id,))
    return redirect(url_for("complexite.liste_complexite"))
