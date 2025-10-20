# Gestionnaire de base de données (database.py)

from contextlib import contextmanager
from models import Session, Member, Meeting, Attendance, MemberStatus
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@contextmanager
def get_session():
    """Context manager pour les sessions"""
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Erreur DB: {e}")
        raise
    finally:
        session.close()

class Database:
    """Classe pour simplifier les opérations de base de données"""
    
    @staticmethod
    def get_member(discord_id: str):
        with get_session() as session:
            return session.query(Member).filter(
                Member.discord_id == str(discord_id)
            ).first()
    
    @staticmethod
    def add_member(**kwargs):
        with get_session() as session:
            member = Member(**kwargs)
            session.add(member)
            session.flush()
            return member
    
    @staticmethod
    def update_member(discord_id: str, **kwargs):
        with get_session() as session:
            member = session.query(Member).filter(
                Member.discord_id == str(discord_id)
            ).first()
            if member:
                for key, value in kwargs.items():
                    setattr(member, key, value)
                member.last_active = datetime.utcnow()
            return member
    
    @staticmethod
    def delete_member(discord_id: str):
        with get_session() as session:
            member = session.query(Member).filter(
                Member.discord_id == str(discord_id)
            ).first()
            if member:
                session.delete(member)
                return True
            return False
    
    @staticmethod
    def get_all_members(status=None):
        with get_session() as session:
            query = session.query(Member)
            if status:
                query = query.filter(Member.status == status)
            return query.all()
    
    @staticmethod
    def create_meeting(**kwargs):
        with get_session() as session:
            meeting = Meeting(**kwargs)
            session.add(meeting)
            session.flush()
            return meeting
    
    @staticmethod
    def get_meeting(meeting_id: int):
        with get_session() as session:
            return session.query(Meeting).filter(
                Meeting.id == meeting_id
            ).first()
    
    @staticmethod
    def get_upcoming_meetings(limit=5):
        with get_session() as session:
            return session.query(Meeting).filter(
                Meeting.date >= datetime.utcnow()
            ).order_by(Meeting.date).limit(limit).all()
    
    @staticmethod
    def record_attendance(meeting_id: int, member_id: int, status='present'):
        with get_session() as session:
            attendance = session.query(Attendance).filter(
                Attendance.meeting_id == meeting_id,
                Attendance.member_id == member_id
            ).first()
            
            if not attendance:
                attendance = Attendance(
                    meeting_id=meeting_id,
                    member_id=member_id,
                    status=status
                )
                session.add(attendance)
            else:
                attendance.status = status
                attendance.timestamp = datetime.utcnow()
            
            return attendance
    
    @staticmethod
    def get_member_stats(member_id: int, days=30):
        with get_session() as session:
            since = datetime.utcnow() - timedelta(days=days)
            
            total_meetings = session.query(Meeting).filter(
                Meeting.date >= since,
                Meeting.is_completed == True
            ).count()
            
            attended = session.query(Attendance).join(Meeting).filter(
                Attendance.member_id == member_id,
                Attendance.status == 'present',
                Meeting.date >= since
            ).count()
            
            return {
                'total': total_meetings,
                'attended': attended,
                'rate': (attended / total_meetings * 100) if total_meetings > 0 else 0
            }