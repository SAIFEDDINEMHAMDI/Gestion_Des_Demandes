# routes/import_excel_routes.py
from datetime import datetime
import os
import pandas as pd
import sqlite3
from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.utils import secure_filename
import uuid
import unicodedata
from difflib import SequenceMatcher
from utils.db_utils import get_db

# ------------------------------------------------------------
# 📦 Blueprint & dossier uploads
# ------------------------------------------------------------
import_excel_bp = Blueprint("import_excel", __name__, url_prefix="/import")
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ------------------------------------------------------------
# 🔠 Fonctions utilitaires
# ------------------------------------------------------------
def normalize_text(text):
    """Nettoie et normalise les textes (accents, espaces, majuscules...)."""
    if text is None:
        return ""
    text = str(text).strip()
    if text.lower() == "nan":
        return ""
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("_", " ").replace("-", " ").replace("’", "'").replace("œ", "oe")
    text = " ".join(text.split())
    return text


def similar(a, b, seuil=0.9):
    """Retourne True si deux chaînes sont suffisamment similaires."""
    if not a or not b:
        return False
    return SequenceMatcher(None, a, b).ratio() >= seuil


# ------------------------------------------------------------
# 🔧 ROUTE PRINCIPALE : Import Excel
# ------------------------------------------------------------
@import_excel_bp.route("/", methods=["GET", "POST"])
def import_excel():
    if request.method == "POST":
        file = request.files.get("file")
        if not file:
            flash("❌ Aucun fichier sélectionné.", "error")
            return redirect(url_for("import_excel.import_excel"))

        # ✅ Nom unique pour éviter les collisions
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_name = f"{name}_{timestamp}{ext}"

        filepath = os.path.join(UPLOAD_FOLDER, unique_name)
        file.save(filepath)

        # 📖 Lecture Excel
        try:
            df = pd.read_excel(filepath)
        except Exception as e:
            flash(f"❌ Erreur de lecture Excel : {e}", "error")
            return redirect(url_for("import_excel.import_excel"))

        log_path = os.path.join(UPLOAD_FOLDER, "import_debug.txt")
        with open(log_path, "w", encoding="utf-8") as debug:
            debug.write("=== DEBUG IMPORT LOG ===\n\n")

            # ------------------------------------------------------------
            # 🧩 Normalisation colonnes
            # ------------------------------------------------------------
            df.columns = [normalize_text(c) for c in df.columns]
            debug.write(f"🔎 Colonnes normalisées : {df.columns.tolist()}\n\n")

            required = [
                "ref ogp",
                "nomencalture du projet",
                "description du projet",
                "date de mep prevue",
            ]
            for r in required:
                if r not in df.columns:
                    flash(f"❌ Colonne manquante : {r}", "error")
                    debug.write(f"❌ Colonne manquante : {r}\n")
                    return redirect(url_for("import_excel.import_excel"))

            # ------------------------------------------------------------
            # 🧹 Nettoyage avant import
            # ------------------------------------------------------------
            conn = get_db()
            cur = conn.cursor()
            cur.execute("PRAGMA foreign_keys = ON")
            cur.execute("DELETE FROM valeur_metier_projet")
            cur.execute("DELETE FROM complexite_projet")
            cur.execute("DELETE FROM Projet")
            conn.commit()
            debug.write("🧹 Anciennes données supprimées.\n\n")

            # ------------------------------------------------------------
            # 📚 Chargement valeurs métier
            # ------------------------------------------------------------
            vm = pd.read_sql_query(
                "SELECT id, libelle, type_libelle, valeur_libelle FROM valeur_metier",
                conn,
            )
            for col in ["libelle", "type_libelle", "valeur_libelle"]:
                vm[col] = vm[col].astype(str).apply(normalize_text)
            debug.write(f"📚 {len(vm)} valeurs métier chargées.\n\n")

            # ------------------------------------------------------------
            # 🧠 Détection blocs projet (1 projet = 3 lignes)
            # ------------------------------------------------------------
            projects = []
            i = 0
            while i < len(df):
                ref = str(df.iloc[i].get("ref ogp", "")).strip()
                if ref and ref.lower() != "nan":
                    projects.append(df.iloc[i:i + 3])
                    i += 3
                else:
                    i += 1
            debug.write(f"📊 {len(projects)} blocs projet détectés.\n\n")

            total_links = 0

            # ------------------------------------------------------------
            # 🔁 Parcours projets
            # ------------------------------------------------------------
            for p_idx, chunk in enumerate(projects, start=1):
                meta = chunk.iloc[0]
                ref_opg = str(meta.get("ref ogp", "")).strip()
                titre = str(meta.get("nomencalture du projet", "")).strip()
                desc = str(meta.get("description du projet", "")).strip()

                # ✅ Conversion de la date Excel
                date_raw = meta.get("date de mep prevue")
                if pd.notna(date_raw):
                    if isinstance(date_raw, pd.Timestamp):
                        date_mep = date_raw.strftime("%Y-%m-%d")
                    else:
                        date_mep = str(date_raw)
                else:
                    date_mep = None

                debug.write(f"\n=== Aperçu du bloc projet {p_idx} ===\n")
                debug.write(f"{chunk.reset_index(drop=True).to_string(index=True)}\n\n")

                debug.write(f"--- Projet {p_idx}: {titre} ({ref_opg}) ---\n")

                # 🔹 Insertion du projet
                cur.execute(
                    """
                    INSERT INTO Projet (ref_opg, titre_projet, description, date_mep, idate)
                    VALUES (?, ?, ?, ?, DATETIME('now'))
                    """,
                    (ref_opg, titre, desc, date_mep),
                )
                conn.commit()
                id_projet = cur.lastrowid

                # --------------------------------------------------------
                # 🔍 Lecture des valeurs métier (corrigée)
                # --------------------------------------------------------
                for col in df.columns:
                    if col in required or col in ["nom du departement", "type de la demande"]:
                        continue

                    # ligne 0 → type (texte)
                    # ligne 2 → valeur (numérique)
                    type_vals = [
                        str(v).strip()
                        for v in chunk.iloc[0:1][col].tolist()
                        if str(v).strip() and str(v).strip().lower() != "nan"
                    ]

                    valeur_vals = [
                        str(v).strip()
                        for v in chunk.iloc[2:3][col].tolist()
                        if str(v).strip() and str(v).strip().lower() != "nan"
                    ]

                    type_libelle = " ".join(type_vals)
                    valeur_libelle = " ".join(valeur_vals)

                    # Normalisation
                    lib_n = normalize_text(col)
                    type_n = normalize_text(type_libelle)
                    val_n = normalize_text(valeur_libelle)

                    debug.write(f"🔍 {col} :: type='{type_libelle}' | valeur='{valeur_libelle}'\n")

                    if not type_n and not val_n:
                        debug.write("❌ aucun match (vides)\n")
                        continue

                    # Recherche exacte puis floue
                    match = vm[
                        vm.apply(
                            lambda r: (
                                r["libelle"] == lib_n
                                and (r["type_libelle"] == type_n or not type_n)
                                and (r["valeur_libelle"] == val_n or not val_n)
                            ),
                            axis=1,
                        )
                    ]

                    if match.empty:
                        match = vm[
                            vm.apply(
                                lambda r: similar(r["libelle"], lib_n)
                                and (not type_n or similar(r["type_libelle"], type_n))
                                and (not val_n or similar(r["valeur_libelle"], val_n)),
                                axis=1,
                            )
                        ]

                    if not match.empty:
                        vm_id = int(match.iloc[0]["id"])
                        cur.execute(
                            """
                            INSERT OR IGNORE INTO valeur_metier_projet (id_projet, id_valeur_metier, idate)
                            VALUES (?, ?, DATETIME('now'))
                            """,
                            (id_projet, vm_id),
                        )
                        total_links += 1
                        debug.write(f"🟩 match id={vm_id}\n")
                    else:
                        debug.write("❌ aucun match\n")

                conn.commit()
                debug.write("\n")

            debug.write(f"✅ Import terminé : {len(projects)} projets, {total_links} liens créés.\n")

        flash(f"✅ Import terminé : {len(projects)} projets, {total_links} liens créés.", "success")
        return redirect(url_for("projet.liste_projets"))

    return render_template("import_excel.html")
