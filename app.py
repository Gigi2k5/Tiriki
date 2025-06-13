from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import random
from config import Config
from datetime import datetime, timedelta
from flask_mail import Mail, Message
import csv
import os
import schedule
import threading
import time
import shutil

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

# Variables importantes
MTN_MOMO_NUMBER = Config.MTN_MOMO_NUMBER
ADMIN_EMAIL = Config.ADMIN_EMAIL
ADMIN_PASSWORD = Config.ADMIN_PASSWORD
TICKET_PRICE = Config.TICKET_PRICE
MAX_TICKET_NUMBER = Config.MAX_TICKET_NUMBER

app.config['MAIL_SERVER'] = Config.SMTP_SERVER
app.config['MAIL_PORT'] = Config.SMTP_PORT
app.config['MAIL_USE_TLS'] = Config.SMTP_USE_TLS
app.config['MAIL_USERNAME'] = Config.SMTP_EMAIL
app.config['MAIL_PASSWORD'] = Config.SMTP_PASSWORD

mail = Mail(app)

def init_db():
    """Initialise la base de données"""
    conn = sqlite3.connect('tiriki.db')
    cursor = conn.cursor()
    
    # Table des utilisateurs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            prenom TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            telephone TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nb_tickets INTEGER NOT NULL,
            validated BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table des tickets
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            ticket_number INTEGER UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Table des paiements (pour validation admin)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            reference TEXT,
            montant REAL,
            validated BOOLEAN DEFAULT FALSE,
            validated_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def generate_unique_tickets(count):
    """Génère des numéros de tickets uniques"""
    conn = sqlite3.connect('tiriki.db')
    cursor = conn.cursor()
    
    # Récupérer les numéros déjà utilisés
    cursor.execute('SELECT ticket_number FROM tickets')
    used_numbers = [row[0] for row in cursor.fetchall()]
    
    # Générer des numéros uniques
    available_numbers = [i for i in range(1, 2001) if i not in used_numbers]
    
    if len(available_numbers) < count:
        conn.close()
        return None  # Pas assez de tickets disponibles
    
    selected_numbers = random.sample(available_numbers, count)
    conn.close()
    return selected_numbers

def backup_database():
    """Sauvegarde automatique de la base de données"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"tiriki_backup_{timestamp}.db"
        # Créer le dossier backups s'il n'existe pas
        os.makedirs('backups', exist_ok=True)
        shutil.copy2('tiriki.db', f'backups/{backup_name}')
        print(f"Sauvegarde créée: {backup_name}")
    except Exception as e:
        print(f"Erreur lors de la sauvegarde: {e}")


# Ajoutez cette fonction après la fonction backup_database() dans app.py

def send_validation_email(user_email, user_nom, user_prenom, ticket_numbers):
    """Envoie un email de confirmation après validation du paiement"""
    try:
        # Formater la liste des tickets
        tickets_str = ", ".join([str(num) for num in sorted(ticket_numbers)])
        
        # Créer le message HTML
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 30px 20px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 28px; }}
                .header .logo {{ font-size: 40px; margin-bottom: 10px; }}
                .content {{ padding: 30px 20px; }}
                .ticket-box {{ background: linear-gradient(45deg, #ff6b35, #f7931e); color: white; padding: 20px; border-radius: 10px; margin: 20px 0; text-align: center; }}
                .ticket-numbers {{ font-size: 20px; font-weight: bold; letter-spacing: 2px; }}
                .info-box {{ background: #e3f2fd; border-left: 4px solid #2196f3; padding: 15px; margin: 20px 0; }}
                .footer {{ background: #f5f5f5; padding: 20px; text-align: center; color: #666; font-size: 14px; }}
                .btn {{ background: linear-gradient(45deg, #ff6b35, #f7931e); color: white; padding: 12px 25px; text-decoration: none; border-radius: 25px; display: inline-block; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🍀</div>
                    <h1>Tiriki - Tombola Numérique</h1>
                    <p>Félicitations ! Votre participation est confirmée</p>
                </div>
                
                <div class="content">
                    <h2>Bonjour {user_prenom} {user_nom},</h2>
                    
                    <p>Excellente nouvelle ! Votre paiement a été <strong>validé avec succès</strong> et vos numéros de tickets ont été générés.</p>
                    
                    <div class="ticket-box">
                        <h3>🎫 Vos Numéros de Tickets</h3>
                        <div class="ticket-numbers">{tickets_str}</div>
                        <p style="margin-top: 15px; font-size: 16px;">Nombre total : {len(ticket_numbers)} ticket{'s' if len(ticket_numbers) > 1 else ''}</p>
                    </div>
                    
                    <div class="info-box">
                        <h4>📋 Informations importantes :</h4>
                        <ul>
                            <li><strong>Conservez précieusement ces numéros</strong> - ils sont uniques et nécessaires pour le tirage</li>
                            <li>Vous pouvez également les retrouver dans votre espace personnel sur le site</li>
                            <li>Le tirage au sort aura lieu selon les conditions annoncées</li>
                            <li>En cas de gain, vous serez contacté directement</li>
                        </ul>
                    </div>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{request.url_root}connexion" class="btn">Accéder à mon espace personnel</a>
                    </div>
                    
                    <p><strong>Bonne chance pour le tirage au sort ! 🍀</strong></p>
                </div>
                
                <div class="footer">
                    <p>Cet email a été envoyé automatiquement par la plateforme Tiriki.</p>
                    <p>© 2024 Tiriki - Tombola Numérique Sécurisée</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Version texte simple
        text_body = f"""
        Bonjour {user_prenom} {user_nom},

        Félicitations ! Votre paiement a été validé avec succès.

        Vos numéros de tickets : {tickets_str}
        Nombre total : {len(ticket_numbers)} ticket{'s' if len(ticket_numbers) > 1 else ''}

        Conservez précieusement ces numéros pour le tirage au sort !

        Vous pouvez également les consulter sur votre espace personnel : {request.url_root}connexion

        Bonne chance !

        L'équipe Tiriki
        """
        
        # Créer et envoyer l'email
        msg = Message(
            subject='🎉 Tiriki - Vos tickets ont été validés !',
            sender=app.config['MAIL_USERNAME'],
            recipients=[user_email],
            body=text_body,
            html=html_body
        )
        
        mail.send(msg)
        print(f"Email de validation envoyé à {user_email}")
        return True
        
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email à {user_email}: {str(e)}")
        return False

def send_admin_notification(user_nom, user_prenom, user_email, nb_tickets, montant):
    """Envoie une notification à l'admin lors d'une nouvelle inscription"""
    try:
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; padding: 20px; }}
                .header {{ background: #dc3545; color: white; padding: 20px; border-radius: 10px; text-align: center; }}
                .info {{ background: #f8f9fa; padding: 15px; margin: 15px 0; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>🔔 Nouvelle inscription Tiriki</h2>
                </div>
                
                <div class="info">
                    <h3>Détails du participant :</h3>
                    <p><strong>Nom :</strong> {user_nom} {user_prenom}</p>
                    <p><strong>Email :</strong> {user_email}</p>
                    <p><strong>Tickets demandés :</strong> {nb_tickets}</p>
                    <p><strong>Montant attendu :</strong> {montant} FCFA</p>
                </div>
                
                <p>Connectez-vous au dashboard admin pour valider le paiement une fois reçu.</p>
                
                <div style="text-align: center; margin: 20px 0;">
                    <a href="{request.url_root}admin/dashboard" style="background: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Accéder au Dashboard</a>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg = Message(
            subject='🔔 Tiriki - Nouvelle inscription en attente',
            sender=app.config['MAIL_USERNAME'],
            recipients=[ADMIN_EMAIL],
            html=html_body
        )
        
        mail.send(msg)
        print(f"Notification admin envoyée pour {user_nom} {user_prenom}")
        return True
        
    except Exception as e:
        print(f"Erreur lors de l'envoi de la notification admin: {str(e)}")
        return False

def start_scheduler():
    """Démarre le planificateur pour les sauvegardes"""
    schedule.every().day.at("02:00").do(backup_database)
    
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(3600)  # Vérifier toutes les heures
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

@app.route('/')
def home():
    return render_template('index.html', mtn_number=MTN_MOMO_NUMBER)

# Remplacez votre route d'inscription par celle-ci :

@app.route('/inscription', methods=['GET', 'POST'])
def inscription():
    if request.method == 'POST':
        nom = request.form['nom'].strip()
        prenom = request.form['prenom'].strip()
        email = request.form['email'].strip()
        telephone = request.form['telephone'].strip()
        password = request.form['password']
        nb_tickets = int(request.form['nb_tickets'])
        
        # Validations
        if nb_tickets < 1 or nb_tickets > 20:
            flash('Le nombre de tickets doit être entre 1 et 20.', 'error')
            return render_template('inscription.html')
        
        conn = sqlite3.connect('tiriki.db')
        cursor = conn.cursor()
        
        # Vérifier si email ou téléphone existe déjà
        cursor.execute('SELECT id FROM users WHERE email = ? OR telephone = ?', (email, telephone))
        if cursor.fetchone():
            flash('Email ou numéro de téléphone déjà utilisé.', 'error')
            conn.close()
            return render_template('inscription.html')
        
        # Créer l'utilisateur
        password_hash = generate_password_hash(password)
        cursor.execute('''
            INSERT INTO users (nom, prenom, email, telephone, password_hash, nb_tickets)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (nom, prenom, email, telephone, password_hash, nb_tickets))
        
        user_id = cursor.lastrowid
        
        # Créer l'entrée de paiement en attente
        reference = f"{telephone}-{nb_tickets}"
        montant = nb_tickets * TICKET_PRICE
        cursor.execute('''
            INSERT INTO payments (user_id, reference, montant)
            VALUES (?, ?, ?)
        ''', (user_id, reference, montant))
        
        conn.commit()
        conn.close()
        
        # 🆕 NOUVEAU : Envoyer notification à l'admin
        send_admin_notification(nom, prenom, email, nb_tickets, montant)
        
        flash(f'Inscription réussie ! Envoyez {montant} FCFA au {MTN_MOMO_NUMBER} avec la référence: {reference}. Votre compte sera validé sous 24h.', 'success')
        return redirect(url_for('connexion'))
    
    return render_template('inscription.html')

@app.route('/connexion', methods=['GET', 'POST'])
def connexion():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = sqlite3.connect('tiriki.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, password_hash, validated FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            session['validated'] = user[2]
            return redirect(url_for('espace_personnel'))
        else:
            flash('Email ou mot de passe incorrect.', 'error')
    
    return render_template('connexion.html')

@app.route('/espace-personnel')
def espace_personnel():
    if 'user_id' not in session:
        return redirect(url_for('connexion'))
    
    conn = sqlite3.connect('tiriki.db')
    cursor = conn.cursor()
    
    # Récupérer les infos utilisateur
    cursor.execute('SELECT nom, prenom, email, telephone, nb_tickets, validated FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    
    # Récupérer les tickets si validé
    tickets = []
    if user[5]:  # Si validé
        cursor.execute('SELECT ticket_number FROM tickets WHERE user_id = ? ORDER BY ticket_number', (session['user_id'],))
        tickets = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    return render_template('espace_personnel.html', user=user, tickets=tickets, ticket_price=TICKET_PRICE)

@app.route('/admin')
def admin():
    return render_template('admin_login.html')

@app.route('/admin/login', methods=['POST'])
def admin_login():
    email = request.form['email']
    password = request.form['password']
    
    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        session['admin'] = True
        return redirect(url_for('admin_dashboard'))
    else:
        flash('Identifiants administrateur incorrects.', 'error')
        return redirect(url_for('admin'))

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    
    conn = sqlite3.connect('tiriki.db')
    cursor = conn.cursor()
    
    # Récupérer les paiements en attende
    cursor.execute('''
        SELECT p.id, u.nom, u.prenom, u.telephone, u.email, p.reference, p.montant, u.nb_tickets, p.created_at
        FROM payments p
        JOIN users u ON p.user_id = u.id
        WHERE p.validated = FALSE AND u.validated = FALSE
        ORDER BY p.created_at DESC
    ''')
    pending_payments = cursor.fetchall()
    
    # Récupérer les tickets distribués avec les informations des utilisateurs
    cursor.execute('''
        SELECT t.ticket_number, u.nom, u.prenom, u.telephone, u.email, t.created_at, u.nb_tickets
        FROM tickets t
        JOIN users u ON t.user_id = u.id
        ORDER BY t.ticket_number ASC
    ''')
    distributed_tickets = cursor.fetchall()
    
    # Statistiques
    cursor.execute('SELECT COUNT(*) FROM users WHERE validated = TRUE')
    validated_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM tickets')
    total_tickets = cursor.fetchone()[0]
    remaining_tickets = MAX_TICKET_NUMBER - total_tickets
    
    conn.close()
    
    return render_template('admin_dashboard.html', 
                         payments=pending_payments,
                         distributed_tickets=distributed_tickets,
                         validated_users=validated_users,
                         total_tickets=total_tickets,
                         remaining_tickets=remaining_tickets)

@app.route('/admin/validate/<int:payment_id>')
def validate_payment(payment_id):
    if not session.get('admin'):
        return redirect(url_for('admin'))
    
    conn = sqlite3.connect('tiriki.db')
    cursor = conn.cursor()
    
    # Récupérer les infos du paiement
    cursor.execute('''
        SELECT p.user_id, u.nb_tickets, u.email, u.nom, u.prenom
        FROM payments p
        JOIN users u ON p.user_id = u.id
        WHERE p.id = ?
    ''', (payment_id,))
    
    payment_info = cursor.fetchone()
    
    if payment_info:
        user_id, nb_tickets, email, nom, prenom = payment_info
        
        # Générer les tickets
        ticket_numbers = generate_unique_tickets(nb_tickets)
        
        if ticket_numbers:
            # Insérer les tickets
            for ticket_num in ticket_numbers:
                cursor.execute('INSERT INTO tickets (user_id, ticket_number) VALUES (?, ?)', 
                             (user_id, ticket_num))
            
            # Marquer l'utilisateur et le paiement comme validés
            cursor.execute('UPDATE users SET validated = TRUE WHERE id = ?', (user_id,))
            cursor.execute('UPDATE payments SET validated = TRUE, validated_at = CURRENT_TIMESTAMP WHERE id = ?', (payment_id,))
            
            conn.commit()
            conn.close()
            
            # 🆕 NOUVEAU : Envoyer email de confirmation à l'utilisateur
            email_sent = send_validation_email(email, nom, prenom, ticket_numbers)
            
            if email_sent:
                flash(f'Paiement validé avec succès ! {nb_tickets} tickets générés pour {nom} {prenom}. Email de confirmation envoyé.', 'success')
            else:
                flash(f'Paiement validé avec succès ! {nb_tickets} tickets générés pour {nom} {prenom}. ⚠️ Erreur lors de l\'envoi de l\'email.', 'warning')
        else:
            conn.close()
            flash('Pas assez de tickets disponibles !', 'error')
    else:
        conn.close()
        flash('Paiement introuvable !', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/export')
def export_csv():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    
    conn = sqlite3.connect('tiriki.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT u.created_at, u.telephone, p.montant, 
               GROUP_CONCAT(t.ticket_number) as tickets
        FROM users u
        JOIN payments p ON u.id = p.user_id
        LEFT JOIN tickets t ON u.id = t.user_id
        WHERE u.validated = TRUE
        GROUP BY u.id
        ORDER BY u.created_at DESC
    ''')
    
    data = cursor.fetchall()
    conn.close()
    
    # Créer le fichier CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f'tiriki_export_{timestamp}.csv'
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Date', 'Téléphone', 'Montant', 'Tickets'])
        writer.writerows(data)
    
    flash(f'Export créé: {filename}', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


if __name__ == '__main__':
    # Créer le dossier de sauvegarde
    os.makedirs('backups', exist_ok=True)
    
    # Initialiser la base de données
    init_db()
    
    # Démarrer le planificateur de sauvegarde
    start_scheduler()
    
    port = int(os.environ.get("PORT", 5000))  # important pour Railway
    app.run(host="0.0.0.0", port=port)