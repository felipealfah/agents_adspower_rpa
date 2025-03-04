import time
import logging
from enum import Enum
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.webdriver import WebDriver

from .account_setup import AccountSetup
from .phone_verify import PhoneVerification
from .terms_handler import TermsHandler
from .account_verify import AccountVerify
from .exceptions import GmailCreationError
from .config import timeouts, account_config, sms_config, log_config

logger = logging.getLogger(__name__)

class GmailCreationState(Enum):
    """Estados possíveis durante a criação da conta."""
    INITIAL = "initial"
    ACCOUNT_SETUP = "account_setup"
    PHONE_VERIFICATION = "phone_verification"
    TERMS_ACCEPTANCE = "terms_acceptance"
    ACCOUNT_VERIFICATION = "account_verification"
    COMPLETED = "completed"
    FAILED = "failed"

class GmailCreator:
    """Classe principal que gerencia o fluxo de criação da conta Gmail."""

    def __init__(self, driver: WebDriver, credentials, sms_api, profile_name="default_profile"):
        self.driver = driver
        self.credentials = credentials
        self.sms_api = sms_api
        self.wait = WebDriverWait(driver, timeouts.DEFAULT_WAIT)
        self.phone_number = None  # Inicialmente como None para evitar valores errados
        self.profile_name = profile_name if profile_name else "default_profile"  # Garantir que nunca seja None ou vazio
        
        # Configuração geral
        self.config = {
            "timeouts": timeouts,
            "account_config": account_config,
            "sms_config": sms_config,
            "log_config": log_config
        }

        self.state = GmailCreationState.INITIAL

    def create_account(self, phone_params=None):
        """
        Executa todo o fluxo de criação da conta Gmail.
        
        Args:
            phone_params (dict, optional): Parâmetros para reutilização de números
                Formato esperado: {
                    'reuse_number': True,
                    'phone_number': '12345678901',
                    'activation_id': 'activation123',
                    'country_code': '1'
                }
        
        Returns:
            tuple: (sucesso, dados_da_conta)
        """
        try:
            logger.info("🚀 Iniciando criação da conta Gmail...")

            # Passo 1: Configuração inicial da conta
            self.state = GmailCreationState.ACCOUNT_SETUP
            account_setup = AccountSetup(self.driver, self.credentials)
            if not account_setup.start_setup():
                raise GmailCreationError("❌ Falha na configuração inicial da conta.")

            # Passo 2: Verificação de telefone
            self.state = GmailCreationState.PHONE_VERIFICATION
            phone_verify = PhoneVerification(self.driver, self.sms_api)

            # Se temos parâmetros de telefone para reutilização
            if phone_params and isinstance(phone_params, dict) and phone_params.get('reuse_number'):
                logger.info(f"♻️ Configurando reutilização de número: {phone_params.get('phone_number')}")
                phone_verify.reuse_number = True
                phone_verify.predefined_number = phone_params.get('phone_number')
                phone_verify.predefined_activation_id = phone_params.get('activation_id')
                phone_verify.predefined_country_code = phone_params.get('country_code')

            if not phone_verify.handle_verification():
                raise GmailCreationError("❌ Falha na verificação de telefone.")

            # 🔹 Captura e armazena o número de telefone corretamente
            if phone_verify.current_activation and phone_verify.current_activation.phone_number:
                self.phone_number = phone_verify.current_activation.phone_number
                logger.info(f"✅ Número de telefone capturado: {self.phone_number}")
            else:
                logger.warning("⚠️ Nenhum número de telefone foi capturado!")
                self.phone_number = "unknown"  # Define um valor padrão caso o número não seja obtido

            # Passo 3: Aceitação dos Termos
            self.state = GmailCreationState.TERMS_ACCEPTANCE
            terms_handler = TermsHandler(self.driver)
            if not terms_handler.handle_terms_acceptance():
                raise GmailCreationError("❌ Falha na aceitação dos termos.")

            # Passo 4: Verificação final da conta
            self.state = GmailCreationState.ACCOUNT_VERIFICATION
            account_verify = AccountVerify(
                self.driver,
                self.credentials,
                profile_name=self.profile_name,  # Nome do perfil do AdsPower
                phone_number=self.phone_number   # Número salvo anteriormente
            )

            if not account_verify.verify_account():
                raise GmailCreationError("❌ Falha na verificação final da conta.")

            # Se tudo deu certo:
            self.state = GmailCreationState.COMPLETED

            # 🔹 Retornar os dados corretos sem duplicação
            account_data = {
                "email": self.credentials["username"] + "@gmail.com",
                "password": self.credentials["password"],
                "phone": self.phone_number,
                "profile": self.profile_name
            }
            
            # Adicionar o ID de ativação se disponível (útil para reutilização)
            if hasattr(phone_verify, 'current_activation') and phone_verify.current_activation:
                account_data["activation_id"] = phone_verify.current_activation.activation_id
                if hasattr(phone_verify.current_activation, 'country_code'):
                    account_data["country_code"] = phone_verify.current_activation.country_code

            logger.info(f"✅ Conta criada com sucesso! Retornando os dados: {account_data}")
            return True, account_data  # Retorna SUCESSO corretamente

        except GmailCreationError as e:
            logger.error(f"🚨 Erro durante o processo: {str(e)}")
            return False, None  # Retorna erro APENAS se uma exceção for levantada

        except Exception as e:
            logger.error(f"❌ Erro inesperado: {str(e)}")
            return False, None  # Retorna erro para exceções desconhecidas