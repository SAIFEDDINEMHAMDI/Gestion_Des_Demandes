# routes/collaborateurs_routes.py
import sqlite3
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from utils.db_utils import query_db, execute_db
from utils.decorators import readonly_if_user  # ✅ ajout du décorateur

collab_bp = Blueprint('collaborateurs', __name__, url_prefix='/collaborateurs')


# -----------------------
# LISTE COLLABORATEURS AVEC PAGINATION + FILTRE + RECHERCHE
# -----------------------
@collab_bp.route('/')
def liste_collaborateurs():
    profil_id = request.args.get('profil_id', type=int)
    search = request.args.get('search', "").strip()
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page

    profils = query_db("SELECT * FROM profils ORDER BY nom")
    affectations = query_db("SELECT * FROM affectation ORDER BY nom")

    base_query = """
        SELECT c.matricule, c.nom, c.prenom, c.profil_id, c.affectation_id,
               p.nom AS profil, a.nom AS affectation
        FROM collaborateurs c
        JOIN profils p ON c.profil_id = p.id
        JOIN affectation a ON c.affectation_id = a.id
        WHERE 1=1
    """
    args = []

    if profil_id:
        base_query += " AND p.id = ?"
        args.append(profil_id)

    if search:
        base_query += " AND (c.matricule LIKE ? OR c.nom LIKE ? OR c.prenom LIKE ?)"
        args.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    # Total
    total = query_db(f"SELECT COUNT(*) as count FROM ({base_query})", args, one=True)['count']

    # Page courante
    collaborateurs = query_db(f"{base_query} ORDER BY c.rowid DESC LIMIT ? OFFSET ?", args + [per_page, offset])

    total_pages = (total // per_page) + (1 if total % per_page > 0 else 0)

    user_role = session.get('user', {}).get('role', '')

    return render_template(
        'collaborateurs/liste.html',
        collaborateurs=collaborateurs,
        profils=profils,
        affectations=affectations,
        profil_id=profil_id,
        search=search,
        page=page,
        total_pages=total_pages,
        user_role=user_role  # ✅ utile pour cacher les actions dans le template
    )


# -----------------------
# AJOUTER COLLABORATEUR
# -----------------------
@collab_bp.route('/ajouter', methods=['POST'])
@readonly_if_user
def ajouter_collaborateur():
    matricule = request.form['matricule']
    nom = request.form['nom']
    prenom = request.form['prenom']
    profil_id = request.form['profil_id']
    affectation_id = request.form['affectation_id']

    # Vérifier unicité matricule+profil
    existant = query_db(
        "SELECT * FROM collaborateurs WHERE matricule = ? AND profil_id = ?",
        [matricule, profil_id],
        one=True
    )
    if existant:
        flash("❌ Ce matricule existe déjà pour ce profil", "danger")
        return redirect(url_for('collaborateurs.liste_collaborateurs'))

    execute_db("""
        INSERT INTO collaborateurs (matricule, nom, prenom, profil_id, affectation_id)
        VALUES (?, ?, ?, ?, ?)
    """, [matricule, nom, prenom, profil_id, affectation_id])

    flash("✅ Collaborateur ajouté avec succès", "success")
    return redirect(url_for('collaborateurs.liste_collaborateurs'))


# -----------------------
# MODIFIER COLLABORATEUR
# -----------------------
@collab_bp.route('/modifier/<matricule>', methods=['POST'])
@readonly_if_user
def modifier_collaborateur(matricule):
    nom = request.form['nom']
    prenom = request.form['prenom']
    profil_id = request.form['profil_id']
    affectation_id = request.form['affectation_id']

    # Vérifier unicité matricule+profil
    existant = query_db(
        "SELECT * FROM collaborateurs WHERE matricule = ? AND profil_id = ? AND matricule != ?",
        [matricule, profil_id, matricule],
        one=True
    )
    if existant:
        flash("❌ Ce matricule existe déjà pour ce profil", "danger")
        return redirect(url_for('collaborateurs.liste_collaborateurs'))

    execute_db("""
        UPDATE collaborateurs
        SET nom = ?, prenom = ?, profil_id = ?, affectation_id = ?
        WHERE matricule = ?
    """, [nom, prenom, profil_id, affectation_id, matricule])

    flash("✅ Collaborateur mis à jour", "success")
    return redirect(url_for('collaborateurs.liste_collaborateurs'))


# -----------------------
# SUPPRIMER COLLABORATEUR
# -----------------------
@collab_bp.route('/supprimer/<matricule>', methods=['POST'])
@readonly_if_user
def supprimer_collaborateur(matricule):
    try:
        projets_lies = query_db(
            "SELECT COUNT(*) AS count FROM projets WHERE collaborateur_matricule = ?", [matricule], one=True
        )
        if projets_lies and projets_lies['count'] > 0:
            flash("❌ Ce collaborateur a des projets associés. Supprimez les projets d’abord.", "danger")
        else:
            execute_db("DELETE FROM collaborateurs WHERE matricule = ?", [matricule])
            flash("✅ Collaborateur supprimé avec succès", "success")
    except Exception as e:
        flash(f"❌ Erreur lors de la suppression : {e}", "danger")

    return redirect(url_for('collaborateurs.liste_collaborateurs'))
