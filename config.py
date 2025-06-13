import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "tiriki_secret_key_2024")
    DATABASE_PATH = 'tiriki.db'
    BACKUP_DIR = 'backups'
    
    MTN_MOMO_NUMBER = os.getenv("MTN_MOMO_NUMBER", "01 61 23 75 02")
    
    ADMIN_EMAIL = os.environ["ADMIN_EMAIL"]
    ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]

    
    MAX_TICKETS_PER_USER = 20
    TICKET_PRICE = 100
    MAX_TICKET_NUMBER = 2000
    
# Email (optionnel)
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp-relay.brevo.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_EMAIL = os.getenv("SMTP_EMAIL")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    SMTP_USE_TLS = True  # On force l’usage de TLS si serveur SMTP connu

    
    # Sauvegardes
    BACKUP_TIME = "02:00"  # Heure de sauvegarde quotidienne
    
    # Validation
    VALIDATION_TIMEOUT_HOURS = 24