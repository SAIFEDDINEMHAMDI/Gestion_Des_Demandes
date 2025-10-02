# routes/caf.py
from flask import Blueprint, render_template, request
from datetime import date, timedelta, datetime
from utils.db_utils import query_db, execute_db  # Assure-toi que execute_db existe
import calendar

caf_bp = Blueprint('caf', __name__, url_prefix='/caf')

from flask import Blueprint, render_template, request
from datetime import date, timedelta
from utils.db_utils import query_db

caf_bp = Blueprint('caf', __name__, url_prefix='/caf')

@caf_bp.route('/automatique')
def caf_automatique():
    annee = 2025
    mois_labels = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]

    # Récupérer le filtre depuis l'URL
    mois_filtre = request.args.get('mois', 'all')

    # Trouver le premier lundi de l'année
    start = date(annee, 1, 1)
    while start.weekday() != 0:  # Lundi = 0
        start += timedelta(days=1)

    # Associer chaque semaine à un mois
    semaine_to_mois = {}
    mois_to_semaines = {m: [] for m in mois_labels}
    week_labels = []

    for i in range(1, 53):
        debut_semaine = start + timedelta(weeks=i-1)
        mois = debut_semaine.strftime("%B")  # "January", "February", etc.
        semaine = f"S{i}"
        week_labels.append(semaine)
        semaine_to_mois[semaine] = mois
        if mois in mois_to_semaines:
            mois_to_semaines[mois].append(semaine)

    # Appliquer le filtre
    if mois_filtre != 'all' and mois_filtre in mois_to_semaines:
        semaines_affichees = mois_to_semaines[mois_filtre]
    else:
        semaines_affichees = week_labels

    # Récupérer les profils
    profils = query_db("""
        SELECT p.id, p.nom, COUNT(c.matricule) AS nb_collab
        FROM profils p
        LEFT JOIN collaborateurs c ON p.id = c.profil_id
        GROUP BY p.id, p.nom
    """)

    data = []
    for profil in profils:
        row = {'profil': profil['nom'], 'nb_collab': profil['nb_collab']}
        for semaine in week_labels:
            row[semaine] = profil['nb_collab'] * 5  # 5 JH/semaine
        data.append(row)

    return render_template(
        'caf_automatique.html',
        week_labels=week_labels,
        semaines_affichees=semaines_affichees,
        semaine_to_mois=semaine_to_mois,
        mois_labels=mois_labels,
        data=data,
        mois_filtre=mois_filtre
    )

@caf_bp.route('/caf-requise')
def caf_requise():
    annee = 2025
    week_labels = [f"S{i}" for i in range(1, 53)]

    # Trouver le premier lundi de l'année
    start = date(annee, 1, 1)
    while start.weekday() != 0:
        start += timedelta(days=1)

    # Récupérer les projets avec leurs phases
    projets = query_db("""
        SELECT 
            p.id, p.titre, p.duree_estimee_jh,
            pp.date_debut, pp.date_fin,
            pph.profil_id, pph.pourcentage
        FROM projets p
        JOIN projet_phases pp ON p.id = pp.projet_id
        JOIN phase_profils_programme pph ON pp.phase_id = pph.phase_id
        WHERE p.statut IN ('En attente', 'À planifier', 'En cours')
    """)

    # Récupérer les profils
    profils = query_db("SELECT id, nom FROM profils")
    profil_dict = {p['id']: p['nom'] for p in profils}

    # Initialiser la charge par semaine
    charge_semaine = {f"S{i}": {p['id']: 0 for p in profils} for i in range(1, 53)}

    for projet in projets:
        try:
            debut = datetime.strptime(projet['date_debut'], "%Y-%m-%d").date()
            fin = datetime.strptime(projet['date_fin'], "%Y-%m-%d").date()
            charge = projet['duree_estimee_jh'] or 0
            pourcentage = projet['pourcentage'] or 1.0
            charge_projet = charge * (pourcentage / 100)
        except:
            continue

        # Répartir sur les semaines
        for i in range(1, 53):
            debut_semaine = start + timedelta(weeks=i-1)
            fin_semaine = debut_semaine + timedelta(days=6)
            key = f"S{i}"
            if debut <= fin_semaine and fin >= debut_semaine:
                overlap = min(fin, fin_semaine) - max(debut, debut_semaine)
                jours = overlap.days + 1
                total_jours = (fin - debut).days + 1
                if total_jours > 0:
                    charge_semaine_projet = (charge_projet * jours) / total_jours
                    charge_semaine[key][projet['profil_id']] += charge_semaine_projet

    # Préparer les données
    data = []
    for profil in profils:
        row = {'profil': profil['nom']}
        for s in week_labels:
            row[s] = charge_semaine[s][profil['id']]
        data.append(row)

    return render_template('caf_requise.html', week_labels=week_labels, data=data)

@caf_bp.route('/caf-disponibles')
def caf_disponibles():
    annee = 2025
    weeks = []
    week_labels = []

    start = date(annee, 1, 1)
    while start.weekday() != 0:
        start += timedelta(days=1)

    num_weeks = 53 if calendar.isleap(annee) else 52
    for i in range(1, num_weeks + 1):
        weeks.append((i, start + timedelta(weeks=i-1)))
        week_labels.append(f"S{i}")

    # Récupérer les collaborateurs avec leurs profils
    collaborateurs = query_db("""
        SELECT 
            c.matricule,
            c.nom || ' ' || c.prenom AS nom_prenom,
            p.nom AS profil,
            a.nom AS affectation,
            p.build_ratio,
            p.run_ratio,
            c.caf_disponible_build,
            c.caf_disponible_run
        FROM collaborateurs c
        JOIN profils p ON c.profil_id = p.id
        JOIN affectation a ON c.affectation_id = a.id
    """)

    # Exemple : 5 JH disponibles par semaine par collab (à remplacer par une vraie logique)
    data = {}
    for collab in collaborateurs:
        matricule = collab['matricule']
        data[matricule] = {}
        for i in range(1, num_weeks + 1):
            data[matricule][f"S{i}"] = 5.0  # Exemple fixe

    return render_template(
        'caf_disponibles.html',
        week_labels=week_labels,
        data=data,
        collaborateurs=collaborateurs
    )