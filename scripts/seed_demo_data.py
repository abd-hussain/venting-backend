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
    AdminStatus,
    BannerPlacement,
    CallMode,
    CmsPageStatus,
    DayOfWeek,
    EarningsTier,
    Gender,
    InviteStatus,
    ModerationActionType,
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
from app.models.admin import (
    AdminAuditLog,
    AdminNote,
    AdminRole,
    AdminUser,
    AdminUserRole,
    AppConfigKv,
    AppFeatureFlag,
    CmsBanner,
    CmsPage,
    ModerationAction,
)

DEMO_PASSWORD = "Password123!"
DEMO_ADMIN_PASSWORD = "Admin123!"


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
            {"id": "en", "name_en": "English", "name_native": "English", "name_ar": "الإنجليزية", "flag_url": "https://flagcdn.com/w160/gb.png", "flag_emoji": "🇬🇧", "sort_order": 10, "is_active": True},
            {"id": "hi", "name_en": "Hindi", "name_native": "हिन्दी", "name_ar": "الهندية", "flag_url": "https://flagcdn.com/w160/in.png", "flag_emoji": "🇮🇳", "sort_order": 20, "is_active": True},
            {"id": "es", "name_en": "Spanish", "name_native": "Español", "name_ar": "الإسبانية", "flag_url": "https://flagcdn.com/w160/es.png", "flag_emoji": "🇪🇸", "sort_order": 30, "is_active": True},
            {"id": "ar", "name_en": "Arabic", "name_native": "العربية", "name_ar": "العربية", "flag_url": "https://flagcdn.com/w160/sa.png", "flag_emoji": "🇸🇦", "sort_order": 40, "is_active": True},
            {"id": "bn", "name_en": "Bengali", "name_native": "বাংলা", "name_ar": "البنغالية", "flag_url": "https://flagcdn.com/w160/bd.png", "flag_emoji": "🇧🇩", "sort_order": 50, "is_active": True},
            {"id": "tr", "name_en": "Turkish", "name_native": "Türkçe", "name_ar": "التركية", "flag_url": "https://flagcdn.com/w160/tr.png", "flag_emoji": "🇹🇷", "sort_order": 60, "is_active": True},
            {"id": "fr", "name_en": "French", "name_native": "Français", "name_ar": "الفرنسية", "flag_url": "https://flagcdn.com/w160/fr.png", "flag_emoji": "🇫🇷", "sort_order": 70, "is_active": True},
        ],
    )

    _upsert_by_id(
        db,
        ComfortArea,
        [
            {"id": "relationships", "name_en": "Relationships", "name_ar": "العلاقات", "icon_emoji": "❤️", "icon_url": None, "sort_order": 10, "allows_custom_text": False, "audience": "ventor", "topic_group": "relationships", "is_active": True},
            {"id": "marriage", "name_en": "Marriage", "name_ar": "الزواج", "icon_emoji": "💍", "icon_url": None, "sort_order": 20, "allows_custom_text": False, "audience": "ventor", "topic_group": "relationships", "is_active": True},
            {"id": "parenting", "name_en": "Parenting", "name_ar": "الأبوة والأمومة", "icon_emoji": "👨‍👩‍👧", "icon_url": None, "sort_order": 30, "allows_custom_text": False, "audience": "ventor", "topic_group": "family", "is_active": True},
            {"id": "career_work", "name_en": "Career & work", "name_ar": "العمل والمسار المهني", "icon_emoji": "💼", "icon_url": None, "sort_order": 40, "allows_custom_text": False, "audience": "ventor", "topic_group": "career", "is_active": True},
            {"id": "stress_anxiety", "name_en": "Stress & anxiety", "name_ar": "التوتر والقلق", "icon_emoji": "😰", "icon_url": None, "sort_order": 50, "allows_custom_text": False, "audience": "ventor", "topic_group": "mental", "is_active": True},
            {"id": "loneliness", "name_en": "Loneliness", "name_ar": "الوحدة", "icon_emoji": "😔", "icon_url": None, "sort_order": 60, "allows_custom_text": False, "audience": "ventor", "topic_group": "mental", "is_active": True},
            {"id": "student_life", "name_en": "Student life", "name_ar": "حياة الطالب", "icon_emoji": "🎓", "icon_url": None, "sort_order": 70, "allows_custom_text": False, "audience": "ventor", "topic_group": "life", "is_active": True},
            {"id": "financial_stress", "name_en": "Financial stress", "name_ar": "الضغط المالي", "icon_emoji": "💰", "icon_url": None, "sort_order": 80, "allows_custom_text": False, "audience": "ventor", "topic_group": "money", "is_active": True},
            {"id": "health_wellness", "name_en": "Health & wellness", "name_ar": "الصحة والعافية", "icon_emoji": "🩺", "icon_url": None, "sort_order": 90, "allows_custom_text": False, "audience": "ventor", "topic_group": "health", "is_active": True},
            {"id": "other", "name_en": "Other", "name_ar": "أخرى", "icon_emoji": "➕", "icon_url": None, "sort_order": 1000, "allows_custom_text": True, "audience": "ventor", "topic_group": None, "is_active": True},
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


def _admin_by_email(db: Session, email: str) -> AdminUser | None:
    return db.query(AdminUser).filter(AdminUser.email == email).one_or_none()


def _role_id(db: Session, key: str) -> uuid.UUID:
    role = db.query(AdminRole).filter(AdminRole.key == key).one()
    return role.id


def seed_admin_cms(db: Session, mobile_ids: dict[str, uuid.UUID] | None = None) -> None:
    """Demo staff accounts + CMS config/content. Roles/permissions come from migration."""
    password_hash = _hash_password(DEMO_ADMIN_PASSWORD)
    now = datetime.now(timezone.utc)
    mobile_ids = mobile_ids or {}

    demo_admins = [
        {
            "email": "super@venting.app",
            "full_name": "Sara Super",
            "role_key": "super_admin",
            "status": AdminStatus.active,
        },
        {
            "email": "ops@venting.app",
            "full_name": "Omar Ops",
            "role_key": "ops",
            "status": AdminStatus.active,
        },
        {
            "email": "support@venting.app",
            "full_name": "Nora Support",
            "role_key": "support",
            "status": AdminStatus.active,
        },
        {
            "email": "finance@venting.app",
            "full_name": "Fadi Finance",
            "role_key": "finance",
            "status": AdminStatus.active,
        },
        {
            "email": "content@venting.app",
            "full_name": "Celine Content",
            "role_key": "content",
            "status": AdminStatus.active,
        },
        {
            "email": "analyst@venting.app",
            "full_name": "Ana Analyst",
            "role_key": "analyst",
            "status": AdminStatus.invited,
        },
    ]

    admin_ids: dict[str, uuid.UUID] = {}
    for row in demo_admins:
        admin = _admin_by_email(db, row["email"])
        if admin is None:
            admin = AdminUser(
                id=uuid.uuid4(),
                email=row["email"],
                password_hash=password_hash,
                full_name=row["full_name"],
                status=row["status"],
                mfa_enabled=False,
                last_login_at=now if row["status"] == AdminStatus.active else None,
            )
            db.add(admin)
            db.flush()
            db.add(
                AdminUserRole(
                    admin_user_id=admin.id,
                    role_id=_role_id(db, row["role_key"]),
                )
            )
            print(f"  + created admin {row['email']} ({row['role_key']})")
        else:
            print(f"  · admin exists {row['email']}")
        admin_ids[row["role_key"]] = admin.id

    super_id = admin_ids["super_admin"]
    ops_id = admin_ids["ops"]
    content_id = admin_ids["content"]

    # Feature flags
    for key, description, enabled, audience in [
        ("instant_match_enabled", "Allow ventors to start instant match", True, "ventor"),
        ("voice_change_enabled", "Voice anonymization in calls", True, "all"),
        ("tips_enabled", "Allow tips after sessions", True, "all"),
        ("invite_rewards_enabled", "Invite friends rewards tab", True, "ventor"),
        ("listener_discovery_v2", "New listener discovery ranking", False, "ventor"),
    ]:
        existing = db.get(AppFeatureFlag, key)
        if existing is None:
            db.add(
                AppFeatureFlag(
                    key=key,
                    description=description,
                    enabled=enabled,
                    rollout_percent=100 if enabled else 10,
                    audience=audience,
                    updated_by=content_id,
                )
            )
        else:
            existing.description = description
            existing.enabled = enabled
            existing.audience = audience
            existing.updated_by = content_id

    # App config KV
    config_rows = {
        "terms_url": "https://venting.app/terms",
        "privacy_url": "https://venting.app/privacy",
        "support_email": "support@venting.app",
        "min_payout_amount": 25.0,
        "voice_change_fee": 0.99,
        "earnings_tiers": {
            "starter": {"rate_per_minute": 0.25, "min_sessions": 0},
            "rising": {"rate_per_minute": 0.35, "min_sessions": 25},
            "trusted": {"rate_per_minute": 0.45, "min_sessions": 100},
            "expert": {"rate_per_minute": 0.55, "min_sessions": 250},
            "elite": {"rate_per_minute": 0.70, "min_sessions": 500},
        },
    }
    for key, value in config_rows.items():
        existing = db.get(AppConfigKv, key)
        if existing is None:
            db.add(AppConfigKv(key=key, value=value, updated_by=super_id))
        else:
            existing.value = value
            existing.updated_by = super_id

    # CMS pages
    pages = [
        {
            "slug": "help/cancel-session",
            "title": "How to cancel a session",
            "locale": "en",
            "body_markdown": (
                "## Cancel a session\n\n"
                "Open **Upcoming**, choose the session, then tap **Cancel**.\n\n"
                "Cancellations within 15 minutes of start may not be refunded."
            ),
            "status": CmsPageStatus.published,
        },
        {
            "slug": "help/cancel-session",
            "title": "كيفية إلغاء جلسة",
            "locale": "ar",
            "body_markdown": (
                "## إلغاء جلسة\n\n"
                "افتح **القادمة**، اختر الجلسة، ثم اضغط **إلغاء**."
            ),
            "status": CmsPageStatus.published,
        },
        {
            "slug": "legal/terms",
            "title": "Terms of Service",
            "locale": "en",
            "body_markdown": "# Terms of Service\n\nDemo terms for local CMS preview.",
            "status": CmsPageStatus.published,
        },
        {
            "slug": "legal/privacy",
            "title": "Privacy Policy (draft)",
            "locale": "en",
            "body_markdown": "# Privacy Policy\n\nDraft — not published yet.",
            "status": CmsPageStatus.draft,
        },
    ]
    for page in pages:
        existing = (
            db.query(CmsPage)
            .filter(CmsPage.slug == page["slug"], CmsPage.locale == page["locale"])
            .one_or_none()
        )
        if existing is None:
            db.add(
                CmsPage(
                    id=uuid.uuid4(),
                    slug=page["slug"],
                    title=page["title"],
                    locale=page["locale"],
                    body_markdown=page["body_markdown"],
                    status=page["status"],
                    published_at=now if page["status"] == CmsPageStatus.published else None,
                    updated_by=content_id,
                )
            )
        else:
            existing.title = page["title"]
            existing.body_markdown = page["body_markdown"]
            existing.status = page["status"]
            existing.updated_by = content_id

    # Banners — skip duplicates by title+placement
    banners = [
        {
            "title": "Welcome to Venting",
            "body": "Book your first calm conversation today.",
            "cta_label": "Find a listener",
            "cta_url": "venting://listeners",
            "placement": BannerPlacement.ventor_home,
            "audience": "ventor",
        },
        {
            "title": "Complete your training",
            "body": "Finish modules to go live and earn.",
            "cta_label": "Open training",
            "cta_url": "venting://training",
            "placement": BannerPlacement.listener_home,
            "audience": "listener",
        },
        {
            "title": "Limited promo",
            "body": "Use code WELCOME10 at checkout.",
            "cta_label": "Apply promo",
            "cta_url": "venting://checkout",
            "placement": BannerPlacement.checkout,
            "audience": "ventor",
        },
    ]
    for banner in banners:
        existing = (
            db.query(CmsBanner)
            .filter(
                CmsBanner.title == banner["title"],
                CmsBanner.placement == banner["placement"],
            )
            .one_or_none()
        )
        if existing is None:
            db.add(
                CmsBanner(
                    id=uuid.uuid4(),
                    title=banner["title"],
                    body=banner["body"],
                    cta_label=banner["cta_label"],
                    cta_url=banner["cta_url"],
                    placement=banner["placement"],
                    audience=banner["audience"],
                    starts_at=now - timedelta(days=1),
                    ends_at=now + timedelta(days=30),
                    is_active=True,
                )
            )

    # Notes + audit (once)
    note_marker = "DEMO_NOTE_LISTENER"
    if (
        db.query(AdminNote)
        .filter(AdminNote.body.contains(note_marker))
        .one_or_none()
        is None
    ):
        listener_id = mobile_ids.get("listener")
        entity_id = listener_id or uuid.UUID("00000000-0000-0000-0000-000000000001")
        db.add(
            AdminNote(
                id=uuid.uuid4(),
                admin_user_id=ops_id,
                entity_type="user",
                entity_id=entity_id,
                body=f"[{note_marker}] Strong listener — approved after ID review. Keep an eye on first-week ratings.",
            )
        )
        db.add(
            AdminAuditLog(
                id=uuid.uuid4(),
                admin_user_id=ops_id,
                action="listener.approve",
                entity_type="listener",
                entity_id=str(entity_id),
                before={"profile_status": "under_review"},
                after={"profile_status": "approved", "is_verified": True},
                ip="127.0.0.1",
                user_agent="seed-demo/1.0",
            )
        )
        db.add(
            AdminAuditLog(
                id=uuid.uuid4(),
                admin_user_id=content_id,
                action="cms.page.publish",
                entity_type="cms_page",
                entity_id="help/cancel-session",
                before={"status": "draft"},
                after={"status": "published"},
                ip="127.0.0.1",
                user_agent="seed-demo/1.0",
            )
        )

    # Link review metadata on demo listener if present
    listener_id = mobile_ids.get("listener")
    if listener_id is not None:
        profile = db.get(ListenerProfile, listener_id)
        if profile is not None and profile.reviewed_by_admin_id is None:
            profile.reviewed_by_admin_id = ops_id
            profile.reviewed_at = now
            profile.rejection_reason = None

    # Sample moderation warn on listener2 if exists
    listener2_id = mobile_ids.get("listener2")
    mod_marker = "DEMO_MOD_WARN"
    if listener2_id is not None and (
        db.query(ModerationAction)
        .filter(ModerationAction.reason.contains(mod_marker))
        .one_or_none()
        is None
    ):
        db.add(
            ModerationAction(
                id=uuid.uuid4(),
                user_id=listener2_id,
                admin_user_id=ops_id,
                action=ModerationActionType.warn,
                reason=f"[{mod_marker}] Late start on two sessions — verbal warning only.",
                starts_at=now,
                ends_at=None,
            )
        )

    db.flush()


def main() -> None:
    get_settings.cache_clear()
    settings = get_settings()
    print(f"Seeding {settings.database_name} @ {settings.database_hostname}...")

    db = SessionLocal()
    try:
        print("Catalogs:")
        seed_catalogs(db)
        print("Demo users:")
        ids = seed_demo_users(db)
        print("Admin CMS:")
        seed_admin_cms(db, ids)
        db.commit()
        print("\nDone.")
        print("Mobile logins (password for all):", DEMO_PASSWORD)
        print("  ventor@venting.app")
        print("  listener@venting.app")
        print("  listener2@venting.app")
        print("Admin portal logins (password for all):", DEMO_ADMIN_PASSWORD)
        print("  super@venting.app   (super_admin)")
        print("  ops@venting.app     (ops)")
        print("  support@venting.app (support)")
        print("  finance@venting.app (finance)")
        print("  content@venting.app (content)")
        print("  analyst@venting.app (analyst, invited)")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
