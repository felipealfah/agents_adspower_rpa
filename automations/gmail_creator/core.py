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
        # Garantir que nunca seja None ou vazio
        self.profile_name = profile_name if profile_name else "default_profile"

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
                raise GmailCreationError(
                    "❌ Falha na configuração inicial da conta.")

            # Passo 2: Verificação de telefone
            self.state = GmailCreationState.PHONE_VERIFICATION
            phone_verify = PhoneVerification(self.driver, self.sms_api)

            # Inicializar phone_manager se necessário
            if hasattr(self, 'phone_manager') and self.phone_manager:
                phone_verify.phone_manager = self.phone_manager

            # Variáveis para controle de fluxo
            phone_verification_success = False
            phone_data = None

            # Verificar se a tela de verificação de telefone está presente
            if phone_verify._check_phone_screen():
                logger.info("📞 Tela de verificação de telefone detectada.")
                # Se temos parâmetros de telefone para reutilização
                if phone_params and isinstance(phone_params, dict) and phone_params.get('reuse_number'):
                    logger.info(
                        f"♻️ Configurando reutilização de número: {phone_params.get('phone_number')}")
                    phone_verify.reuse_number = True
                    phone_verify.predefined_number = phone_params.get(
                        'phone_number')
                    phone_verify.predefined_activation_id = phone_params.get(
                        'activation_id')
                    phone_verify.predefined_country_code = phone_params.get(
                        'country_code')

                # Esta chamada inclui todo o processo de verificação por SMS
                phone_verification_success = phone_verify.handle_verification()

                if not phone_verification_success:
                    raise GmailCreationError(
                        "❌ Falha na verificação de telefone.")

                # Captura os dados do telefone verificado
                phone_data = phone_verify.get_current_phone_data()
                if not phone_data:
                    logger.error(
                        "❌ Falha ao obter dados do telefone após verificação")
                    raise GmailCreationError(
                        "Dados do telefone não disponíveis após verificação")
            else:
                logger.info(
                    "📞 Tela de verificação de telefone não detectada, pulando para aceitação dos termos.")
                # Se não houver verificação de telefone, definimos valores padrão
                phone_data = {
                    'phone_number': phone_params.get('phone_number') if phone_params else None,
                    'country_code': phone_params.get('country_code') if phone_params else None,
                    'activation_id': phone_params.get('activation_id') if phone_params else None,
                    'country_name': "unknown"
                }
                phone_verification_success = True

            # Extrair dados do telefone
            phone_number = phone_data.get('phone_number')
            country_code = phone_data.get('country_code')
            activation_id = phone_data.get('activation_id')
            country_name = phone_data.get('country_name')

            # **Novo Passo: Pular a tela de recuperação de email**
            terms_handler = TermsHandler(self.driver)
            if not terms_handler._skip_recovery_email():
                logger.warning(
                    "⚠️ Não foi possível pular a tela de recuperação de email, mas continuando...")

            # Passo 3: Aceitação dos Termos
            self.state = GmailCreationState.TERMS_ACCEPTANCE
            if not terms_handler.handle_terms_acceptance():
                raise GmailCreationError("❌ Falha na aceitação dos termos.")

            # Passo 4: Verificação final da conta
            self.state = GmailCreationState.ACCOUNT_VERIFICATION
            account_verify = AccountVerify(
                self.driver,
                self.credentials,
                profile_name=self.profile_name,
                phone_number=phone_number
            )

            if not account_verify.verify_account():
                raise GmailCreationError(
                    "❌ Falha na verificação final da conta.")

            # Se tudo deu certo:
            self.state = GmailCreationState.COMPLETED

            # 🔹 Retornar os dados completos da conta
            account_data = {
                "first_name": self.credentials["first_name"],
                "last_name": self.credentials["last_name"],
                "email": self.credentials["username"] + "@gmail.com",
                "password": self.credentials["password"],
                "phone": phone_number,
                "country_code": country_code,
                "country_name": country_name,
                "activation_id": activation_id,
                "profile": self.profile_name
            }

            logger.info(
                f"✅ Conta criada com sucesso! Retornando os dados: {account_data}")
            return True, account_data

        except GmailCreationError as e:
            logger.error(f"🚨 Erro durante o processo: {str(e)}")
            return False, None

        except Exception as e:
            logger.error(f"❌ Erro inesperado: {str(e)}")
            return False, None
