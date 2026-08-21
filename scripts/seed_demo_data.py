"""
Seed catalogs + demo users for local development.

Usage (from repo root, venv active):

    python -m scripts.seed_demo_data

Idempotent: re-running upserts catalogs and skips existing demo users.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

import bcrypt
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.auth import User
from app.models.availability import ListenerAvailabilitySettings, ListenerAvailabilitySlot
from app.models.earnings import ListenerWallet
from app.models.enums import (
    CallMode,
    DayOfWeek,
    EarningsTier,
    Gender,
    InviteStatus,
    MoodKind,
    NotificationType,
    ProfileStatus,
    RewardOfferKind,
    SessionStatus,
    SessionTimeMode,
    SetupStepStatus,
    TrainingStatus,
    UserRole,
)
from app.models.lookups import (
    Boundary,
    ComfortArea,
    Language,
    LifeExperience,
    ListenerBoundary,
    ListenerComfortArea,
    ListenerLanguage,
    ListenerLifeExperience,
    VentorInterest,
)
from app.models.notifications import Notification
from app.models.profiles import ListenerProfile, VentorProfile
from app.models.promo import PromoCode
from app.models.rewards import InviteCode, InviteEvent, RewardOffer
from app.models.sessions import Session as VentingSession
from app.models.settings import (
    ListenerNotificationPreferences,
    ListenerPrivacySettings,
    VentorNotificationPreferences,
    VentorPrivacySettings,
)
from app.models.training import ListenerTrainingProgress, TrainingModule
from app.models.ventor_wellness import Achievement, MoodCheckin, VentorFavorite

DEMO_PASSWORD = "Password123!"


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _upsert_by_id(db: Session, model, rows: list[dict], pk: str = "id") -> None:
    for row in rows:
        existing = db.get(model, row[pk])
        if existing is None:
            db.add(model(**row))
        else:
            for key, value in row.items():
                if key != pk:
                    setattr(existing, key, value)


def seed_catalogs(db: Session) -> None:
    _upsert_by_id(
        db,
        Language,
        [
            {"id": "en", "name_en": "English", "name_ar": "الإنجليزية", "is_active": True},
            {"id": "ar", "name_en": "Arabic", "name_ar": "العربية", "is_active": True},
            {"id": "fr", "name_en": "French", "name_ar": "الفرنسية", "is_active": True},
        ],
    )

    _upsert_by_id(
        db,
        ComfortArea,
        [
            {"id": "relationships", "name_en": "Relationships", "name_ar": "العلاقات", "topic_group": "relationships", "is_active": True},
            {"id": "marriage", "name_en": "Marriage", "name_ar": "الزواج", "topic_group": "relationships", "is_active": True},
            {"id": "parenting", "name_en": "Parenting", "name_ar": "الأبوة والأمومة", "topic_group": "family", "is_active": True},
            {"id": "career_work", "name_en": "Career / Work", "name_ar": "العمل والمسار المهني", "topic_group": "career", "is_active": True},
            {"id": "stress_anxiety", "name_en": "Stress / Anxiety", "name_ar": "التوتر والقلق", "topic_group": "mental", "is_active": True},
            {"id": "loneliness", "name_en": "Loneliness", "name_ar": "الوحدة", "topic_group": "mental", "is_active": True},
            {"id": "student_life", "name_en": "Student life", "name_ar": "حياة الطالب", "topic_group": "life", "is_active": True},
            {"id": "financial_stress", "name_en": "Financial stress", "name_ar": "الضغط المالي", "topic_group": "money", "is_active": True},
            {"id": "health_wellness", "name_en": "Health / Wellness", "name_ar": "الصحة والعافية", "topic_group": "health", "is_active": True},
        ],
    )

    _upsert_by_id(
        db,
        LifeExperience,
        [
            {"id": "single", "name_en": "Single", "name_ar": "أعزب / عزباء", "is_active": True},
            {"id": "in_relationship", "name_en": "In a relationship", "name_ar": "في علاقة", "is_active": True},
            {"id": "married", "name_en": "Married", "name_ar": "متزوج / متزوجة", "is_active": True},
            {"id": "divorced", "name_en": "Divorced", "name_ar": "مطلق / مطلقة", "is_active": True},
            {"id": "widowed", "name_en": "Widowed", "name_ar": "أرمل / أرملة", "is_active": True},
            {"id": "parent", "name_en": "Parent", "name_ar": "والد / والدة", "is_active": True},
            {"id": "single_parent", "name_en": "Single parent", "name_ar": "والد / والدة وحيد/ة", "is_active": True},
            {"id": "caregiver", "name_en": "Caregiver", "name_ar": "مقدّم رعاية", "is_active": True},
            {"id": "career_change", "name_en": "Career change", "name_ar": "تغيير مسار مهني", "is_active": True},
            {"id": "job_loss", "name_en": "Job loss", "name_ar": "فقدان العمل", "is_active": True},
            {"id": "startup_founder", "name_en": "Startup founder", "name_ar": "مؤسس شركة ناشئة", "is_active": True},
            {"id": "financial_struggle", "name_en": "Financial struggle", "name_ar": "صعوبات مالية", "is_active": True},
            {"id": "life_stages", "name_en": "Life stages", "name_ar": "مراحل الحياة", "is_active": True},
            {"id": "grief_loss", "name_en": "Grief / Loss", "name_ar": "الحزن / الفقد", "is_active": True},
            {"id": "anxiety_stress", "name_en": "Anxiety / Stress", "name_ar": "القلق / التوتر", "is_active": True},
            {"id": "health_challenge", "name_en": "Health challenge", "name_ar": "تحدي صحي", "is_active": True},
            {"id": "addiction_recovery", "name_en": "Addiction recovery", "name_ar": "التعافي من الإدمان", "is_active": True},
        ],
    )

    _upsert_by_id(
        db,
        Boundary,
        [
            {"id": "suicide_self_harm", "name_en": "Suicide / Self-harm", "name_ar": "الانتحار / إيذاء النفس", "is_active": True},
            {"id": "domestic_violence", "name_en": "Domestic violence", "name_ar": "العنف الأسري", "is_active": True},
            {"id": "sexual_topics", "name_en": "Sexual topics", "name_ar": "مواضيع جنسية", "is_active": True},
            {"id": "addiction", "name_en": "Addiction", "name_ar": "الإدمان", "is_active": True},
            {"id": "politics", "name_en": "Politics", "name_ar": "السياسة", "is_active": True},
            {"id": "religion", "name_en": "Religion", "name_ar": "الدين", "is_active": True},
            {"id": "illegal_activities", "name_en": "Illegal activities", "name_ar": "أنشطة غير قانونية", "is_active": True},
        ],
    )

    _upsert_by_id(
        db,
        Achievement,
        [
            {"id": "first_session", "title_key": "achievements.first_session.title", "subtitle_key": "achievements.first_session.subtitle", "description_key": "achievements.first_session.description", "sort_order": 1, "is_active": True},
            {"id": "mood_streak_3", "title_key": "achievements.mood_streak_3.title", "subtitle_key": "achievements.mood_streak_3.subtitle", "description_key": "achievements.mood_streak_3.description", "sort_order": 2, "is_active": True},
            {"id": "invited_friend", "title_key": "achievements.invited_friend.title", "subtitle_key": "achievements.invited_friend.subtitle", "description_key": "achievements.invited_friend.description", "sort_order": 3, "is_active": True},
        ],
    )

    _upsert_by_id(
        db,
        TrainingModule,
        [
            {"id": "art_of_listening", "title_key": "training.art_of_listening", "content_url": "https://example.com/training/art-of-listening", "sort_order": 1, "is_active": True},
            {"id": "empathy", "title_key": "training.empathy", "content_url": "https://example.com/training/empathy", "sort_order": 2, "is_active": True},
            {"id": "boundaries", "title_key": "training.boundaries", "content_url": "https://example.com/training/boundaries", "sort_order": 3, "is_active": True},
            {"id": "difficult_situations", "title_key": "training.difficult_situations", "content_url": "https://example.com/training/difficult-situations", "sort_order": 4, "is_active": True},
            {"id": "crisis_awareness", "title_key": "training.crisis_awareness", "content_url": "https://example.com/training/crisis-awareness", "sort_order": 5, "is_active": True},
            # Legacy seed modules kept active for existing progress rows
            {"id": "setting_boundaries", "title_key": "training.setting_boundaries", "content_url": "https://example.com/training/boundaries", "sort_order": 90, "is_active": False},
            {"id": "first_session_ready", "title_key": "training.first_session_ready", "content_url": "https://example.com/training/first-session", "sort_order": 91, "is_active": False},
        ],
    )

    # Fixed UUIDs so re-runs stay stable
    offer_welcome = uuid.UUID("11111111-1111-1111-1111-111111111111")
    offer_off20 = uuid.UUID("22222222-2222-2222-2222-222222222222")
    promo_welcome = uuid.UUID("33333333-3333-3333-3333-333333333333")

    if db.get(RewardOffer, offer_welcome) is None:
        db.add(
            RewardOffer(
                id=offer_welcome,
                code="welcome_gift",
                kind=RewardOfferKind.free_minutes,
                points_cost=0,
                free_minutes=10,
                is_welcome_gift=True,
                is_active=True,
            )
        )
    if db.get(RewardOffer, offer_off20) is None:
        db.add(
            RewardOffer(
                id=offer_off20,
                code="off_20_any",
                kind=RewardOfferKind.percent_off,
                points_cost=200,
                percent_off=20,
                is_welcome_gift=False,
                is_active=True,
            )
        )
    if db.get(PromoCode, promo_welcome) is None:
        db.add(
            PromoCode(
                id=promo_welcome,
                code="WELCOME20",
                percent_off=20,
                max_redemptions=1000,
                redemption_count=0,
                is_active=True,
            )
        )

    demo_promos = [
        (uuid.UUID("33333333-3333-3333-3333-333333333334"), "SAVE10", 10, None),
        (uuid.UUID("33333333-3333-3333-3333-333333333335"), "VENT5", None, Decimal("5.00")),
        (uuid.UUID("33333333-3333-3333-3333-333333333336"), "WELCOME15", 15, None),
    ]
    for promo_id, code, percent, fixed in demo_promos:
        if db.get(PromoCode, promo_id) is None:
            db.add(
                PromoCode(
                    id=promo_id,
                    code=code,
                    percent_off=percent,
                    fixed_amount=fixed,
                    max_redemptions=1000,
                    redemption_count=0,
                    is_active=True,
                )
            )

    db.flush()


def _user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).one_or_none()


def seed_demo_users(db: Session) -> dict[str, uuid.UUID]:
    password_hash = _hash_password(DEMO_PASSWORD)
    ids: dict[str, uuid.UUID] = {}

    # --- Ventor ---
    ventor_email = "ventor@venting.app"
    ventor = _user_by_email(db, ventor_email)
    if ventor is None:
        ventor = User(
            id=uuid.uuid4(),
            email=ventor_email,
            password_hash=password_hash,
            role=UserRole.ventor,
            is_active=True,
            registration_complete=True,
            last_login_at=datetime.now(timezone.utc),
        )
        db.add(ventor)
        db.flush()
        db.add(
            VentorProfile(
                user_id=ventor.id,
                nickname="Sam",
                gender=Gender.prefer_not_to_say,
                quote="Looking for a calm space to talk.",
                is_anonymous=True,
                points_balance=250,
                mood_streak_days=2,
                last_mood_checkin_date=date.today(),
                completed_sessions_count=1,
                active_reward_offer_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            )
        )
        db.flush()
        db.add(VentorPrivacySettings(ventor_id=ventor.id))
        db.add(VentorNotificationPreferences(ventor_id=ventor.id))
        db.add(VentorInterest(ventor_id=ventor.id, comfort_area_id="stress_anxiety"))
        db.add(VentorInterest(ventor_id=ventor.id, comfort_area_id="relationships"))
        db.add(
            MoodCheckin(
                ventor_id=ventor.id,
                mood=MoodKind.okay,
                note="Feeling a bit overwhelmed today.",
                checkin_date=date.today() - timedelta(days=1),
            )
        )
        db.add(
            MoodCheckin(
                ventor_id=ventor.id,
                mood=MoodKind.great,
                note="Better after talking it out.",
                checkin_date=date.today(),
            )
        )
        db.add(
            InviteCode(
                ventor_id=ventor.id,
                code="SAM-INVITE",
                invite_link="https://venting.app/invite/SAM-INVITE",
            )
        )
        print(f"  + created ventor {ventor_email}")
    else:
        print(f"  · ventor exists {ventor_email}")
    ids["ventor"] = ventor.id

    # --- Listener 1 (approved, online) ---
    listener_email = "listener@venting.app"
    listener = _user_by_email(db, listener_email)
    if listener is None:
        listener = User(
            id=uuid.uuid4(),
            email=listener_email,
            password_hash=password_hash,
            role=UserRole.listener,
            is_active=True,
            registration_complete=True,
            last_login_at=datetime.now(timezone.utc),
        )
        db.add(listener)
        db.flush()
        db.add(
            ListenerProfile(
                user_id=listener.id,
                full_name="Layla Hassan",
                phone_e164="+96170123456",
                phone_country_iso="LB",
                about_me="I love helping people feel heard.",
                date_of_birth=date(1994, 5, 12),
                country="Lebanon",
                country_iso="LB",
                city="Beirut",
                gender=Gender.female,
                bio="Warm, patient listener. Comfortable with stress & relationships.",
                is_online=True,
                is_verified=True,
                profile_status=ProfileStatus.approved,
                accept_instant_calls=True,
                session_length_minutes=30,
                break_length_minutes=15,
                time_zone_id="Asia/Beirut",
                rate_per_minute=Decimal("0.25"),
                current_tier=EarningsTier.starter,
                rating_avg=Decimal("4.80"),
                rating_count=12,
                session_count=18,
                rating_breakdown={"5": 10, "4": 2, "3": 0, "2": 0, "1": 0},
                setup_identity_status=SetupStepStatus.done,
                setup_profile_status=SetupStepStatus.done,
                setup_availability_status=SetupStepStatus.done,
                setup_training_status=SetupStepStatus.done,
                setup_tutorial_status=SetupStepStatus.done,
                agreed_to_terms_at=datetime.now(timezone.utc),
            )
        )
        db.flush()
        db.add(
            ListenerAvailabilitySettings(
                listener_id=listener.id,
                accept_instant_calls=True,
                session_length_minutes=30,
                break_length_minutes=15,
                time_zone_id="Asia/Beirut",
            )
        )
        for day in (DayOfWeek.mon, DayOfWeek.wed, DayOfWeek.fri):
            db.add(
                ListenerAvailabilitySlot(
                    listener_id=listener.id,
                    day=day,
                    start_time=time(18, 0),
                    end_time=time(21, 0),
                )
            )
        db.add(ListenerPrivacySettings(listener_id=listener.id))
        db.add(ListenerNotificationPreferences(listener_id=listener.id))
        db.add(
            ListenerWallet(
                listener_id=listener.id,
                available_balance=Decimal("42.50"),
                pending_balance=Decimal("7.50"),
                lifetime_earned=Decimal("120.00"),
            )
        )
        for lang in ("en", "ar"):
            db.add(ListenerLanguage(listener_id=listener.id, language_id=lang))
        for area in ("stress_anxiety", "relationships", "parenting"):
            db.add(ListenerComfortArea(listener_id=listener.id, comfort_area_id=area))
        for exp in ("anxiety_stress", "life_stages", "in_relationship"):
            db.add(ListenerLifeExperience(listener_id=listener.id, life_experience_id=exp))
        for boundary in ("politics", "illegal_activities"):
            db.add(ListenerBoundary(listener_id=listener.id, boundary_id=boundary))
        for module_id in (
            "art_of_listening",
            "empathy",
            "boundaries",
            "difficult_situations",
            "crisis_awareness",
        ):
            db.add(
                ListenerTrainingProgress(
                    listener_id=listener.id,
                    module_id=module_id,
                    status=TrainingStatus.completed,
                    completed_at=datetime.now(timezone.utc),
                )
            )
        print(f"  + created listener {listener_email}")
    else:
        print(f"  · listener exists {listener_email}")
    ids["listener"] = listener.id

    # --- Listener 2 (rising tier) ---
    listener2_email = "listener2@venting.app"
    listener2 = _user_by_email(db, listener2_email)
    if listener2 is None:
        listener2 = User(
            id=uuid.uuid4(),
            email=listener2_email,
            password_hash=password_hash,
            role=UserRole.listener,
            is_active=True,
            registration_complete=True,
        )
        db.add(listener2)
        db.flush()
        db.add(
            ListenerProfile(
                user_id=listener2.id,
                full_name="Omar Faris",
                country="United Arab Emirates",
                country_iso="AE",
                city="Dubai",
                gender=Gender.male,
                bio="Career coach energy with a calm listening style.",
                is_online=False,
                is_verified=True,
                profile_status=ProfileStatus.approved,
                time_zone_id="Asia/Dubai",
                rate_per_minute=Decimal("0.33"),
                current_tier=EarningsTier.rising,
                rating_avg=Decimal("4.60"),
                rating_count=28,
                session_count=40,
                rating_breakdown={"5": 20, "4": 6, "3": 2, "2": 0, "1": 0},
                setup_identity_status=SetupStepStatus.done,
                setup_profile_status=SetupStepStatus.done,
                setup_availability_status=SetupStepStatus.done,
                setup_training_status=SetupStepStatus.done,
                setup_tutorial_status=SetupStepStatus.done,
                agreed_to_terms_at=datetime.now(timezone.utc),
            )
        )
        db.flush()
        db.add(
            ListenerAvailabilitySettings(
                listener_id=listener2.id,
                accept_instant_calls=False,
                session_length_minutes=45,
                break_length_minutes=15,
                time_zone_id="Asia/Dubai",
            )
        )
        db.add(ListenerPrivacySettings(listener_id=listener2.id))
        db.add(ListenerNotificationPreferences(listener_id=listener2.id))
        db.add(ListenerWallet(listener_id=listener2.id, available_balance=Decimal("210.00")))
        db.add(ListenerLanguage(listener_id=listener2.id, language_id="en"))
        db.add(ListenerLanguage(listener_id=listener2.id, language_id="ar"))
        db.add(ListenerComfortArea(listener_id=listener2.id, comfort_area_id="career_work"))
        db.add(ListenerComfortArea(listener_id=listener2.id, comfort_area_id="stress_anxiety"))
        db.add(ListenerLifeExperience(listener_id=listener2.id, life_experience_id="career_change"))
        db.add(ListenerBoundary(listener_id=listener2.id, boundary_id="religion"))
        print(f"  + created listener {listener2_email}")
    else:
        print(f"  · listener exists {listener2_email}")
    ids["listener2"] = listener2.id

    db.flush()

    # Favorites + invite event + notification + sample completed session
    if (
        db.query(VentorFavorite)
        .filter_by(ventor_id=ids["ventor"], listener_id=ids["listener"])
        .one_or_none()
        is None
    ):
        db.add(VentorFavorite(ventor_id=ids["ventor"], listener_id=ids["listener"]))

    invite = db.query(InviteCode).filter_by(ventor_id=ids["ventor"]).one_or_none()
    if invite and db.query(InviteEvent).filter_by(invite_code_id=invite.id).count() == 0:
        db.add(
            InviteEvent(
                invite_code_id=invite.id,
                inviter_ventor_id=ids["ventor"],
                invitee_user_id=ids["listener"],
                invitee_display_name="Layla Hassan",
                status=InviteStatus.joined,
                points_earned=50,
            )
        )

    if (
        db.query(Notification)
        .filter_by(user_id=ids["listener"], title="Welcome to Venting")
        .one_or_none()
        is None
    ):
        db.add(
            Notification(
                user_id=ids["listener"],
                type=NotificationType.system,
                title="Welcome to Venting",
                body="Your listener profile is ready. Turn online when you want sessions.",
                data={"screen": "listener_dashboard"},
                is_read=False,
            )
        )

    if (
        db.query(VentingSession)
        .filter_by(ventor_id=ids["ventor"], listener_id=ids["listener"])
        .count()
        == 0
    ):
        started = datetime.now(timezone.utc) - timedelta(days=2, hours=1)
        ended = started + timedelta(minutes=28)
        db.add(
            VentingSession(
                ventor_id=ids["ventor"],
                listener_id=ids["listener"],
                status=SessionStatus.completed,
                duration_minutes=30,
                actual_duration_seconds=28 * 60,
                time_mode=SessionTimeMode.scheduled,
                scheduled_at=started,
                started_at=started,
                ended_at=ended,
                call_mode=CallMode.voice,
                speech_language="en",
                voice_change_enabled=False,
                is_instant=False,
                message="Needed someone to talk about work stress.",
                tags=["stress_anxiety", "career_work"],
                listener_history_outcome="accepted",
            )
        )

    return ids


def main() -> None:
    get_settings.cache_clear()
    settings = get_settings()
    print(f"Seeding {settings.database_name} @ {settings.database_hostname}...")

    db = SessionLocal()
    try:
        print("Catalogs:")
        seed_catalogs(db)
        print("Demo users:")
        seed_demo_users(db)
        db.commit()
        print("\nDone.")
        print("Demo logins (password for all):", DEMO_PASSWORD)
        print("  ventor@venting.app")
        print("  listener@venting.app")
        print("  listener2@venting.app")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
