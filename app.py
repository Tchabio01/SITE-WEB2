import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import uuid
from datetime import datetime

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'secret_key_default')

# Configuration de la base de données
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'parlons_damour_db'),
    'charset': 'utf8mb4'
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Erreur de connexion à MySQL: {e}")
        return None

def create_database():
    """Crée la base de données si elle n'existe pas"""
    try:
        # Connexion sans spécifier la base de données
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        cursor = conn.cursor()
        
        # Création de la base de données avec vérification d'existence
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']} "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        print(f"[+] Base de données '{DB_CONFIG['database']}' créée ou déjà existante")
        
        cursor.close()
        conn.close()
    except Error as e:
        print(f"Erreur lors de la création de la base de données: {e}")
        raise

def create_tables():
    """Crée les tables nécessaires dans la base de données"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Table pour les signalements
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS signalements (
            id INT AUTO_INCREMENT PRIMARY KEY,
            type_situation VARCHAR(100) NOT NULL,
            ville VARCHAR(50) NOT NULL,
            quartier VARCHAR(50) NOT NULL,
            description TEXT NOT NULL,
            preuve_path VARCHAR(255),
            coordonnees VARCHAR(100),
            anonyme BOOLEAN DEFAULT 0,
            date_creation DATETIME DEFAULT CURRENT_TIMESTAMP,
            status ENUM('nouveau', 'en_cours', 'traite', 'ferme') DEFAULT 'nouveau'
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        # Table pour les adhésions
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS adhesions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nom_complet VARCHAR(100) NOT NULL,
            email VARCHAR(100) NOT NULL UNIQUE,
            telephone VARCHAR(20) NOT NULL,
            ville VARCHAR(50) NOT NULL,
            disponibilite VARCHAR(100) NOT NULL,
            competences TEXT,
            date_creation DATETIME DEFAULT CURRENT_TIMESTAMP,
            niveau_urgence ENUM('normal', 'eleve') DEFAULT 'normal'
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        # Table pour la newsletter
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS newsletter (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(100) UNIQUE NOT NULL,
            date_inscription DATETIME DEFAULT CURRENT_TIMESTAMP,
            actif BOOLEAN DEFAULT 1
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        # Table pour les vidéos de signalement
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS signalements_video (
            id INT AUTO_INCREMENT PRIMARY KEY,
            video_path VARCHAR(255) NOT NULL,
            date_creation DATETIME DEFAULT CURRENT_TIMESTAMP,
            traite BOOLEAN DEFAULT 0,
            id_signalement INT,
            FOREIGN KEY (id_signalement) REFERENCES signalements(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        # Table pour le suivi des actions
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS actions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            titre VARCHAR(100) NOT NULL,
            description TEXT NOT NULL,
            lieu VARCHAR(100) NOT NULL,
            date_action DATE NOT NULL,
            benevoles_requis INT DEFAULT 0,
            date_creation DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        print("[+] Tables créées avec succès")
        conn.commit()
    except Error as e:
        print(f"Erreur lors de la création des tables: {e}")
        raise
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/')
def index():
    """Affiche la page d'accueil"""
    return render_template('index.html')

@app.route('/submit_signalement', methods=['POST'])
def submit_signalement():
    """Traite le formulaire de signalement"""
    try:
        # Récupération des données du formulaire
        type_situation = request.form.get('type_situation')
        ville = request.form.get('ville')
        quartier = request.form.get('quartier')
        description = request.form.get('description')
        coordonnees = request.form.get('coordonnees')
        anonyme = 1 if request.form.get('anonyme') else 0
        
        # Gestion du fichier joint
        preuve_file = request.files.get('preuve')
        preuve_path = None
        
        if preuve_file and preuve_file.filename != '':
            # Créer un nom de fichier unique
            filename = f"preuve_{uuid.uuid4().hex}_{preuve_file.filename}"
            upload_dir = os.path.join('static', 'uploads')
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
            filepath = os.path.join(upload_dir, filename)
            preuve_file.save(filepath)
            preuve_path = f"/static/uploads/{filename}"

        # Connexion à la base de données
        conn = get_db_connection()
        if not conn:
            flash("Erreur de connexion à la base de données", "danger")
            return redirect(url_for('index'))
        
        cursor = conn.cursor()
        
        # Insertion dans la base de données
        cursor.execute(
            "INSERT INTO signalements (type_situation, ville, quartier, description, preuve_path, coordonnees, anonyme) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (type_situation, ville, quartier, description, preuve_path, coordonnees, anonyme)
        )
        
        conn.commit()
        flash("Signalement enregistré avec succès!", "success")
        return redirect(url_for('index'))
    
    except Exception as e:
        print(f"Erreur lors de l'enregistrement du signalement: {e}")
        flash(f"Erreur lors de l'enregistrement: {str(e)}", "danger")
        return redirect(url_for('index'))

@app.route('/submit_adhesion', methods=['POST'])
def submit_adhesion():
    """Traite le formulaire d'adhésion"""
    try:
        # Récupération des données du formulaire
        nom_complet = request.form.get('nom_complet')
        email = request.form.get('email')
        telephone = request.form.get('telephone')
        ville = request.form.get('ville')
        
        # Gestion des disponibilités
        disponibilites = []
        if request.form.get('weekends'): disponibilites.append('Weekends')
        if request.form.get('weekdays'): disponibilites.append('Semaine')
        if request.form.get('occasional'): disponibilites.append('Occasionnel')
        disponibilite = ', '.join(disponibilites)
        
        competences = request.form.get('competences')

        # Connexion à la base de données
        conn = get_db_connection()
        if not conn:
            flash("Erreur de connexion à la base de données", "danger")
            return redirect(url_for('index'))
        
        cursor = conn.cursor()
        
        # Insertion dans la base de données
        cursor.execute(
            "INSERT INTO adhesions (nom_complet, email, telephone, ville, disponibilite, competences) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (nom_complet, email, telephone, ville, disponibilite, competences)
        )
        
        conn.commit()
        flash("Votre demande d'adhésion a été enregistrée avec succès!", "success")
        return redirect(url_for('index'))
    
    except Exception as e:
        print(f"Erreur lors de l'enregistrement de l'adhésion: {e}")
        flash(f"Erreur lors de l'enregistrement: {str(e)}", "danger")
        return redirect(url_for('index'))

@app.route('/submit_newsletter', methods=['POST'])
def submit_newsletter():
    """Traite l'inscription à la newsletter"""
    try:
        email = request.form.get('email_newsletter')
        
        # Connexion à la base de données
        conn = get_db_connection()
        if not conn:
            return jsonify(success=False, message="Database connection error"), 500
        
        cursor = conn.cursor()
        
        # Vérifier si l'email existe déjà
        cursor.execute("SELECT id FROM newsletter WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify(success=False, message="Cet email est déjà inscrit"), 400
        
        # Insertion dans la base de données
        cursor.execute(
            "INSERT INTO newsletter (email) VALUES (%s)",
            (email,)
        )
        
        conn.commit()
        return jsonify(success=True, message="Inscription à la newsletter réussie!")
    
    except Exception as e:
        print(f"Erreur lors de l'inscription à la newsletter: {e}")
        return jsonify(success=False, message=str(e)), 500

@app.route('/video_signalement', methods=['POST'])
def video_signalement():
    """Traite l'envoi d'une vidéo de signalement"""
    try:
        # Récupérer la vidéo
        video_file = request.files.get('video')
        
        if not video_file or video_file.filename == '':
            return jsonify(success=False, message="Aucune vidéo fournie"), 400
        
        # Créer un nom de fichier unique
        filename = f"signalement_{uuid.uuid4().hex}_{video_file.filename}"
        upload_dir = os.path.join('static', 'videos')
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        filepath = os.path.join(upload_dir, filename)
        video_file.save(filepath)
        video_path = f"/static/videos/{filename}"

        # Enregistrer dans la base de données
        conn = get_db_connection()
        if not conn:
            return jsonify(success=False, message="Database connection error"), 500
        
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO signalements_video (video_path) VALUES (%s)",
            (video_path,)
        )
        conn.commit()
        
        return jsonify(success=True, message="Signalement vidéo enregistré avec succès!")
    
    except Exception as e:
        print(f"Erreur lors de l'enregistrement du signalement vidéo: {e}")
        return jsonify(success=False, message="Erreur serveur"), 500

# Page d'administration pour voir les signalements
@app.route('/admin/signalements')
def admin_signalements():
    try:
        conn = get_db_connection()
        if not conn:
            flash("Erreur de connexion à la base de données", "danger")
            return redirect(url_for('index'))
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM signalements ORDER BY date_creation DESC")
        signalements = cursor.fetchall()
        
        return render_template('admin_signalements.html', signalements=signalements)
    
    except Exception as e:
        print(f"Erreur lors de la récupération des signalements: {e}")
        flash(f"Erreur: {str(e)}", "danger")
        return redirect(url_for('index'))

# Page d'administration pour voir les adhésions
@app.route('/admin/adhesions')
def admin_adhesions():
    try:
        conn = get_db_connection()
        if not conn:
            flash("Erreur de connexion à la base de données", "danger")
            return redirect(url_for('index'))
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM adhesions ORDER BY date_creation DESC")
        adhesions = cursor.fetchall()
        
        return render_template('admin_adhesions.html', adhesions=adhesions)
    
    except Exception as e:
        print(f"Erreur lors de la récupération des adhésions: {e}")
        flash(f"Erreur: {str(e)}", "danger")
        return redirect(url_for('index'))

if __name__ == '__main__':
    # Initialiser la base de données
    create_database()
    create_tables()
    
    # Créer les dossiers nécessaires
    if not os.path.exists('static/uploads'):
        os.makedirs('static/uploads')
    if not os.path.exists('static/videos'):
        os.makedirs('static/videos')
    
    # Démarrer l'application
    app.run(debug=True)