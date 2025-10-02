# backend/app.py

from dotenv import load_dotenv
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import uuid
from werkzeug.utils import secure_filename
from services.wsjf_calculator import calculate_wsjf
from utils.db_utils import execute_db, init_db, query_db
from werkzeug.security import generate_password_hash, check_password_hash

# ----------------- IMPORT DES BLUEPRINTS -----------------
from routes.collaborateurs_routes import collab_bp
from routes.caf import caf_bp
from routes.programmes_routes import programmes_bp
from routes.projets_routes import projets_bp
from routes.valeurs_metier_routes import valeurs_bp
from routes.profils_routes import profils_bp

# ----------------- CONFIGURATION -----------------
load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'votre_cle_secrete_super_securisee')

# Enregistrement des Blueprints
app.register_blueprint(collab_bp)
app.register_blueprint(caf_bp)

app.register_blueprint(profils_bp)
app.register_blueprint(programmes_bp)
app.register_blueprint(projets_bp)
app.register_blueprint(valeurs_bp)

# Gestion des uploads
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialisation DB au démarrage
init_db()

# ----------------- ROUTES -----------------

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/create_admin', methods=['GET', 'POST'])
def create_admin():
    """Créer un administrateur si besoin"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        user_id = str(uuid.uuid4())

        try:
            execute_db("""
                INSERT INTO users (id, username, password, role)
                VALUES (?, ?, ?, ?)
            """, [user_id, username, hashed_password, 'admin'])
            flash("✅ Utilisateur admin créé avec succès.", "success")
            return redirect(url_for('login'))
        except Exception:
            flash("❌ Ce nom d'utilisateur existe déjà.", "danger")
    return render_template('create_admin.html')


# ----------------- LOGIN / LOGOUT -----------------

@app.route('/', methods=['GET', 'POST'])
def login():
    """Page de connexion"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = query_db("SELECT * FROM users WHERE username = ?", [username], one=True)
        if user and check_password_hash(user['password'], password):
            session['user'] = dict(user)
            flash("✅ Connexion réussie", "success")
            return redirect(url_for('priorites'))
        else:
            flash("❌ Nom d'utilisateur ou mot de passe incorrect", "danger")
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Déconnexion"""
    session.pop('user', None)
    flash("ℹ️ Vous êtes déconnecté.", "info")
    return redirect(url_for('login'))


# ----------------- INTERFACES MULTI-ÉTAPES -----------------

@app.route('/interface1', methods=['GET', 'POST'])
def interface1():
    categorie = query_db("SELECT * FROM categorie")
    if request.method == 'POST':
        date_mep = datetime.strptime(request.form['date_mep'], '%Y-%m-%d').date()
        session['form1'] = {
            'titre': request.form['titre'],
            'description': request.form['description'],
            'type_demande': request.form['type_demande'],
            'date_mep': date_mep.strftime('%Y-%m-%d'),
            'release': request.form['release'],
            'categorie_id': request.form['categorie_id']
        }
        return redirect(url_for('interface2'))
    return render_template('interface1.html', now=datetime.now(), categorie=categorie)


@app.route('/interface2', methods=['GET', 'POST'])
def interface2():
    if 'form1' not in session:
        return redirect(url_for('interface1'))
    if request.method == 'POST':
        session['form2'] = request.form.to_dict()
        return redirect(url_for('interface3'))
    return render_template('interface2.html')


@app.route('/interface3', methods=['GET', 'POST'])
def interface3():
    if 'form1' not in session or 'form2' not in session:
        return redirect(url_for('interface1'))

    if request.method == 'POST':
        project_id = str(uuid.uuid4())
        form1 = session.pop('form1', {})
        form2 = session.pop('form2', {})
        form3 = request.form.to_dict()
        all_data = {**form1, **form2, **form3, 'project_id': project_id}

        # Calcul WSJF
        resultats = calculate_wsjf(all_data)
        score_wsjf, complexite, jh_estime = resultats['score_wsjf'], resultats['complexite'], resultats['jh_estime']

        # Trouver release associée
        date_mep = all_data.get('date_mep')
        release_info = query_db("""
            SELECT id FROM releases WHERE ? BETWEEN debut AND fin ORDER BY debut DESC LIMIT 1
        """, [date_mep], one=True)
        release_id = release_info['id'] if release_info else None

        try:
            execute_db('''INSERT INTO projets (
                id, titre, description, alignement_strategic, impact_pnb, impact_satisfaction, date_mep, 
                conquerir_client, maitrise_couts, attenuation_menaces, creation_opportunites, 
                conditions_techniques, deadline_reglementaire, pression_concurrence, echeances_strategiques, 
                urgence_obsolescence, dependances_projets, q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, 
                score_wsjf, release_id, categorie_id, statut, duree_estimee_jh, complexite)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (project_id, all_data['titre'], all_data['description'], all_data['alignement_strategic'],
                 all_data['impact_pnb'], all_data['impact_satisfaction'], all_data['date_mep'],
                 all_data['conquerir_client'], all_data['maitrise_couts'],
                 all_data['attenuation_menaces'], all_data['creation_opportunites'],
                 all_data['conditions_techniques'], all_data['deadline_reglementaire'],
                 all_data['pression_concurrence'], all_data['echeances_strategiques'],
                 all_data['urgence_obsolescence'], all_data['dependances_projets'],
                 all_data['q1'], all_data['q2'], all_data['q3'], all_data['q4'],
                 all_data['q5'], all_data['q6'], all_data['q7'], all_data['q8'],
                 all_data['q9'], all_data['q10'],
                 score_wsjf, release_id, all_data.get('categorie_id'),
                 all_data.get('statut', 'En attente'), jh_estime, complexite))
            session['project_id'] = project_id
        except Exception as e:
            return f"Erreur : {e}", 500

        return redirect(url_for('resultat'))

    return render_template('interface3.html')


# ----------------- RESULTATS -----------------

@app.route('/resultat')
def resultat():
    project_id = session.get('project_id')
    if not project_id:
        return redirect(url_for('interface1'))
    projet = query_db('SELECT * FROM projets WHERE id = ?', [project_id], one=True)
    if not projet:
        return "Projet non trouvé", 404
    try:
        date_affichee = datetime.strptime(projet['date_mep'], '%Y-%m-%d').strftime('%d/%m/%Y')
    except ValueError:
        date_affichee = projet['date_mep']
    return render_template('resultat.html', result=projet, date_mep=date_affichee)


# ----------------- PRIORITES -----------------

@app.route('/priorites')
def priorites():
    filtre_retenu = request.args.get('retenu')
    query = """
        SELECT p.*, c.nom AS categorie 
        FROM projets p
        LEFT JOIN categorie c ON p.categorie_id = c.id
    """
    if filtre_retenu == '1':
        query += " WHERE p.retenu = 1 "
    query += " ORDER BY p.score_wsjf DESC LIMIT 50"

    projets = query_db(query)
    return render_template('priorites.html', projets=projets, filtre_retenu=filtre_retenu)


@app.route('/modifier-priorite/<id>', methods=['GET', 'POST'])
def modifier_priorite(id):
    projet = query_db("SELECT * FROM projets WHERE id = ?", [id], one=True)
    categories = query_db("SELECT * FROM categorie")
    programmes = query_db("SELECT * FROM programmes")

    if not projet:
        flash("❌ Projet introuvable", "danger")
        return redirect(url_for('priorites'))

    if request.method == 'POST':
        form_data = request.form.to_dict()
        resultats = calculate_wsjf(form_data)
        score_wsjf, complexite, jh_estime = resultats['score_wsjf'], resultats['complexite'], resultats['jh_estime']

        champs = [
            'titre', 'description', 'alignement_strategic', 'impact_pnb', 'impact_satisfaction',
            'date_mep', 'conquerir_client', 'maitrise_couts', 'attenuation_menaces',
            'creation_opportunites', 'conditions_techniques', 'deadline_reglementaire',
            'pression_concurrence', 'echeances_strategiques', 'urgence_obsolescence',
            'dependances_projets', 'q1', 'q2', 'q3', 'q4', 'q5', 'q6', 'q7', 'q8', 'q9', 'q10',
            'categorie_id', 'statut', 'programme_id'
        ]
        valeurs = [form_data.get(champ, '') for champ in champs]
        valeurs.extend([score_wsjf, jh_estime, complexite, id])

        update_query = """
            UPDATE projets SET 
                titre = ?, description = ?, alignement_strategic = ?, impact_pnb = ?, impact_satisfaction = ?, 
                date_mep = ?, conquerir_client = ?, maitrise_couts = ?, attenuation_menaces = ?, creation_opportunites = ?, 
                conditions_techniques = ?, deadline_reglementaire = ?, pression_concurrence = ?, echeances_strategiques = ?, urgence_obsolescence = ?, 
                dependances_projets = ?, q1 = ?, q2 = ?, q3 = ?, q4 = ?, q5 = ?, q6 = ?, q7 = ?, q8 = ?, q9 = ?, q10 = ?, 
                categorie_id = ?, statut = ?, programme_id = ?, score_wsjf = ?, duree_estimee_jh = ?, complexite = ?
            WHERE id = ?
        """
        execute_db(update_query, valeurs)
        flash("✅ Projet mis à jour avec recalcul du WSJF et de la charge", "success")
        return redirect(url_for('priorites'))

    return render_template('modifier_priorite.html', projet=dict(projet), categories=categories, programmes=programmes)


@app.route('/toggle_retenu/<string:projet_id>', methods=['POST'])
def toggle_retenu(projet_id):
    projet = query_db("SELECT retenu FROM projets WHERE id = ?", [projet_id], one=True)
    if projet is None:
        flash("❌ Projet introuvable", "danger")
    else:
        nouveau_statut = 0 if projet['retenu'] else 1
        execute_db("UPDATE projets SET retenu = ? WHERE id = ?",
                   [nouveau_statut, projet_id])
        flash("✅ Statut 'retenu' mis à jour", "success")
    return redirect(url_for('priorites'))


# ----------------- MAIN -----------------

if __name__ == '__main__':
    host = "127.0.0.1"
    port = 5000
    print(f"[APP] 🚀 Projet lancé sur : http://{host}:{port}")
    print(f"[APP] 📂 Dossier uploads : {UPLOAD_FOLDER}")
    app.run(host=host, port=port, debug=False, use_reloader=False)
