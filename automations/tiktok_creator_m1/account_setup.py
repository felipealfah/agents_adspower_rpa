import json
import logging
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .exceptions import AccountSetupError
from .config.locators import SignupLocators  # Importando os locators

logger = logging.getLogger(__name__)


class AccountSetup:
    """Classe responsável pela configuração inicial da conta TikTok."""

    def __init__(self, driver, credentials_file):
        self.driver = driver
        self.credentials_file = credentials_file
        self.credentials = self.load_credentials()

    def load_credentials(self):
        """Carrega as credenciais do arquivo JSON."""
        try:
            with open(self.credentials_file, "r") as file:
                return json.load(file)
        except Exception as e:
            logger.error(f"Erro ao carregar credenciais: {str(e)}")
            raise AccountSetupError("Falha ao carregar credenciais.")

    def start_setup(self):
        """Inicia o processo de configuração da conta TikTok."""
        try:
            # 1. Acessar o link de cadastro do TikTok
            self.driver.get(SignupLocators.TIKTOK_SIGNUP_URL)
            logger.info("Acessando a página de cadastro do TikTok.")

            # 2. Clicar no botão de cadastro
            self.wait_for_element_and_click(
                SignupLocators.INITIAL_SIGNUP_BUTTON)

            # 3. Esperar carregar a página
            time.sleep(3)  # Ajuste o tempo conforme necessário

            # 4. Clicar no link para continuar com o cadastro
            self.wait_for_element_and_click(SignupLocators.CONTINUE_LINK)

            # 5. Esperar carregar a página
            time.sleep(3)  # Ajuste o tempo conforme necessário

            # 6. Preencher as informações de aniversário, email e senha
            self.fill_account_info()

            logger.info("Configuração da conta concluída com sucesso.")
            return True

        except Exception as e:
            logger.error(f"Erro durante a configuração da conta: {str(e)}")
            raise AccountSetupError("Falha na configuração da conta.")

    def wait_for_element_and_click(self, xpath):
        """Aguarda um elemento ser clicável e clica nele."""
        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            element.click()
            logger.info(f"Clicou no elemento com XPath: {xpath}")
        except (TimeoutException, NoSuchElementException) as e:
            logger.error(f"Erro ao clicar no elemento: {str(e)}")
            raise AccountSetupError("Elemento não encontrado ou não clicável.")

    def fill_account_info(self):
        """Preenche as informações da conta usando as credenciais carregadas."""
        if not self.credentials:
            raise AccountSetupError(
                "Nenhuma credencial disponível para preencher.")

        # Supondo que estamos usando a primeira conta do arquivo
        account = self.credentials[0]

        # Preencher informações de aniversário
        # Aqui você deve adicionar a lógica para preencher a data de nascimento
        # Exemplo: self.driver.find_element(By.XPATH, SignupLocators.BIRTHDAY_MONTH).send_keys("01")

        # Preencher email
        email_input = self.driver.find_element(
            By.XPATH, SignupLocators.USERNAME_INPUT)
        email_input.send_keys(account["email"])
        logger.info(f"Preenchido email: {account['email']}")

        # Preencher senha
        password_input = self.driver.find_element(
            By.XPATH, SignupLocators.PASSWORD_INPUT)
        password_input.send_keys(account["password"])
        logger.info("Preenchida a senha.")

        # Aqui você pode adicionar a lógica para clicar no botão de finalizar cadastro, se necessário
