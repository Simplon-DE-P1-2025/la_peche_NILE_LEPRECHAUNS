"""
audit.py - Tracer les modifications dans la base de données
"""
from src.database.models import AuditLog
from datetime import datetime


def enregistrer_modification(db, utilisateur, action, table_nom):
    
    log = AuditLog(
        timestamp=datetime.now(),
        utilisateur=utilisateur,
        action=action,
        table_nom=table_nom
    )
    db.add(log)
    db.commit()
    print(f"✅ Modification enregistrée: {action} sur {table_nom} par {utilisateur}")


def voir_historique(db, limite=10):
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limite).all()


def voir_modifications_table(db, table_nom):
    return db.query(AuditLog).filter(
        AuditLog.table_nom == table_nom
    ).order_by(AuditLog.timestamp.desc()).all()
