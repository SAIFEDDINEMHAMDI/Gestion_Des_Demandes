# routes/valeurs_metier_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from utils.db_utils import query_db, execute_db

valeurs_bp = Blueprint('valeurs_metier', __name__, url_prefix='/valeurs')


# -----------------------
# LISTE AVEC PAGINATION
# -----------------------
@valeurs_bp.route('/')
def liste_valeurs():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page
    search = request.args.get('q', '').strip()

    base_query = "SELECT * FROM valeur_metier"
    args = []
    if search:
        base_query += " WHERE libelle LIKE ? OR CAST(ponderation AS TEXT) LIKE ?"
        args.extend([f"%{search}%", f"%{search}%"])

    total = query_db(f"SELECT COUNT(*) as count FROM ({base_query})", args, one=True)['count']
    valeurs = query_db(f"{base_query} ORDER BY idate DESC, udate DESC LIMIT ? OFFSET ?", args + [per_page, offset])

    total_pages = (total // per_page) + (1 if total % per_page > 0 else 0)

    return render_template(
        'valeur_metier_list.html',
        valeurs=valeurs,
        page=page,
        total_pages=total_pages,
        search=search
    )


# -----------------------
# ROUTE DE RECHERCHE DYNAMIQUE
# -----------------------
@valeurs_bp.route('/search')
def search_valeurs():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page
    query = request.args.get('q', '').strip()

    base_query = "SELECT * FROM valeur_metier"
    args = []
    if query:
        base_query += " WHERE libelle LIKE ? OR CAST(ponderation AS TEXT) LIKE ?"
        args.extend([f"%{query}%", f"%{query}%"])

    total = query_db(f"SELECT COUNT(*) as count FROM ({base_query})", args, one=True)['count']
    valeurs = query_db(f"{base_query} ORDER BY idate DESC, udate DESC LIMIT ? OFFSET ?", args + [per_page, offset])

    total_pages = (total // per_page) + (1 if total % per_page > 0 else 0)

    return render_template(
        'partials/valeurs_table.html',
        valeurs=valeurs,
        page=page,
        total_pages=total_pages
    )


# -----------------------
# AJOUTER
# -----------------------
@valeurs_bp.route('/ajouter', methods=['POST'])
def ajouter_valeur():
    libelle = request.form['libelle']
    ponderation = request.form['ponderation']
    user = session.get('user', {}).get('username', 'inconnu')

    execute_db("""
        INSERT INTO valeur_metier (libelle, ponderation, iuser, idate, uuser, udate)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, CURRENT_TIMESTAMP)
    """, [libelle, ponderation, user, user])

    flash("✅ Valeur métier ajoutée avec succès", "success")
    return redirect(url_for('valeurs_metier.liste_valeurs'))


# -----------------------
# MODIFIER
# -----------------------
@valeurs_bp.route('/modifier/<id>', methods=['POST'])
def modifier_valeur(id):
    libelle = request.form['libelle']
    ponderation = request.form['ponderation']
    user = session.get('user', {}).get('username', 'inconnu')

    execute_db("""
        UPDATE valeur_metier
        SET libelle = ?, ponderation = ?, uuser = ?, udate = CURRENT_TIMESTAMP
        WHERE id = ?
    """, [libelle, ponderation, user, id])

    flash("✅ Valeur métier mise à jour", "success")
    return redirect(url_for('valeurs_metier.liste_valeurs'))


# -----------------------
# SUPPRIMER
# -----------------------
@valeurs_bp.route('/supprimer/<id>', methods=['POST'])
def supprimer_valeur(id):
    execute_db("DELETE FROM valeur_metier WHERE id = ?", [id])
    flash("✅ Valeur métier supprimée", "success")
    return redirect(url_for('valeurs_metier.liste_valeurs'))
