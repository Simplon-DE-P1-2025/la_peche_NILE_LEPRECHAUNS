"""
crud.py - Lire et écrire dans la base de données
CRUD = Create, Read, Update, Delete
"""
from .models import Operation, Moyen, BilanHumain
from datetime import datetime


# ========== LIRE DES DONNÉES ==========

def lire_operations(db, limite=10):
    """
    Lire les opérations

    Exemple:
        db = get_session()
        operations = lire_operations(db, limite=5)
        for op in operations:
            print(op.operation_id, op.evenement_type)
        db.close()
    """
    return db.query(Operation).limit(limite).all()


def lire_une_operation(db, operation_id):
    """
    Lire UNE opération par son ID

    Exemple:
        db = get_session()
        operation = lire_une_operation(db, 12345)
        print(operation.cross_nom)
        db.close()
    """
    return db.query(Operation).filter(Operation.operation_id == operation_id).first()


def lire_moyens_operation(db, operation_id):
    """
    Lire les moyens d'une opération

    Exemple:
        db = get_session()
        moyens = lire_moyens_operation(db, 12345)
        for moyen in moyens:
            print(moyen.type_moyen, moyen.nom)
        db.close()
    """
    return db.query(Moyen).filter(Moyen.operation_id == operation_id).all()


# ========== CRÉER DES DONNÉES ==========

def creer_operation(db, operation_id, date, cross_nom, evenement_type):
    """
    Créer une nouvelle opération

    Exemple:
        db = get_session()
        operation = creer_operation(
            db,
            operation_id=99999,
            date=datetime.now(),
            cross_nom="CROSS Etel",
            evenement_type="Test"
        )
        print(f"Opération créée: {operation.operation_id}")
        db.close()
    """
    operation = Operation(
        operation_id=operation_id,
        date_heure_reception=date,
        cross_nom=cross_nom,
        evenement_type=evenement_type
    )
    db.add(operation)
    db.commit()
    db.refresh(operation)
    return operation


# ========== COMPTER ==========

def compter_operations(db):
    """
    Compter le nombre d'opérations

    Exemple:
        db = get_session()
        total = compter_operations(db)
        print(f"Il y a {total} opérations")
        db.close()
    """
    return db.query(Operation).count()
