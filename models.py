from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    Enum,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import enum
import sys
import json

# Import config avec gestion d'erreur
try:
    from config import DATABASE_URL
except ImportError:
    print("❌ Erreur: Impossible d'importer config.py")
    sys.exit(1)

# Vérifier que l'URL est valide
if not DATABASE_URL:
    print("❌ Erreur: DATABASE_URL non configuré")
    sys.exit(1)

# Créer l'engine avec gestion d'erreur
try:
    Base = declarative_base()
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # Vérifie la connexion avant de l'utiliser
        pool_recycle=3600,  # Recycle les connexions après 1h
        echo=False,  # Mettre à True pour debug
    )
    Session = sessionmaker(bind=engine)
    print("✅ Connexion à la base de données configurée")
except Exception as e:
    print(f"❌ Erreur de connexion à la base de données: {e}")
    sys.exit(1)


# Status des membres (Actif, Inactif, Suspendu)
# Actif : participe régulièrement aux réunions et activités
# Inactif : ne participe plus aux activités depuis un certain temps
# Suspendu : exclu temporairement pour non-respect des règles
class MemberStatus(enum.Enum):
    ACTIVE = "actif"
    INACTIVE = "inactif"
    SUSPENDED = "suspendu"


class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True)
    discord_id = Column(String(32), unique=True, nullable=False)
    username = Column(String(100), nullable=False)
    full_name = Column(String(200))
    email = Column(String(200), nullable=True)  # Email optionnel
    role = Column(String(100), nullable=True)  # DEV, IA, INFRA
    specialization = Column(String(200))
    status = Column(Enum(MemberStatus), default=MemberStatus.ACTIVE)
    joined_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)

    attendances = relationship("Attendance", back_populates="member")
    organized_meetings = relationship(
        "Meeting", back_populates="organizer", foreign_keys="Meeting.organizer_id"
    )


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True)
    title = Column(
        String(200), nullable=False, index=True
    )  # Index pour recherche par nom
    description = Column(Text)
    date = Column(DateTime, nullable=False)
    created_by = Column(String(32))  # Discord ID du créateur
    organizer_id = Column(Integer, ForeignKey("members.id"))  # Organisateur (membre)
    target_roles = Column(Text)  # Rôles ciblés (JSON: ["DEV", "IA"] ou "ALL")
    is_completed = Column(Boolean, default=False)
    attendance_validated = Column(Boolean, default=False)  # Appel validé
    attendance_validated_at = Column(DateTime)  # Date de validation
    attendance_validated_by = Column(String(32))  # Discord ID de qui a validé

    attendances = relationship("Attendance", back_populates="meeting")
    organizer = relationship(
        "Member", back_populates="organized_meetings", foreign_keys=[organizer_id]
    )

    # Retourne les rôles ciblés sous forme de liste
    def get_target_roles(self):
        if not self.target_roles:
            return []
        try:
            roles = json.loads(self.target_roles)
            return roles if isinstance(roles, list) else []
        except:
            return []

    # Définit les rôles ciblés à partir d'une liste ou "ALL"
    def set_target_roles(self, roles):
        if roles == "ALL" or roles == ["ALL"]:
            self.target_roles = json.dumps(["ALL"])
        else:
            self.target_roles = json.dumps(
                roles if isinstance(roles, list) else [roles]
            )


class Attendance(Base):
    __tablename__ = "attendances"

    id = Column(Integer, primary_key=True)
    member_id = Column(Integer, ForeignKey("members.id"))
    meeting_id = Column(Integer, ForeignKey("meetings.id"))
    status = Column(String(20), default="present")  # present, absent, excused
    timestamp = Column(DateTime, default=datetime.utcnow)
    modified_at = Column(DateTime)  # Si modifié après validation
    modified_by = Column(String(32))  # Discord ID de qui a modifié

    member = relationship("Member", back_populates="attendances")
    meeting = relationship("Meeting", back_populates="attendances")


# Status des tickets
class TicketStatus(enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    PENDING = "pending"


# Types de tickets
class TicketType(enum.Enum):
    JOIN_LABO = "join_labo"
    JOIN_POLE = "join_pole"


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    discord_user_id = Column(String(32), nullable=False, index=True)
    discord_username = Column(String(100), nullable=False)
    channel_id = Column(String(32), unique=True, nullable=False)
    type = Column(Enum(TicketType), nullable=False)
    pole_requested = Column(String(10))  # Pour les tickets de pôle (DEV, IA, INFRA)
    reason = Column(Text)
    status = Column(Enum(TicketStatus), default=TicketStatus.OPEN)
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime)
    closed_by = Column(String(32))  # Discord ID de qui a fermé
    assigned_to = Column(String(32))  # Discord ID de l'admin assigné


class TicketSettings(Base):
    __tablename__ = "ticket_settings"

    id = Column(Integer, primary_key=True)
    guild_id = Column(String(32), unique=True, nullable=False)
    tickets_enabled = Column(Boolean, default=True)
    pole_tickets_enabled = Column(Boolean, default=True)
    ticket_category_id = Column(String(32))  # ID de la catégorie pour les tickets
    log_channel_id = Column(String(32))  # Channel pour logs des tickets


# Initialise la base de données (crée les tables)
def init_database():
    try:
        Base.metadata.create_all(engine)
        print("✅ Tables de base de données créées/vérifiées")
        return True
    except Exception as e:
        print(f"❌ Erreur lors de la création des tables: {e}")
        return False


# Initialiser au chargement du module
if __name__ == "__main__":
    init_database()
