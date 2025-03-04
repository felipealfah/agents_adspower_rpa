from enum import Enum
from dataclasses import dataclass
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from .exceptions import (
    TermsAcceptanceError,
    ElementInteractionError,
    NavigationError
)
from .config import timeouts
from .locators import terms_locators

logger = logging.getLogger(__name__)

class TermsState(Enum):
    """Estados possíveis do processo de aceitação dos termos."""
    INITIAL = "initial"
    TERMS_PAGE = "terms_page"
    TERMS_ACCEPTED = "terms_accepted"
    CONFIRMATION_HANDLED = "confirmation_handled"
    RECOVERY_SKIPPED = "recovery_skipped"
    REVIEW_COMPLETED = "review_completed"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class TermsInfo:
    """Armazena informações sobre o processo de aceitação dos termos."""
    state: TermsState = TermsState.INITIAL
    terms_accepted: bool = False
    confirmation_handled: bool = False
    recovery_skipped: bool = False
    review_completed: bool = False
    attempts: int = 0
    max_attempts: int = 3

class TermsHandler:
    """
    Gerencia o processo de aceitação de termos e revisão de conta.
    Responsável por aceitar os termos de uso e pular etapas opcionais.
    """
    
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, timeouts.DEFAULT_WAIT)
        self.terms_info = TermsInfo()
        self.max_retries = 3
        self.retry_delay = 2

    def handle_terms_acceptance(self) -> bool:
        """Processo principal de aceitação dos termos."""
        try:
            logger.info("📄 Iniciando processo após verificação de telefone...")

            # Nova sequência correta
            acceptance_steps = [
                (self._skip_recovery_email, TermsState.RECOVERY_SKIPPED),     # 1. Pular email de recuperação
                (self._handle_review_page, TermsState.REVIEW_COMPLETED),      # 2. Confirmar telefone na tela de revisão
                (self._accept_terms, TermsState.TERMS_PAGE),                  # 3. Aceitar os termos
                (self._handle_confirmation_modal, TermsState.TERMS_ACCEPTED)  # 4. Confirmar no modal
            ]

            for step_func, new_state in acceptance_steps:
                self.terms_info.state = new_state

                if not self._execute_with_retry(step_func):
                    self.terms_info.state = TermsState.FAILED
                    return False

            self.terms_info.state = TermsState.COMPLETED
            return True

        except Exception as e:
            logger.error(f"Erro durante processo pós-verificação: {str(e)}")
            self.terms_info.state = TermsState.FAILED
            raise TermsAcceptanceError(f"Falha no processo pós-verificação: {str(e)}")

    def _element_exists(self, xpath, timeout=3):
        """Verifica se um elemento existe na página."""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            return True
        except TimeoutException:
            return False

    def _execute_with_retry(self, func) -> bool:
        """Executa uma função com sistema de retry."""
        for attempt in range(self.max_retries):
            try:
                func()
                return True
            except Exception as e:
                logger.warning(f"⚠️ Tentativa {attempt + 1} falhou: {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                return False

    def _accept_terms(self):
        """Aceita os termos de uso com suporte a múltiplos formatos de tela."""
        try:
            logger.info("📌 Localizando botão 'Aceitar' nos termos de uso...")
            
            # Lista de possíveis XPaths para o botão de aceitar
            accept_button_xpaths = [
                # XPath original
                terms_locators.AGREE_BUTTON,
                # Alternativas comuns
                "//button[@aria-label='Aceitar']",
                "//button[contains(text(), 'Aceitar')]",
                "//button[contains(text(), 'Acepto')]",
                "//button[contains(text(), 'Concordo')]",
                "//button[contains(text(), 'Agree')]",
                "//button[contains(text(), 'I agree')]",
                "//button[@jsname='LgbsSe']", # ID interno do Google
                "//div[@role='button' and contains(., 'Agree')]",
                "//div[@role='button' and contains(., 'I agree')]"
            ]
            
            # Tenta cada XPath até encontrar um que funcione
            for xpath in accept_button_xpaths:
                try:
                    agree_button = self.driver.find_element(By.XPATH, xpath)
                    if agree_button.is_displayed() and agree_button.is_enabled():
                        logger.info(f"✅ Botão 'Aceitar' encontrado com XPath: {xpath}")
                        
                        # Tenta clicar com JavaScript para maior confiabilidade
                        self.driver.execute_script("arguments[0].click();", agree_button)
                        time.sleep(2)
                        
                        logger.info("✅ Termos aceitos com sucesso.")
                        self.terms_info.terms_accepted = True
                        return
                except Exception:
                    continue
                    
            # Se chegou aqui, nenhum botão foi encontrado
            raise TermsAcceptanceError("Botão de aceite dos termos não encontrado.")
            
        except Exception as e:
            raise ElementInteractionError("botão de aceite dos termos", "clicar", str(e))

    def _handle_confirmation_modal(self):
        """Verifica se há um modal de confirmação e lida com ele."""
        try:
            logger.info("📌 Verificando se há um modal de confirmação...")

            # Lista de possíveis XPaths para o botão de confirmação
            confirm_button_xpaths = [
                terms_locators.CONFIRM_BUTTON,
                "//*[@id='yDmH0d']/div[2]/div[2]/div/div[2]/button[2]",  # Sem o /div[3] no final
                "//button[contains(text(), 'Confirm')]",
                "//button[contains(text(), 'Aceitar')]",
                "//button[contains(text(), 'I agree')]",
                "//button[@jsname='j6LnEc']"  # ID interno frequentemente usado pelo Google
            ]

            # Esperar um pouco para o modal aparecer completamente
            time.sleep(2)

            # Tenta cada XPath
            for xpath in confirm_button_xpaths:
                try:
                    if self._element_exists(xpath, timeout=2):
                        # Usar JavaScript para clicar é mais confiável para elementos que podem estar ocultos
                        # ou interceptados por outros elementos
                        confirm_button = self.driver.find_element(By.XPATH, xpath)
                        
                        # Rolar até o elemento para garantir que está visível
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", confirm_button)
                        time.sleep(1)  # Pequena pausa para garantir que o scroll terminou
                        
                        # Clicar com JavaScript
                        self.driver.execute_script("arguments[0].click();", confirm_button)
                        logger.info(f"✅ Modal de confirmação fechado usando XPath: {xpath}")
                        self.terms_info.confirmation_handled = True
                        time.sleep(2)  # Espera para processamento
                        return
                except Exception as e:
                    logger.warning(f"⚠️ Tentativa de clicar no botão de confirmação falhou: {str(e)}")
                    continue

            # Se chegarmos aqui, ou não tem modal ou não conseguimos clicar
            # Vamos verificar se avançamos para a próxima tela
            if "myaccount.google.com" in self.driver.current_url:
                logger.info("✅ Já avançamos para a conta Google. Modal não está mais visível.")
                self.terms_info.confirmation_handled = True
                return

            logger.info("✅ Nenhum modal de confirmação encontrado, continuando...")
            self.terms_info.confirmation_handled = True

        except TimeoutException:
            logger.info("✅ Nenhum modal de confirmação encontrado, continuando...")
            self.terms_info.confirmation_handled = True
        except Exception as e:
            raise ElementInteractionError("modal de confirmação", "clicar", str(e))

    def _skip_recovery_email(self) -> bool:
        """Pula a tela de recuperação de email."""
        try:
            logger.info("📌 Verificando tela de email de recuperação (Skip)...")
            skip_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, terms_locators.RECOVERY_EMAIL_SKIP))
            )
            skip_button.click()
            logger.info("✅ Botão 'Skip' clicado com sucesso.")
            time.sleep(2)  # Pequena pausa

            return True
        except TimeoutException:
            logger.warning("⚠️ Tela de email de recuperação não apareceu, continuando...")
            return True  # Continua o fluxo normalmente
        except Exception as e:
            logger.error(f"❌ Erro ao tentar pular email de recuperação: {str(e)}")
            return False

    def _handle_review_page(self):
        """Confirma o número de telefone na tela de revisão."""
        try:
            logger.info("📌 Verificando tela de confirmação de telefone...")
            
            # Lista de possíveis XPaths para o botão Next
            next_button_xpaths = [
                "//span[contains(text(),'Next')]",
                "//span[contains(text(),'Continue')]",
                "//span[contains(text(),'Continuar')]",
                "//button[@type='submit']",
                "//button[contains(@class, 'VfPpkd-LgbsSe')]"
            ]
            
            # Tenta cada XPath
            for xpath in next_button_xpaths:
                try:
                    if self._element_exists(xpath, timeout=3):
                        next_button = self.driver.find_element(By.XPATH, xpath)
                        if next_button.is_displayed() and next_button.is_enabled():
                            # Tenta clicar no botão com JavaScript para maior confiabilidade
                            self.driver.execute_script("arguments[0].click();", next_button)
                            time.sleep(2)
                            logger.info(f"✅ Clicou no botão de confirmação de telefone: {xpath}")
                            self.terms_info.review_completed = True
                            return
                except:
                    continue

            logger.warning("⚠️ Nenhum botão de confirmação de telefone encontrado, continuando...")
            self.terms_info.review_completed = True

        except Exception as e:
            raise ElementInteractionError("botão de confirmação de telefone", "clicar", str(e))