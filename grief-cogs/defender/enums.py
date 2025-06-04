import enum


class EmergencyMode:
    def __init__(self, *, manual):
        self.is_manual = (
            manual  # Manual mode won't automatically be disabled by staff activity
        )


class Rank(enum.IntEnum):
    """Ranks of trust"""

    Rank1 = 1  # Trusted user. Has at least one of the roles defined in "trusted_roles" or is staff/admin
    Rank2 = 2  # User that satisfies all the requirements below
    Rank3 = 3  # User that joined <X days ago
    Rank4 = 4  # User that satisfies Rank3's requirement and also has less than X messages in the server


class Action(enum.Enum):
    NoAction = "none"
    Ban = "ban"
    Kick = "kick"
    Softban = "softban"
    Punish = "punish"


class QAAction(enum.Enum):
    BanDeleteOneDay = "ban"


class QAInteractions(enum.Enum):
    Ban = "ban"
    Kick = "kick"
    Softban = "softban"
    Punish = "punish"
    BanAndDelete24 = "b24"


class AutoModules(enum.Enum):
    RaiderDetection = "Raider detection"
    InviteFilter = "Invite filter"
    JoinMonitor = "Join monitor"
    Warden = "Warden"


class ManualModules(enum.Enum):
    Alert = "Alert"
    Vaporize = "Vaporize"
    Silence = "Silence"
    Voteout = "Voteout"


class EmergencyModules(enum.Enum):
    Voteout = "voteout"
    Vaporize = "vaporize"
    Silence = "silence"


# https://developers.perspectiveapi.com/s/about-the-api-attributes-and-languages


class PerspectiveAttributes(enum.Enum):
    Toxicity = "TOXICITY"
    SevereToxicity = "SEVERE_TOXICITY"
    IdentityAttack = "IDENTITY_ATTACK"
    Insult = "INSULT"
    Profanity = "PROFANITY"
    Threat = "THREAT"
    SexuallyExplicit = "SEXUALLY_EXPLICIT"
    Flirtation = "FLIRTATION"
