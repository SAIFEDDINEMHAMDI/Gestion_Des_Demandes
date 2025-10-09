# routes/projet_routes.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from utils.db_utils import query_db, get_db

projet_bp = Blueprint("projet", __name__, url_prefix="/projet")


# ===============================
# Liste des projets
# ===============================
@projet_bp.route("/liste")
def liste_projets():
    projets = query_db("""
        SELECT 
            p.id,
            p.titre_projet AS titre,
            p.description AS categorie,
            IFNULL(p.score_wsjf_projet, 0) AS score_wsjf,
            p.date_mep AS date_mep,
            IFNULL(p.retenue, 'Non') AS retenu
        FROM Projet p
        ORDER BY p.id DESC
    """)
    return render_template("projets_liste.html", projet=projets)


# ===============================
# Bloc 1️⃣ - Modifier les infos principales du projet
# ===============================
@projet_bp.route("/modifier/<int:projet_id>", methods=["GET", "POST"])
def modifier_projet(projet_id):
    conn = get_db()
    cur = conn.cursor()

    # Charger le projet
    projet = query_db("SELECT * FROM Projet WHERE id = ?", [projet_id], one=True)
    if not projet:
        flash("❌ Projet introuvable.", "error")
        return redirect(url_for("projet.liste_projets"))

    # =============================
    # Charger les valeurs métier
    # =============================
    valeurs_selectionnees = query_db("""
        SELECT DISTINCT vmp.id_valeur_metier,
                        vm.libelle,
                        vm.type_libelle,
                        vm.valeur_libelle
        FROM valeur_metier_projet vmp
        JOIN valeur_metier vm ON vm.id = vmp.id_valeur_metier
        WHERE vmp.id_projet = ?
        ORDER BY vmp.id ASC
    """, [projet_id])

    valeurs_possibles = query_db("""
        SELECT DISTINCT libelle, id, type_libelle, valeur_libelle
        FROM valeur_metier
        WHERE type_libelle IS NOT NULL AND type_libelle <> ''
        ORDER BY libelle, id
    """)

    dropdowns = {}
    for v in valeurs_possibles:
        v_dict = dict(v)
        dropdowns.setdefault(v_dict["libelle"], []).append(v_dict)

    # =============================
    # Charger les complexités
    # =============================
    libelles_complexite = query_db("""
        SELECT DISTINCT libelle
        FROM complexite
        WHERE libelle IS NOT NULL AND libelle <> ''
        ORDER BY libelle
    """)

    complexites = []
    for l in libelles_complexite:
        lib = l["libelle"]
        valeur_existante = query_db("""
            SELECT 
                c.id AS id_complexite,
                c.libelle,
                c.type_libelle,
                c.valeur_libelle
            FROM complexite_projet cp
            JOIN complexite c ON c.id = cp.id_complexite
            WHERE cp.id_projet = ? AND c.libelle = ?
            LIMIT 1
        """, [projet_id, lib], one=True)

        if valeur_existante:
            complexites.append({
                "libelle": lib,
                "id_complexite": valeur_existante["id_complexite"],
                "type_libelle": valeur_existante["type_libelle"],
                "valeur_libelle": valeur_existante["valeur_libelle"]
            })
        else:
            complexites.append({
                "libelle": lib,
                "id_complexite": None,
                "type_libelle": None,
                "valeur_libelle": None
            })

    complexite_possibles = query_db("""
        SELECT DISTINCT libelle, id, type_libelle, valeur_libelle
        FROM complexite
        WHERE type_libelle IS NOT NULL AND type_libelle <> ''
        ORDER BY  id
    """)

    dropdowns_complexite = {}
    for c in complexite_possibles:
        c_dict = dict(c)
        dropdowns_complexite.setdefault(c_dict["libelle"], []).append(c_dict)

    # =============================
    # Bloc 1️⃣ : mise à jour du projet uniquement
    # =============================
    if request.method == "POST":
        titre = request.form.get("titre")
        description = request.form.get("description")
        categorie = request.form.get("categorie")
        statut = request.form.get("statut")

        cur.execute("""
            UPDATE Projet
            SET titre_projet = ?, description = ?, categorie = ?, statut = ?, 
                udate = DATETIME('now'), uuser = 1
            WHERE id = ?
        """, (titre, description, categorie, statut, projet_id))
        conn.commit()

        flash("✅ Informations du projet mises à jour avec succès.", "success")
        return redirect(url_for("projet.modifier_projet", projet_id=projet_id))

    return render_template(
        "projets_modifier.html",
        projet=projet,
        valeurs=valeurs_selectionnees,
        dropdowns=dropdowns,
        complexites=complexites,
        dropdowns_complexite=dropdowns_complexite
    )


# ===============================
# Bloc 2️⃣ - Mettre à jour une valeur métier à la fois
# ===============================
@projet_bp.route("/update_valeur/<int:projet_id>/<libelle>", methods=["POST"])
def update_valeur_metier(projet_id, libelle):
    conn = get_db()
    cur = conn.cursor()
    nouvelle_valeur_id = request.form.get("nouvelle_valeur_id")

    if not nouvelle_valeur_id:
        flash("⚠️ Aucune valeur sélectionnée.", "warning")
        return redirect(url_for("projet.modifier_projet", projet_id=projet_id))

    old_val = query_db("""
        SELECT vmp.id_valeur_metier
        FROM valeur_metier_projet vmp
        JOIN valeur_metier vm ON vm.id = vmp.id_valeur_metier
        WHERE vmp.id_projet = ? AND vm.libelle = ?
    """, [projet_id, libelle], one=True)

    if not old_val:
        cur.execute("""
            INSERT INTO valeur_metier_projet (id_projet, id_valeur_metier, idate, iuser)
            VALUES (?, ?, DATETIME('now'), 1)
        """, (projet_id, nouvelle_valeur_id))
        flash(f"🆕 Valeur '{libelle}' ajoutée avec succès.", "success")
    else:
        cur.execute("""
            UPDATE valeur_metier_projet
            SET id_valeur_metier = ?, udate = DATETIME('now'), uuser = 1
            WHERE id_projet = ? AND id_valeur_metier = ?
        """, (nouvelle_valeur_id, projet_id, old_val["id_valeur_metier"]))
        flash(f"✅ Valeur '{libelle}' mise à jour avec succès.", "success")

    conn.commit()
    return redirect(url_for("projet.modifier_projet", projet_id=projet_id))


@projet_bp.route("/update_all_complexites/<int:projet_id>", methods=["POST"])
def update_all_complexites(projet_id):
    conn = get_db()
    cur = conn.cursor()

    # 1️⃣ - Mettre à jour ou insérer les complexités du projet
    libelles_complexite = query_db("""
        SELECT DISTINCT libelle
        FROM complexite
        WHERE libelle IS NOT NULL AND libelle <> ''
    """)

    for l in libelles_complexite:
        lib = l["libelle"]
        valeur_id = request.form.get(f"complexite_{lib}")
        if not valeur_id:
            continue

        existing = query_db("""
            SELECT cp.id_complexite
            FROM complexite_projet cp
            JOIN complexite c ON c.id = cp.id_complexite
            WHERE cp.id_projet = ? AND c.libelle = ?
        """, [projet_id, lib], one=True)

        if existing:
            cur.execute("""
                UPDATE complexite_projet
                SET id_complexite = ?, udate = DATETIME('now'), uuser = 1
                WHERE id_projet = ? AND id_complexite = ?
            """, (valeur_id, projet_id, existing["id_complexite"]))
        else:
            cur.execute("""
                INSERT INTO complexite_projet (id_projet, id_complexite, idate, iuser)
                VALUES (?, ?, DATETIME('now'), 1)
            """, (projet_id, valeur_id))

    # ✅ 2️⃣ - Recalculer le score WSJF
    # Somme des valeurs métier pondérées
    somme_valeur_metier = query_db("""
        SELECT SUM(vm.valeur_libelle * vm.ponderation) AS total
        FROM valeur_metier_projet vmp
        JOIN valeur_metier vm ON vm.id = vmp.id_valeur_metier
        WHERE vmp.id_projet = ?
    """, [projet_id], one=True)["total"] or 0

    # Somme des complexités pondérées
    somme_complexite = query_db("""
        SELECT SUM(c.valeur_libelle * c.ponderation) AS total
        FROM complexite_projet cp
        JOIN complexite c ON c.id = cp.id_complexite
        WHERE cp.id_projet = ?
    """, [projet_id], one=True)["total"] or 1  # éviter division par 0

    # Calcul final
    score_wsjf = round(somme_valeur_metier / somme_complexite, 2)

    # Mise à jour du projet
    cur.execute("""
        UPDATE Projet
        SET score_wsjf_projet = ?, udate = DATETIME('now'), uuser = 1
        WHERE id = ?
    """, (score_wsjf, projet_id))

    conn.commit()

    flash(f"✅ Complexités enregistrées et score WSJF recalculé : {score_wsjf}", "success")
    return redirect(url_for("projet.modifier_projet", projet_id=projet_id))
