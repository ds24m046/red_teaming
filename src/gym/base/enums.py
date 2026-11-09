from enum import StrEnum



class Profile(StrEnum):
    WEAK = "weak"
    HARDENED = "hardened"


class DiscussionStyle(StrEnum):
    ROUND_TABLE = "ROUND_TABLE"
    PEER_REVIEW = "PEER_REVIEW"
    DEBATE = "DEBATE"
    TASK_FORCE = "TASK_FORCE"


class ConversationState(StrEnum):
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    AWAITING_HUMAN = "AWAITING_HUMAN"
    ENDED = "ENDED"
    ERROR = "ERROR"