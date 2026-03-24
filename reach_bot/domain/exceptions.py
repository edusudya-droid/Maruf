from typing import Any


class AppError(Exception):
    """Base application error."""

    def __init__(self, code: str, message: str, details: Any = None, retryable: bool = False):
        self.code = code
        self.message = message
        self.details = details
        self.retryable = retryable
        super().__init__(message)

    def to_dict(self) -> dict:
        return {
            "success": False,
            "data": None,
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
                "retryable": self.retryable,
            },
            "meta": None,
        }


# Auth errors
class AuthDeniedError(AppError):
    def __init__(self, message: str = "Kirish rad etildi"):
        super().__init__("AUTH_DENIED", message)


class UserNotFoundError(AppError):
    def __init__(self, message: str = "Foydalanuvchi topilmadi"):
        super().__init__("USER_NOT_FOUND", message)


class UserBlockedError(AppError):
    def __init__(self, message: str = "Foydalanuvchi bloklangan"):
        super().__init__("USER_BLOCKED", message)


class PermissionDeniedError(AppError):
    def __init__(self, message: str = "Ruxsat yo'q"):
        super().__init__("PERMISSION_DENIED", message)


class InvalidRoleError(AppError):
    def __init__(self, message: str = "Noto'g'ri rol"):
        super().__init__("INVALID_ROLE", message)


class UserAlreadyExistsError(AppError):
    def __init__(self, message: str = "Foydalanuvchi allaqachon mavjud"):
        super().__init__("USER_ALREADY_EXISTS", message)


# Channel errors
class OfficialChannelNotConfiguredError(AppError):
    def __init__(self, message: str = "Rasmiy kanal sozlanmagan"):
        super().__init__("OFFICIAL_CHANNEL_NOT_CONFIGURED", message)


# Post errors
class PostsFetchFailedError(AppError):
    def __init__(self, message: str = "Postlarni olishda xato"):
        super().__init__("POSTS_FETCH_FAILED", message, retryable=True)


class InvalidPostUrlError(AppError):
    def __init__(self, message: str = "Noto'g'ri post URL"):
        super().__init__("INVALID_POST_URL", message)


class PostNotFoundError(AppError):
    def __init__(self, message: str = "Post topilmadi"):
        super().__init__("POST_NOT_FOUND", message)


class PostNotSelectedError(AppError):
    def __init__(self, message: str = "Post tanlanmagan"):
        super().__init__("POST_NOT_SELECTED", message)


# Analysis errors
class AnalysisAlreadyRunningError(AppError):
    def __init__(self, message: str = "Analiz allaqachon bajarilmoqda"):
        super().__init__("ANALYSIS_ALREADY_RUNNING", message)


class AnalysisNotFoundError(AppError):
    def __init__(self, message: str = "Analiz topilmadi"):
        super().__init__("ANALYSIS_NOT_FOUND", message)


class DailyLimitReachedError(AppError):
    def __init__(self, message: str = "Kunlik limit to'ldi"):
        super().__init__("DAILY_LIMIT_REACHED", message)


class QueueError(AppError):
    def __init__(self, message: str = "Navbat xatosi", retryable: bool = True):
        super().__init__("QUEUE_ERROR", message, retryable=retryable)


# Text processing errors
class EmptyTextError(AppError):
    def __init__(self, message: str = "Matn bo'sh"):
        super().__init__("EMPTY_TEXT", message)


class NormalizationError(AppError):
    def __init__(self, message: str = "Normalizatsiya xatosi"):
        super().__init__("NORMALIZATION_ERROR", message)


class EmptySourceTextError(AppError):
    def __init__(self, message: str = "Manba matni bo'sh"):
        super().__init__("EMPTY_SOURCE_TEXT", message)


class EmptyCandidateTextError(AppError):
    def __init__(self, message: str = "Nomzod matni bo'sh"):
        super().__init__("EMPTY_CANDIDATE_TEXT", message)


class TextCompareError(AppError):
    def __init__(self, message: str = "Matn taqqoslash xatosi"):
        super().__init__("TEXT_COMPARE_ERROR", message)


# Availability errors
class SourceUnavailableError(AppError):
    def __init__(self, message: str = "Manba mavjud emas", retryable: bool = True):
        super().__init__("SOURCE_UNAVAILABLE", message, retryable=retryable)


class PostDeletedError(AppError):
    def __init__(self, message: str = "Post o'chirilgan"):
        super().__init__("POST_DELETED", message)


class NoViewsDataError(AppError):
    def __init__(self, message: str = "Ko'rishlar ma'lumoti yo'q"):
        super().__init__("NO_VIEWS_DATA", message)


class LowSimilarityError(AppError):
    def __init__(self, message: str = "O'xshashlik past"):
        super().__init__("LOW_SIMILARITY", message)


class DuplicateDetectedError(AppError):
    def __init__(self, message: str = "Dublikat aniqlandi"):
        super().__init__("DUPLICATE_DETECTED", message)


class DetectedPostSaveError(AppError):
    def __init__(self, message: str = "Topilgan postni saqlashda xato"):
        super().__init__("DETECTED_POST_SAVE_ERROR", message)


# Validation errors
class InvalidStatusError(AppError):
    def __init__(self, message: str = "Noto'g'ri status"):
        super().__init__("INVALID_STATUS", message)


class InvalidConfirmationTypeError(AppError):
    def __init__(self, message: str = "Noto'g'ri tasdiqlash turi"):
        super().__init__("INVALID_CONFIRMATION_TYPE", message)


# Settings errors
class SettingNotFoundError(AppError):
    def __init__(self, message: str = "Sozlama topilmadi"):
        super().__init__("SETTING_NOT_FOUND", message)


class InvalidSettingValueError(AppError):
    def __init__(self, message: str = "Noto'g'ri sozlama qiymati"):
        super().__init__("INVALID_SETTING_VALUE", message)


# Infrastructure errors
class DbError(AppError):
    def __init__(self, message: str = "Ma'lumotlar bazasi xatosi", retryable: bool = True):
        super().__init__("DB_ERROR", message, retryable=retryable)


class UnexpectedError(AppError):
    def __init__(self, message: str = "Kutilmagan xato"):
        super().__init__("UNEXPECTED_ERROR", message)


def ok(data: Any = None, meta: Any = None) -> dict:
    """Build a successful response."""
    return {"success": True, "data": data, "error": None, "meta": meta}


def err(exc: AppError) -> dict:
    """Build an error response from an AppError."""
    return exc.to_dict()
