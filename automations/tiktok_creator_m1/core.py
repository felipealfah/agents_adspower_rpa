from enum import Enum
import logging
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.webdriver import WebDriver
import json

from .account_setup import AccountSetup
#from .phone_verify import PhoneVerification
from .exceptions import TikTokCreationError
from .config.config import timeouts, account_config

logger = logging.getLogger(__name__)


class TikTokCreationState(Enum):
    """Estados possíveis durante o processo de criação da conta."""
    INITIAL = "initial"
    ACCOUNT_SETUP = "account_setup"
    PHONE_VERIFICATION = "phone_verification"
    COMPLETED = "completed"
    ERROR = "error"


class TikTokCreator:
    """Classe principal que gerencia o fluxo de criação da conta TikTok."""

    def __init__(self, driver: WebDriver, credentials_file: str, sms_api, profile_name="default_profile"):
        self.driver = driver
        self.credentials_file = credentials_file
        self.sms_api = sms_api
        self.wait = WebDriverWait(driver, timeouts.DEFAULT_WAIT)
        self.profile_name = profile_name
        self.state = TikTokCreationState.INITIAL

    def load_credentials(self):
        """Carrega as credenciais do arquivo JSON."""
        try:
            with open(self.credentials_file, "r") as file:
                return json.load(file)
        except Exception as e:
            logger.error(f"Erro ao carregar credenciais: {str(e)}")
            raise TikTokCreationError("Falha ao carregar credenciais.")

    def create_account(self) -> tuple[bool, dict | None]:
        """
        Executa o fluxo completo de criação da conta TikTok.

        Returns:
            tuple[bool, dict | None]: (sucesso, dados_da_conta)
        """
        try:
            logger.info("🚀 Iniciando criação da conta TikTok...")

            # Carregar credenciais
            self.credentials = self.load_credentials()

            # Passo 1: Configuração inicial da conta
            self.state = TikTokCreationState.ACCOUNT_SETUP
            account_setup = AccountSetup(self.driver, self.credentials_file)
            if not account_setup.start_setup():
                raise TikTokCreationError(
                    "❌ Falha na configuração inicial da conta.")

            # Passo 2: Verificação de telefone
            self.state = TikTokCreationState.PHONE_VERIFICATION
            phone_verify = PhoneVerification(self.driver, self.sms_api)

            phone_data = phone_verify.handle_verification()
            if not phone_data:
                raise TikTokCreationError(
                    "❌ Falha na verificação do telefone.")

            # Se chegou aqui, a conta foi criada com sucesso
            self.state = TikTokCreationState.COMPLETED

            # Retornar os dados da conta
            account_data = {
                # Usando o email como username
                "username": self.credentials[0]["email"],
                "password": self.credentials[0]["password"],
                "phone": phone_data["phone_number"],
                "country_code": phone_data["country_code"],
                "profile": self.profile_name
            }

            logger.info(
                f"✅ Conta criada com sucesso! Retornando os dados: {account_data}")
            return True, account_data

        except TikTokCreationError as e:
            logger.error(f"🚨 Erro durante o processo: {str(e)}")
            return False, None

        except Exception as e:
            logger.error(f"❌ Erro inesperado: {str(e)}")
            return False, None
