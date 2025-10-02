# routes/profils_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from utils.db_utils import query_db, execute_db

profils_bp = Blueprint("profils", __name__, url_prefix="/profils")

# 📌 Liste des profils
@profils_bp.route("/")
def liste_profils():
    profils = query_db("SELECT * FROM profils ORDER BY id ASC")
    return render_template("profils_list.html", profils=profils)

# 📌 Ajouter un profil
@profils_bp.route("/ajouter", methods=["POST"])
def ajouter_profil():
    nom = request.form.get("nom")
    description = request.form.get("description")
    build_ratio = request.form.get("build_ratio", 70)
    run_ratio = request.form.get("run_ratio", 30)
    heures_base = request.form.get("heures_base", 35)

    if not nom:
        flash("❌ Le nom du profil est obligatoire.", "danger")
        return redirect(url_for("profils.liste_profils"))

    try:
        execute_db("""
            INSERT INTO profils (nom, description, build_ratio, run_ratio, heures_base)
            VALUES (?, ?, ?, ?, ?)
        """, [nom, description, build_ratio, run_ratio, heures_base])
        flash("✅ Profil ajouté avec succès.", "success")
    except Exception as e:
        flash(f"❌ Erreur lors de l’ajout du profil : {e}", "danger")

    return redirect(url_for("profils.liste_profils"))

# 📌 Modifier un profil
@profils_bp.route("/modifier/<int:id>", methods=["POST"])
def modifier_profil(id):
    nom = request.form.get("nom")
    description = request.form.get("description")
    build_ratio = request.form.get("build_ratio", 70)
    run_ratio = request.form.get("run_ratio", 30)
    heures_base = request.form.get("heures_base", 35)

    try:
        execute_db("""
            UPDATE profils
            SET nom=?, description=?, build_ratio=?, run_ratio=?, heures_base=?
            WHERE id=?
        """, [nom, description, build_ratio, run_ratio, heures_base, id])
        flash("✅ Profil modifié avec succès.", "success")
    except Exception as e:
        flash(f"❌ Erreur lors de la modification du profil : {e}", "danger")

    return redirect(url_for("profils.liste_profils"))

# 📌 Supprimer un profil
@profils_bp.route("/supprimer/<int:id>", methods=["POST"])
def supprimer_profil(id):
    try:
        execute_db("DELETE FROM profils WHERE id = ?", [id])
        flash("✅ Profil supprimé avec succès.", "success")
    except Exception as e:
        flash(f"❌ Erreur lors de la suppression du profil : {e}", "danger")

    return redirect(url_for("profils.liste_profils"))
