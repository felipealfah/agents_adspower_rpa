from dataclasses import dataclass
from typing import Dict, List


@dataclass
class TimeoutConfig:
    """Configurações de timeout para diferentes operações."""
    DEFAULT_WAIT: int = 20
    ELEMENT_WAIT: int = 10
    PAGE_LOAD_WAIT: int = 30
    SMS_WAIT: int = 120
    RETRY_INTERVAL: int = 10


@dataclass
class AccountConfig:
    """Configurações relacionadas à conta."""
    MAX_USERNAME_ATTEMPTS: int = 5
    TIKTOK_SIGNUP_URL: str = "https://www.tiktok.com/signup"

    # Configurações específicas do TikTok
    MIN_AGE: int = 13
    MAX_AGE: int = 80
    USERNAME_MIN_LENGTH: int = 4
    USERNAME_MAX_LENGTH: int = 24


@dataclass
class SMSConfig:
    """Configurações relacionadas à verificação SMS."""
    MAX_SMS_ATTEMPTS: int = 3
    MAX_RETRY_ATTEMPTS: int = 12
    SERVICE_NAME: str = "tk"  # Código do serviço TikTok
    RETRY_INTERVAL: int = 10


# Instâncias das configurações
timeouts = TimeoutConfig()
account_config = AccountConfig()
sms_config = SMSConfig()
