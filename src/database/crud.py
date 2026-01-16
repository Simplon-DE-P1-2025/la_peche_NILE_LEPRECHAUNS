"""Opérations CRUD avec SQLAlchemy ORM - Approche Hybride.

L'audit est géré automatiquement par les triggers PostgreSQL.
On se concentre uniquement sur la logique métier.

Usage:
    from src.database.crud import crud_operation, crud_flotteur
    from src.database.connection import get_session

    with get_session() as session:
        # Créer
        op = crud_operation.create(session, {"operation_id": 1, ...}, user="admin")

        # Lire
        op = crud_operation.get(session, 1)
        ops = crud_operation.search(session, cross="Etel")

        # Mettre à jour
        crud_operation.update(session, op, {"type_operation": "MAS"}, user="admin")

        # Supprimer
        crud_operation.delete(session, 1, user="admin")
"""

from typing import TypeVar, Generic, Optional, Type, Any
from datetime import date

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session, joinedload

from src.database.models import (
    Base,
    Operation,
    Flotteur,
    ResultatHumain,
    OperationStats,
    User,
)
from src.database.connection import (
    set_session_user,
    refresh_materialized_views_async,
    invalidate_stats_cache,
)

# Type générique pour les modèles
ModelType = TypeVar("ModelType", bound=Base)

# Tables qui affectent la vue matérialisée operations_stats
# Le refresh n'est nécessaire que pour ces tables
TABLES_AFFECTING_STATS = {"operations", "resultats_humain"}


def _trigger_stats_refresh(model: type) -> None:
    """Déclenche le refresh de la vue matérialisée si nécessaire.

    Appelé après les opérations CRUD sur les tables qui affectent
    operations_stats (operations, resultats_humain).
    """
    table_name = getattr(model, "__tablename__", "")
    if table_name in TABLES_AFFECTING_STATS:
        # Invalider le cache Streamlit immédiatement
        invalidate_stats_cache()
        # Rafraîchir la vue matérialisée en arrière-plan
        refresh_materialized_views_async()


# =============================================================================
# Classe CRUD Générique
# =============================================================================
class CRUDBase(Generic[ModelType]):
    """Classe CRUD générique pour tous les modèles.

    Fournit les opérations de base :
    - get : Récupérer par ID
    - get_multi : Récupérer plusieurs avec pagination
    - count : Compter les enregistrements
    - create : Créer un nouvel enregistrement
    - update : Mettre à jour un enregistrement
    - delete : Supprimer un enregistrement
    """

    def __init__(self, model: Type[ModelType]):
        """Initialiser avec le modèle SQLAlchemy."""
        self.model = model

    def get(self, session: Session, id: int) -> Optional[ModelType]:
        """Récupérer un enregistrement par ID.

        Args:
            session: Session SQLAlchemy
            id: Identifiant de l'enregistrement

        Returns:
            L'objet trouvé ou None
        """
        return session.get(self.model, int(id))

    def get_multi(
        self, session: Session, skip: int = 0, limit: int = 100, order_by: str = None
    ) -> list[ModelType]:
        """Récupérer plusieurs enregistrements avec pagination.

        Args:
            session: Session SQLAlchemy
            skip: Nombre d'enregistrements à sauter
            limit: Nombre maximum à retourner
            order_by: Colonne de tri (desc par défaut)

        Returns:
            Liste d'objets
        """
        query = select(self.model)

        if order_by:
            col = getattr(self.model, order_by, None)
            if col is not None:
                query = query.order_by(col.desc())

        query = query.offset(skip).limit(limit)
        return list(session.scalars(query).all())

    def count(self, session: Session) -> int:
        """Compter le nombre total d'enregistrements.

        Args:
            session: Session SQLAlchemy

        Returns:
            Nombre total
        """
        return session.scalar(select(func.count()).select_from(self.model))

    def create(self, session: Session, obj_in: dict, user: str = "system") -> ModelType:
        """Créer un nouvel enregistrement.

        Le trigger PostgreSQL s'occupera de l'audit automatiquement !
        La vue matérialisée sera rafraîchie en arrière-plan si nécessaire.

        Args:
            session: Session SQLAlchemy
            obj_in: Dictionnaire des données
            user: Utilisateur pour l'audit

        Returns:
            L'objet créé
        """
        # Définir l'utilisateur pour l'audit
        set_session_user(session, user)

        # Créer l'objet
        db_obj = self.model(**obj_in)
        session.add(db_obj)
        session.flush()  # Pour obtenir l'ID généré
        session.refresh(db_obj)

        # Rafraîchir la vue matérialisée si nécessaire (en arrière-plan)
        _trigger_stats_refresh(self.model)

        return db_obj

    def update(
        self, session: Session, db_obj: ModelType, obj_in: dict, user: str = "system"
    ) -> ModelType:
        """Mettre à jour un enregistrement.

        Le trigger PostgreSQL loggera old_values et new_values automatiquement !
        La vue matérialisée sera rafraîchie en arrière-plan si nécessaire.

        Args:
            session: Session SQLAlchemy
            db_obj: Objet à mettre à jour
            obj_in: Dictionnaire des nouvelles valeurs
            user: Utilisateur pour l'audit

        Returns:
            L'objet mis à jour
        """
        set_session_user(session, user)

        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        session.flush()
        session.refresh(db_obj)

        # Rafraîchir la vue matérialisée si nécessaire (en arrière-plan)
        _trigger_stats_refresh(self.model)

        return db_obj

    def delete(self, session: Session, id: int, user: str = "system") -> bool:
        """Supprimer un enregistrement.

        Le trigger PostgreSQL loggera old_values automatiquement !
        La vue matérialisée sera rafraîchie en arrière-plan si nécessaire.

        Args:
            session: Session SQLAlchemy
            id: Identifiant à supprimer
            user: Utilisateur pour l'audit

        Returns:
            True si supprimé, False si non trouvé
        """
        set_session_user(session, user)

        obj = self.get(session, id)
        if obj:
            session.delete(obj)
            # Rafraîchir la vue matérialisée si nécessaire (en arrière-plan)
            _trigger_stats_refresh(self.model)
            return True
        return False


# =============================================================================
# CRUD Operations
# =============================================================================
class CRUDOperation(CRUDBase[Operation]):
    """CRUD pour les opérations avec fonctionnalités spécifiques."""

    def get_with_relations(self, session: Session, id: int) -> Optional[Operation]:
        """Récupérer une opération avec toutes ses relations.

        Charge en une seule requête :
        - flotteurs
        - resultats_humain
        - stats

        Args:
            session: Session SQLAlchemy
            id: ID de l'opération

        Returns:
            Operation avec relations chargées ou None
        """
        query = (
            select(Operation)
            .options(
                joinedload(Operation.flotteurs),
                joinedload(Operation.resultats_humain),
            )
            .where(Operation.operation_id == int(id))
        )
        return session.scalar(query)

    def search(
        self,
        session: Session,
        cross: str = None,
        departement: str = None,
        type_operation: str = None,
        date_debut: date = None,
        date_fin: date = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Operation]:
        """Rechercher des opérations avec filtres.

        Args:
            session: Session SQLAlchemy
            cross: Filtrer par CROSS
            departement: Filtrer par département
            type_operation: Filtrer par type
            date_debut: Date minimum
            date_fin: Date maximum
            skip: Pagination - offset
            limit: Pagination - limit

        Returns:
            Liste d'opérations correspondantes
        """
        query = select(Operation)

        conditions = []
        if cross:
            conditions.append(Operation.cross == cross)
        if departement:
            conditions.append(Operation.departement == departement)
        if type_operation:
            conditions.append(Operation.type_operation == type_operation)
        if date_debut:
            conditions.append(Operation.date_heure_reception_alerte >= date_debut)
        if date_fin:
            conditions.append(Operation.date_heure_reception_alerte <= date_fin)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(Operation.date_heure_reception_alerte.desc())
        query = query.offset(skip).limit(limit)

        return list(session.scalars(query).all())

    def count_filtered(
        self,
        session: Session,
        cross: str = None,
        departement: str = None,
        type_operation: str = None,
        date_debut: date = None,
        date_fin: date = None,
    ) -> int:
        """Compter les opérations avec les mêmes filtres que search."""
        query = select(func.count()).select_from(Operation)

        conditions = []
        if cross:
            conditions.append(Operation.cross == cross)
        if departement:
            conditions.append(Operation.departement == departement)
        if type_operation:
            conditions.append(Operation.type_operation == type_operation)
        if date_debut:
            conditions.append(Operation.date_heure_reception_alerte >= date_debut)
        if date_fin:
            conditions.append(Operation.date_heure_reception_alerte <= date_fin)

        if conditions:
            query = query.where(and_(*conditions))

        return session.scalar(query)

    def get_by_cross(self, session: Session, cross: str) -> list[Operation]:
        """Récupérer les opérations d'un CROSS."""
        return self.search(session, cross=cross)

    def get_distinct_values(self, session: Session, column: str) -> list[str]:
        """Récupérer les valeurs distinctes d'une colonne.

        Utile pour les filtres dropdown.
        """
        col = getattr(Operation, column, None)
        if col is None:
            return []

        query = select(col).distinct().where(col.isnot(None)).order_by(col)
        return list(session.scalars(query).all())


# =============================================================================
# CRUD Flotteurs
# =============================================================================
class CRUDFlotteur(CRUDBase[Flotteur]):
    """CRUD pour les flotteurs."""

    def get_by_operation(self, session: Session, operation_id: int) -> list[Flotteur]:
        """Récupérer les flotteurs d'une opération."""
        query = (
            select(Flotteur)
            .where(Flotteur.operation_id == operation_id)
            .order_by(Flotteur.flotteur_id)
        )
        return list(session.scalars(query).all())

    def search_by_type(self, session: Session, type_flotteur: str) -> list[Flotteur]:
        """Rechercher par type de flotteur (recherche partielle)."""
        query = select(Flotteur).where(
            Flotteur.type_flotteur.ilike(f"%{type_flotteur}%")
        )
        return list(session.scalars(query).all())

    def get_distinct_types(self, session: Session) -> list[str]:
        """Récupérer les types de flotteurs distincts."""
        query = (
            select(Flotteur.type_flotteur)
            .distinct()
            .where(Flotteur.type_flotteur.isnot(None))
            .order_by(Flotteur.type_flotteur)
        )
        return list(session.scalars(query).all())


# =============================================================================
# CRUD Résultats Humains
# =============================================================================
class CRUDResultatHumain(CRUDBase[ResultatHumain]):
    """CRUD pour les résultats humains."""

    def get_by_operation(
        self, session: Session, operation_id: int
    ) -> list[ResultatHumain]:
        """Récupérer les résultats d'une opération."""
        query = select(ResultatHumain).where(
            ResultatHumain.operation_id == operation_id
        )
        return list(session.scalars(query).all())

    def get_by_resultat(self, session: Session, resultat: str) -> list[ResultatHumain]:
        """Récupérer par type de résultat."""
        query = select(ResultatHumain).where(ResultatHumain.resultat_humain == resultat)
        return list(session.scalars(query).all())


# =============================================================================
# CRUD Operations Stats (VIEW - lecture seule)
# =============================================================================
class CRUDOperationStats:
    """Accès en lecture seule à la VIEW operations_stats."""

    def get(self, session: Session, operation_id: int) -> Optional[OperationStats]:
        """Récupérer les stats d'une opération."""
        query = select(OperationStats).where(
            OperationStats.operation_id == operation_id
        )
        return session.scalar(query)

    def get_by_operation(
        self, session: Session, operation_id: int
    ) -> Optional[OperationStats]:
        """Alias pour get()."""
        return self.get(session, operation_id)

    def get_all(self, session: Session) -> list[OperationStats]:
        """Récupérer toutes les stats."""
        query = select(OperationStats)
        return list(session.scalars(query).all())


# =============================================================================
# CRUD Users
# =============================================================================
class CRUDUser(CRUDBase[User]):
    """CRUD pour les utilisateurs."""

    def get_by_username(self, session: Session, username: str) -> Optional[User]:
        """Récupérer un utilisateur par nom."""
        query = select(User).where(User.username == username)
        return session.scalar(query)

    def get_by_email(self, session: Session, email: str) -> Optional[User]:
        """Récupérer un utilisateur par email."""
        query = select(User).where(User.email == email)
        return session.scalar(query)

    def authenticate(
        self, session: Session, username: str, password: str
    ) -> Optional[User]:
        """Authentifier un utilisateur.

        Args:
            session: Session SQLAlchemy
            username: Nom d'utilisateur
            password: Mot de passe en clair

        Returns:
            User si authentification réussie, None sinon
        """
        import bcrypt

        user = self.get_by_username(session, username)
        if not user or not user.is_active:
            return None

        try:
            if bcrypt.checkpw(
                password.encode("utf-8"), user.password_hash.encode("utf-8")
            ):
                return user
        except Exception:
            return None

        return None

    def get_active_users(self, session: Session) -> list[User]:
        """Récupérer tous les utilisateurs actifs."""
        query = select(User).where(User.is_active == True).order_by(User.username)
        return list(session.scalars(query).all())

    def create_user(
        self,
        session: Session,
        username: str,
        password: str,
        email: str = None,
        role: str = "viewer",
    ) -> Optional[User]:
        """Créer un nouvel utilisateur avec hash du mot de passe.

        Args:
            session: Session SQLAlchemy
            username: Nom d'utilisateur
            password: Mot de passe en clair (sera hashé)
            email: Email optionnel
            role: Rôle (viewer, editor, admin)

        Returns:
            User créé ou None si username existe déjà
        """
        import bcrypt

        # Vérifier si l'utilisateur existe
        if self.get_by_username(session, username):
            return None

        password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        user_data = {
            "username": username,
            "password_hash": password_hash,
            "email": email,
            "role": role,
            "is_active": True,
        }

        return self.create(session, user_data, user="system")


# =============================================================================
# Instances des CRUD (singletons)
# =============================================================================
crud_operation = CRUDOperation(Operation)
crud_flotteur = CRUDFlotteur(Flotteur)
crud_resultat_humain = CRUDResultatHumain(ResultatHumain)
crud_operation_stats = CRUDOperationStats()
crud_user = CRUDUser(User)


# =============================================================================
# Fonctions utilitaires
# =============================================================================
def create_operation_with_relations(
    session: Session,
    operation_data: dict,
    flotteurs: list[dict] = None,
    resultats: list[dict] = None,
    stats: dict = None,
    user: str = "system",
) -> Operation:
    """Créer une opération avec ses relations en une transaction.

    Args:
        session: Session SQLAlchemy
        operation_data: Données de l'opération
        flotteurs: Liste de dictionnaires pour les flotteurs
        resultats: Liste de dictionnaires pour les résultats humains
        stats: Dictionnaire pour les statistiques
        user: Utilisateur pour l'audit

    Returns:
        Operation créée avec ses relations
    """
    set_session_user(session, user)

    # Créer l'opération
    operation = Operation(**operation_data)
    session.add(operation)
    session.flush()

    # Ajouter les flotteurs
    if flotteurs:
        for f_data in flotteurs:
            f_data["operation_id"] = operation.operation_id
            flotteur = Flotteur(**f_data)
            session.add(flotteur)

    # Ajouter les résultats
    if resultats:
        for r_data in resultats:
            r_data["operation_id"] = operation.operation_id
            resultat = ResultatHumain(**r_data)
            session.add(resultat)

    # Ajouter les stats (commenté - OperationStats sera une view PostgreSQL)
    # if stats:
    #     stats["operation_id"] = operation.operation_id
    #     operation_stats = OperationStats(**stats)
    #     session.add(operation_stats)

    session.flush()
    session.refresh(operation)

    return operation
