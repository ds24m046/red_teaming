from enum import StrEnum


class ConversationState(StrEnum):
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    AWAITING_HUMAN = "AWAITING_HUMAN"
    ENDED = "ENDED"
    ERROR = "ERROR"