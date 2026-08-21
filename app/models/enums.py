"""PostgreSQL enums from docs/database-schema.md § Shared enums."""

import enum


class UserRole(str, enum.Enum):
    ventor = "ventor"
    listener = "listener"


class Gender(str, enum.Enum):
    male = "male"
    female = "female"
    prefer_not_to_say = "prefer_not_to_say"


class ProfileStatus(str, enum.Enum):
    incomplete = "incomplete"
    under_review = "under_review"
    approved = "approved"
    rejected = "rejected"


class SetupStepStatus(str, enum.Enum):
    done = "done"
    in_progress = "in_progress"
    locked = "locked"


class DayOfWeek(str, enum.Enum):
    mon = "mon"
    tue = "tue"
    wed = "wed"
    thu = "thu"
    fri = "fri"
    sat = "sat"
    sun = "sun"


class SessionTimeMode(str, enum.Enum):
    instant = "instant"
    nearest = "nearest"
    scheduled = "scheduled"


class CallMode(str, enum.Enum):
    voice = "voice"
    video = "video"


class SessionRequestStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"
    expired = "expired"
    cancelled = "cancelled"


class SessionStatus(str, enum.Enum):
    upcoming = "upcoming"
    live = "live"
    completed = "completed"
    cancelled = "cancelled"
    missed = "missed"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    refunded = "refunded"
    failed = "failed"


class ReportReason(str, enum.Enum):
    inappropriate_behavior = "inappropriate_behavior"
    harassment = "harassment"
    hate_speech = "hate_speech"
    safety_concern = "safety_concern"
    not_listening = "not_listening"
    technical_issue = "technical_issue"
    other = "other"


class ReportedRole(str, enum.Enum):
    ventor = "ventor"
    listener = "listener"


class LedgerEntryType(str, enum.Enum):
    session_earning = "session_earning"
    tip = "tip"
    penalty = "penalty"
    payout = "payout"
    payout_reversal = "payout_reversal"
    adjustment = "adjustment"


class PayoutStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class PayoutMethodType(str, enum.Enum):
    bank = "bank"
    paypal = "paypal"


class RewardOfferKind(str, enum.Enum):
    percent_off = "percent_off"
    free_minutes = "free_minutes"
    priority_match = "priority_match"


class EarningsTier(str, enum.Enum):
    starter = "starter"
    rising = "rising"
    trusted = "trusted"
    expert = "expert"
    elite = "elite"


class InviteStatus(str, enum.Enum):
    pending = "pending"
    joined = "joined"
    first_session = "first_session"
    booked_call = "booked_call"


class NotificationType(str, enum.Enum):
    session_request = "session_request"
    session_reminder = "session_reminder"
    review = "review"
    payout = "payout"
    system = "system"
    rewards = "rewards"


class TrainingStatus(str, enum.Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"


class MoodKind(str, enum.Enum):
    great = "great"
    okay = "okay"
    anxious = "anxious"
    sad = "sad"
    angry = "angry"


# --- Admin portal / CMS (docs/admin-portal-cms.md) ---


class AdminStatus(str, enum.Enum):
    active = "active"
    invited = "invited"
    disabled = "disabled"


class ModerationActionType(str, enum.Enum):
    warn = "warn"
    suspend = "suspend"
    unsuspend = "unsuspend"
    ban = "ban"
    unban = "unban"
    force_logout = "force_logout"


class ReviewDecision(str, enum.Enum):
    approved = "approved"
    rejected = "rejected"
    needs_more_info = "needs_more_info"


class CmsPageStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


class BannerPlacement(str, enum.Enum):
    ventor_home = "ventor_home"
    listener_home = "listener_home"
    checkout = "checkout"
    global_ = "global"
