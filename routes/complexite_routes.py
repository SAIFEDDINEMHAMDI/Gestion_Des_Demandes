# routes/complexite_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from utils.db_utils import query_db, execute_db
from datetime import datetime

complexite_bp = Blueprint('complexite', __name__, url_prefix='/complexite')

# -----------------------
# LISTE AVEC PAGINATION + RECHERCHE
# -----------------------
@complexite_bp.route('/')
def liste_complexite():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page
    search = request.args.get('q', '').strip()

    base_query = "SELECT * FROM Complexite"
    args = []
    if search:
        base_query += """
            WHERE libelle LIKE ? 
               OR type_libelle LIKE ? 
               OR valeur_libelle LIKE ? 
               OR CAST(ponderation AS TEXT) LIKE ?
               OR CAST(macro_estimation AS TEXT) LIKE ?
        """
        args.extend([f"%{search}%"] * 5)

    total = query_db(f"SELECT COUNT(*) as count FROM ({base_query})", args, one=True)['count']
    complexites = query_db(f"{base_query} ORDER BY idate DESC LIMIT ? OFFSET ?", args + [per_page, offset])

    total_pages = (total // per_page) + (1 if total % per_page > 0 else 0)

    return render_template(
        'complexite_list.html',
        complexites=complexites,
        page=page,
        total_pages=total_pages
    )

# -----------------------
# AJOUTER
# -----------------------
@complexite_bp.route('/ajouter', methods=['POST'])
def ajouter_valeur():
    libelle = request.form['libelle']
    type_libelle = request.form['type_libelle']
    valeur_libelle = request.form['valeur_libelle']
    ponderation = request.form['ponderation']
    macro_estimation = request.form['macro_estimation']
    iuser = 1
    idate = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    execute_db("""
        INSERT INTO Complexite (libelle, type_libelle, valeur_libelle, ponderation, macro_estimation, iuser, idate)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [libelle, type_libelle, valeur_libelle, ponderation, macro_estimation, iuser, idate])

    flash("✅ Complexité ajoutée avec succès", "success")
    return redirect(url_for('complexite.liste_complexite'))

# -----------------------
# MODIFIER
# -----------------------
@complexite_bp.route('/modifier/<int:id>', methods=['POST'])
def modifier_valeur(id):
    libelle = request.form['libelle']
    type_libelle = request.form['type_libelle']
    valeur_libelle = request.form['valeur_libelle']
    ponderation = request.form['ponderation']
    macro_estimation = request.form['macro_estimation']
    uuser = 1
    udate = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    execute_db("""
        UPDATE Complexite 
        SET libelle=?, type_libelle=?, valeur_libelle=?, ponderation=?, macro_estimation=?, uuser=?, udate=?
        WHERE id=?
    """, [libelle, type_libelle, valeur_libelle, ponderation, macro_estimation, uuser, udate, id])

    flash("✅ Complexité mise à jour", "success")
    return redirect(url_for('complexite.liste_complexite'))

# -----------------------
# SUPPRIMER
# -----------------------
@complexite_bp.route('/supprimer/<int:id>', methods=['POST'])
def supprimer_valeur(id):
    execute_db("DELETE FROM Complexite WHERE id=?", [id])
    flash("❌ Complexité supprimée", "danger")
    return redirect(url_for('complexite.liste_complexite'))
