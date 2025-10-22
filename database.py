# Gestionnaire de base de données (database.py)

from contextlib import contextmanager
from models import Session, Member, Meeting, Attendance, MemberStatus
from datetime import datetime, timedelta
import logging
import json

logger = logging.getLogger(__name__)


# Contexte de session pour les opérations DB
@contextmanager
def get_session():
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


# Classe utilitaire pour les opérations de base de données
class Database:

    # --- Membres ---
    @staticmethod
    def get_member(discord_id: str):
        with get_session() as session:
            member = (
                session.query(Member)
                .filter(Member.discord_id == str(discord_id))
                .first()
            )
            if member:
                # Charger complètement l'objet avant fermeture de la session
                session.expunge(member)
            return member

    @staticmethod
    def add_member(**kwargs):
        with get_session() as session:
            member = Member(**kwargs)
            session.add(member)
            session.flush()  # pour obtenir l'ID
            session.expunge(member)  # détacher proprement avant return
            return member

    @staticmethod
    def update_member(discord_id: str, **kwargs):
        with get_session() as session:
            member = (
                session.query(Member)
                .filter(Member.discord_id == str(discord_id))
                .first()
            )
            if member:
                for key, value in kwargs.items():
                    setattr(member, key, value)
                member.last_active = datetime.utcnow()
                session.flush()
                session.expunge(member)
            return member

    @staticmethod
    def delete_member(discord_id: str):
        with get_session() as session:
            member = (
                session.query(Member)
                .filter(Member.discord_id == str(discord_id))
                .first()
            )
            if member:
                session.delete(member)
                return True
            return False

    @staticmethod
    def get_all_members(status=None, role=None):
        with get_session() as session:
            query = session.query(Member)
            if status:
                query = query.filter(Member.status == status)
            if role:
                query = query.filter(Member.role == role)
            members = query.order_by(Member.full_name).all()
            for m in members:
                session.expunge(m)
            return members

    @staticmethod
    def get_members_by_roles(roles):
        """Récupérer les membres ayant un des rôles spécifiés"""
        with get_session() as session:
            if "ALL" in roles:
                members = (
                    session.query(Member)
                    .filter(Member.status == MemberStatus.ACTIVE)
                    .all()
                )
            else:
                members = (
                    session.query(Member)
                    .filter(
                        Member.role.in_(roles), Member.status == MemberStatus.ACTIVE
                    )
                    .all()
                )
            for m in members:
                session.expunge(m)
            return members

    # --- Meetings ---
    @staticmethod
    def create_meeting(**kwargs):
        with get_session() as session:
            meeting = Meeting(**kwargs)
            # Gérer les rôles ciblés
            if "target_roles" in kwargs:
                roles = kwargs["target_roles"]
                meeting.set_target_roles(roles)
            session.add(meeting)
            session.flush()
            session.expunge(meeting)
            return meeting

    @staticmethod
    def get_meeting(meeting_id: int):
        with get_session() as session:
            meeting = session.query(Meeting).filter(Meeting.id == meeting_id).first()
            if meeting:
                session.expunge(meeting)
            return meeting

    @staticmethod
    def get_meeting_by_name(name: str):
        """Rechercher une réunion par son nom"""
        with get_session() as session:
            meetings = (
                session.query(Meeting)
                .filter(Meeting.title.ilike(f"%{name}%"))
                .filter(Meeting.is_completed == False)
                .all()
            )
            for m in meetings:
                session.expunge(m)
            return meetings

    @staticmethod
    def get_upcoming_meetings(limit=5, role=None):
        with get_session() as session:
            query = session.query(Meeting).filter(Meeting.date >= datetime.utcnow())

            # Filtrer par rôle si spécifié
            if role:
                # Rechercher les meetings qui ciblent ce rôle ou ALL
                meetings = query.all()
                filtered = []
                for meeting in meetings:
                    target_roles = meeting.get_target_roles()
                    if "ALL" in target_roles or role in target_roles:
                        filtered.append(meeting)
                meetings = filtered[:limit]
            else:
                meetings = query.order_by(Meeting.date).limit(limit).all()

            for m in meetings:
                session.expunge(m)
            return meetings

    # --- Présence ---
    @staticmethod
    def record_attendance(
        meeting_id: int, member_id: int, status="present", modified_by=None
    ):
        with get_session() as session:
            attendance = (
                session.query(Attendance)
                .filter(
                    Attendance.meeting_id == meeting_id,
                    Attendance.member_id == member_id,
                )
                .first()
            )

            if not attendance:
                attendance = Attendance(
                    meeting_id=meeting_id, member_id=member_id, status=status
                )
                session.add(attendance)
            else:
                attendance.status = status
                attendance.timestamp = datetime.utcnow()
                if modified_by:
                    attendance.modified_at = datetime.utcnow()
                    attendance.modified_by = modified_by

            session.flush()
            session.expunge(attendance)
            return attendance

    @staticmethod
    def validate_attendance(meeting_id: int, validated_by: str):
        """Valider l'appel d'une réunion"""
        with get_session() as session:
            meeting = session.query(Meeting).filter(Meeting.id == meeting_id).first()
            if meeting:
                meeting.attendance_validated = True
                meeting.attendance_validated_at = datetime.utcnow()
                meeting.attendance_validated_by = validated_by
                session.flush()
                return True
            return False

    @staticmethod
    def get_meeting_attendance(meeting_id: int):
        """Récupérer la liste des présences pour une réunion"""
        with get_session() as session:
            attendances = (
                session.query(Attendance, Member)
                .join(Member)
                .filter(Attendance.meeting_id == meeting_id)
                .all()
            )
            result = []
            for att, member in attendances:
                session.expunge(att)
                session.expunge(member)
                result.append((att, member))
            return result

    @staticmethod
    def get_meeting_stats(meeting_id: int):
        """Retourne des statistiques pour une réunion donnée:
        - present, absent, excused counts
        - expected attendees (selon target_roles)
        - participation rate (en pourcentage)
        """
        with get_session() as session:
            meeting = session.query(Meeting).filter(Meeting.id == meeting_id).first()
            if not meeting:
                return None

            # Comptages des présences
            present = (
                session.query(Attendance)
                .filter(
                    Attendance.meeting_id == meeting_id, Attendance.status == "present"
                )
                .count()
            )
            absent = (
                session.query(Attendance)
                .filter(
                    Attendance.meeting_id == meeting_id, Attendance.status == "absent"
                )
                .count()
            )
            excused = (
                session.query(Attendance)
                .filter(
                    Attendance.meeting_id == meeting_id, Attendance.status == "excused"
                )
                .count()
            )

            # Calculer le nombre attendu selon les rôles ciblés
            target_roles = meeting.get_target_roles()
            if "ALL" in target_roles:
                expected = (
                    session.query(Member)
                    .filter(Member.status == MemberStatus.ACTIVE)
                    .count()
                )
            else:
                expected = (
                    session.query(Member)
                    .filter(
                        Member.role.in_(target_roles),
                        Member.status == MemberStatus.ACTIVE,
                    )
                    .count()
                )

            rate = (present / expected * 100) if expected > 0 else 0

            return {
                "meeting": meeting,
                "present": present,
                "absent": absent,
                "excused": excused,
                "expected": expected,
                "rate": rate,
            }

    # --- Statistiques ---
    @staticmethod
    def get_member_stats(member_id: int, days=30):
        with get_session() as session:
            since = datetime.utcnow() - timedelta(days=days)

            # Récupérer le membre pour son rôle
            member = session.query(Member).filter(Member.id == member_id).first()
            if not member:
                return {"total": 0, "attended": 0, "rate": 0}

            # Meetings concernant ce membre
            all_meetings = (
                session.query(Meeting)
                .filter(
                    Meeting.date >= since,
                    Meeting.date <= datetime.utcnow(),
                    Meeting.is_completed == True,
                )
                .all()
            )

            # Filtrer par rôle ciblé
            relevant_meetings = []
            for meeting in all_meetings:
                target_roles = meeting.get_target_roles()
                if "ALL" in target_roles or member.role in target_roles:
                    relevant_meetings.append(meeting.id)

            total_meetings = len(relevant_meetings)

            # Compter les présences
            attended = (
                (
                    session.query(Attendance)
                    .filter(
                        Attendance.member_id == member_id,
                        Attendance.status == "present",
                        (
                            Attendance.meeting_id.in_(relevant_meetings)
                            if relevant_meetings
                            else False
                        ),
                    )
                    .count()
                )
                if relevant_meetings
                else 0
            )

            return {
                "total": total_meetings,
                "attended": attended,
                "rate": (attended / total_meetings * 100) if total_meetings > 0 else 0,
            }

    @staticmethod
    def get_role_stats(role: str, days=30):
        """Statistiques par pôle (DEV, IA, INFRA)"""
        with get_session() as session:
            since = datetime.utcnow() - timedelta(days=days)

            # Membres du pôle
            members = (
                session.query(Member)
                .filter(Member.role == role, Member.status == MemberStatus.ACTIVE)
                .all()
            )

            if not members:
                return {
                    "role": role,
                    "members_count": 0,
                    "avg_attendance_rate": 0,
                    "total_meetings": 0,
                    "top_members": [],
                }

            # Meetings concernant ce pôle
            all_meetings = (
                session.query(Meeting)
                .filter(
                    Meeting.date >= since,
                    Meeting.date <= datetime.utcnow(),
                    Meeting.is_completed == True,
                )
                .all()
            )

            relevant_meetings = []
            for meeting in all_meetings:
                target_roles = meeting.get_target_roles()
                if "ALL" in target_roles or role in target_roles:
                    relevant_meetings.append(meeting.id)

            # Calculer le taux de présence moyen
            total_rate = 0
            member_stats = []

            for member in members:
                stats = Database.get_member_stats(member.id, days)
                total_rate += stats["rate"]
                member_stats.append(
                    {
                        "member": member.full_name or member.username,
                        "rate": stats["rate"],
                        "attended": stats["attended"],
                    }
                )

            # Trier pour avoir le top des membres
            member_stats.sort(key=lambda x: x["rate"], reverse=True)

            return {
                "role": role,
                "members_count": len(members),
                "avg_attendance_rate": total_rate / len(members) if members else 0,
                "total_meetings": len(relevant_meetings),
                "top_members": member_stats[:5],  # Top 5
            }

    @staticmethod
    def get_global_stats(days=30):
        """Statistiques globales du laboratoire"""
        with get_session() as session:
            since = datetime.utcnow() - timedelta(days=days)

            # Total membres actifs
            active_members = (
                session.query(Member)
                .filter(Member.status == MemberStatus.ACTIVE)
                .count()
            )

            # Total réunions
            total_meetings = (
                session.query(Meeting)
                .filter(
                    Meeting.date >= since,
                    Meeting.date <= datetime.utcnow(),
                    Meeting.is_completed == True,
                )
                .count()
            )

            # Calcul du taux de participation global
            if total_meetings > 0:
                total_expected = (
                    session.query(Meeting)
                    .filter(
                        Meeting.date >= since,
                        Meeting.date <= datetime.utcnow(),
                        Meeting.is_completed == True,
                    )
                    .all()
                )

                total_attendances = 0
                total_expected_attendances = 0

                for meeting in total_expected:
                    target_roles = meeting.get_target_roles()
                    if "ALL" in target_roles:
                        expected = active_members
                    else:
                        expected = (
                            session.query(Member)
                            .filter(
                                Member.role.in_(target_roles),
                                Member.status == MemberStatus.ACTIVE,
                            )
                            .count()
                        )

                    actual = (
                        session.query(Attendance)
                        .filter(
                            Attendance.meeting_id == meeting.id,
                            Attendance.status == "present",
                        )
                        .count()
                    )

                    total_attendances += actual
                    total_expected_attendances += expected

                global_rate = (
                    (total_attendances / total_expected_attendances * 100)
                    if total_expected_attendances > 0
                    else 0
                )
            else:
                global_rate = 0

            return {
                "active_members": active_members,
                "total_meetings": total_meetings,
                "global_attendance_rate": global_rate,
                "period_days": days,
            }
