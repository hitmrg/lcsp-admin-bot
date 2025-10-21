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
    email = Column(String(200))
    role = Column(String(100))
    specialization = Column(String(200))
    status = Column(Enum(MemberStatus), default=MemberStatus.ACTIVE)
    joined_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)

    attendances = relationship("Attendance", back_populates="member")


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    date = Column(DateTime, nullable=False)
    created_by = Column(String(32))
    is_completed = Column(Boolean, default=False)

    attendances = relationship("Attendance", back_populates="meeting")


class Attendance(Base):
    __tablename__ = "attendances"

    id = Column(Integer, primary_key=True)
    member_id = Column(Integer, ForeignKey("members.id"))
    meeting_id = Column(Integer, ForeignKey("meetings.id"))
    status = Column(String(20), default="present")
    timestamp = Column(DateTime, default=datetime.utcnow)

    member = relationship("Member", back_populates="attendances")
    meeting = relationship("Meeting", back_populates="attendances")


def init_database():
    """Initialiser la base de données"""
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
