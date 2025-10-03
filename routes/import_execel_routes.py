# routes/import_excel_routes.py

from flask import Blueprint, render_template, request, redirect, url_for, flash
import pandas as pd
import os
from werkzeug.utils import secure_filename
from utils.db_utils import execute_db, query_db
from datetime import datetime

import_bp = Blueprint("import", __name__, url_prefix="/import")

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@import_bp.route("/", methods=["GET", "POST"])
def import_excel():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            flash("Veuillez choisir un fichier Excel", "danger")
            return redirect(request.url)

        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        try:
            # Lire Excel
            df = pd.read_excel(filepath, header=None)

            # Exemple : récupération projet
            projet_data = {
                "ref_opg": df.iloc[1, 0],
                "titre_projet": df.iloc[1, 1],
                "description": df.iloc[1, 2],
                "id_release": df.iloc[1, 3],
                "id_programme": df.iloc[1, 4],
                "date_mep": df.iloc[1, 5],
            }

            execute_db("""
                INSERT INTO Projet (ref_opg, titre_projet, description, id_release, id_programme, date_mep, idate, iuser)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                projet_data["ref_opg"],
                projet_data["titre_projet"],
                projet_data["description"],
                projet_data["id_release"],
                projet_data["id_programme"],
                projet_data["date_mep"],
                datetime.now().date(),
                1
            ))

            projet_id = query_db("SELECT last_insert_rowid() as id", one=True)["id"]

            flash(f"Projet {projet_id} inséré ✅", "success")

        except Exception as e:
            flash(f"Erreur lors de l'import : {e}", "danger")

        return redirect(url_for("import.import_excel"))

    return render_template("import_excel.html")
