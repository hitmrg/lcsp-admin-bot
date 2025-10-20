# Modèles de base de données (models.py)

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import enum
from config import DB_URL

Base = declarative_base()
engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)

class MemberStatus(enum.Enum):
    ACTIVE = "actif"
    INACTIVE = "inactif"
    SUSPENDED = "suspendu"

class Member(Base):
    __tablename__ = 'members'
    
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
    __tablename__ = 'meetings'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    date = Column(DateTime, nullable=False)
    created_by = Column(String(32))
    is_completed = Column(Boolean, default=False)
    
    attendances = relationship("Attendance", back_populates="meeting")

class Attendance(Base):
    __tablename__ = 'attendances'
    
    id = Column(Integer, primary_key=True)
    member_id = Column(Integer, ForeignKey('members.id'))
    meeting_id = Column(Integer, ForeignKey('meetings.id'))
    status = Column(String(20), default='present')
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    member = relationship("Member", back_populates="attendances")
    meeting = relationship("Meeting", back_populates="attendances")

# Créer les tables
Base.metadata.create_all(engine)