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
        """Processo principal de aceitação dos termos com lógica revisada."""
        try:
            logger.info("📄 Iniciando processo após verificação de telefone...")
            time.sleep(3)  # Aguardar carregamento completo da página
            
            # 1. Primeiro etapa: pular email de recuperação e tela de revisão
            # Estas etapas são comuns a ambos os fluxos
            if not self._skip_recovery_email():
                logger.warning("⚠️ Possível problema ao pular email de recuperação, mas continuando...")
            
            if not self._handle_review_page():
                logger.warning("⚠️ Possível problema na tela de revisão, mas continuando...")
            
            time.sleep(3)  # Aguardar carregamento
            
            # 2. Verificar se estamos na tela com checkboxes
            if self._is_checkbox_terms_screen():
                logger.info("✅ Detectada tela de termos com checkboxes")
                
                # Tentar marcar os checkboxes e clicar no botão
                if self._handle_checkbox_terms():
                    logger.info("✅ Termos com checkboxes tratados com sucesso!")
                    self.terms_info.state = TermsState.COMPLETED
                    return True
                else:
                    logger.error("❌ Falha ao tratar checkboxes, tentando fluxo alternativo...")
            
            # 3. Se não detectou checkboxes ou falhou na etapa anterior, tenta o fluxo normal
            logger.info("📌 Tentando fluxo normal de aceitação dos termos...")
            
            # Tentar aceitar os termos normalmente
            if not self._accept_terms():
                logger.error("❌ Falha ao aceitar termos no fluxo normal")
                self.terms_info.state = TermsState.FAILED
                return False
            
            # Verificar e tratar o modal de confirmação
            if not self._handle_confirmation_modal():
                logger.error("❌ Falha no modal de confirmação")
                self.terms_info.state = TermsState.FAILED
                return False
            
            # Se chegou até aqui, consideramos um sucesso
            logger.info("✅ Processo de aceitação de termos concluído com sucesso!")
            self.terms_info.state = TermsState.COMPLETED
            return True

        except Exception as e:
            logger.error(f"❌ Erro durante processo de aceitação de termos: {str(e)}")
            self.terms_info.state = TermsState.FAILED
            raise TermsAcceptanceError(f"Falha no processo de aceitação de termos: {str(e)}")

    def _is_checkbox_terms_screen(self) -> bool:
        """Verifica se estamos na tela de termos com checkboxes."""
        try:
            # Procura por textos específicos que indicam a tela de checkboxes
            checkbox_indicators = [
                "//div[contains(text(), 'Concordo com')]",
                "//div[contains(text(), 'I agree to')]",
                "//div[contains(text(), 'Estoy de acuerdo con')]",
                "//span[contains(text(), 'Concordo com')]"
            ]
            
            # Verificar a presença de elementos de checkbox
            checkbox_inputs = [
                terms_locators.TERMS_CHECKBOX1,
                terms_locators.TERMS_CHECKBOX2,
                terms_locators.TERMS_CHECKBOX3
            ]
            
            # Verificar indicadores de texto
            for indicator in checkbox_indicators:
                if self._element_exists(indicator, timeout=2):
                    logger.info(f"✅ Indicador de texto para checkboxes encontrado: {indicator}")
                    return True
                    
            # Verificar elementos de checkbox
            for checkbox in checkbox_inputs:
                if self._element_exists(checkbox, timeout=2):
                    logger.info(f"✅ Elemento de checkbox encontrado: {checkbox}")
                    return True
                    
            logger.info("📌 Não foram encontrados indicadores de tela de checkboxes")
            return False
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar tela de checkboxes: {str(e)}")
            return False
            
    def _handle_checkbox_terms(self) -> bool:
        """Manipula especificamente os checkboxes e botão da tela de termos."""
        try:
            logger.info("📌 Tentando marcar checkboxes e confirmar termos...")
            
            # Marcar cada checkbox, com foco nos elementos de label (mais clicáveis)
            checkboxes_marked = True
            
            # Lista de possíveis elementos clicáveis relacionados aos checkboxes
            checkbox_areas = [
                # Primeiro, tentar elementos de label (geralmente mais fáceis de clicar)
                "//div[contains(text(), 'Concordo com')]/preceding::label[1]",
                "//div[contains(text(), 'Concordo com')]/ancestor::label",
                "//span[contains(text(), 'Concordo com')]/preceding::label[1]",
                "//span[contains(text(), 'Concordo com')]/ancestor::label",
                # Depois, tentar elementos de checkbox específicos
                terms_locators.TERMS_CHECKBOX1,
                terms_locators.TERMS_CHECKBOX2,
                terms_locators.TERMS_CHECKBOX3
            ]
            
            # Tentar clicar em cada área
            for area_xpath in checkbox_areas:
                if self._element_exists(area_xpath, timeout=2):
                    try:
                        # Tentar obter o elemento
                        element = self.driver.find_element(By.XPATH, area_xpath)
                        
                        # Scrollar até o elemento
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                        time.sleep(1)
                        
                        # Tentar clicar com diferentes métodos
                        try:
                            # Método 1: Clique direto
                            element.click()
                            logger.info(f"✅ Clique direto bem-sucedido em: {area_xpath}")
                        except Exception as e1:
                            logger.warning(f"⚠️ Clique direto falhou: {str(e1)}")
                            try:
                                # Método 2: Clique via JavaScript
                                self.driver.execute_script("arguments[0].click();", element)
                                logger.info(f"✅ Clique via JavaScript bem-sucedido em: {area_xpath}")
                            except Exception as e2:
                                logger.error(f"❌ Ambos os métodos de clique falharam para: {area_xpath}")
                                checkboxes_marked = False
                    except Exception as e:
                        logger.error(f"❌ Erro ao interagir com elemento {area_xpath}: {str(e)}")
                        checkboxes_marked = False
            
            # Se não conseguiu marcar todos os checkboxes, registrar erro
            if not checkboxes_marked:
                logger.warning("⚠️ Problemas ao marcar alguns checkboxes, mas continuando...")
                
            # Tentar clicar no botão de confirmação
            button_clicked = False
            confirm_button_xpaths = [
                terms_locators.TERMS_CONFIRM_BUTTON,
                "//button[contains(text(), 'Concordo')]",
                "//button[contains(text(), 'I agree')]",
                "//button[contains(text(), 'Aceitar')]",
                "//button[contains(@class, 'VfPpkd-LgbsSe')]"
            ]
            
            for button_xpath in confirm_button_xpaths:
                if self._element_exists(button_xpath, timeout=2):
                    try:
                        button = self.driver.find_element(By.XPATH, button_xpath)
                        
                        # Scrollar até o botão
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                        time.sleep(1)
                        
                        # Tentar clicar
                        try:
                            button.click()
                            logger.info(f"✅ Clique direto no botão: {button_xpath}")
                            button_clicked = True
                            break
                        except Exception as e1:
                            logger.warning(f"⚠️ Clique direto no botão falhou: {str(e1)}")
                            try:
                                self.driver.execute_script("arguments[0].click();", button)
                                logger.info(f"✅ Clique via JavaScript no botão: {button_xpath}")
                                button_clicked = True
                                break
                            except Exception as e2:
                                logger.error(f"❌ Ambos os métodos de clique falharam para o botão: {button_xpath}")
                    except Exception as e:
                        logger.error(f"❌ Erro ao interagir com botão {button_xpath}: {str(e)}")
            
            if not button_clicked:
                logger.error("❌ Não foi possível clicar no botão de confirmação")
                return False
                
            # Aguardar para ver se avançamos
            time.sleep(5)
            
            # Verificar se ainda estamos na mesma tela
            for area_xpath in checkbox_areas[:4]:  # Usar apenas os primeiros indicadores de texto
                if self._element_exists(area_xpath, timeout=2):
                    logger.error("❌ Ainda estamos na tela de checkboxes. O processo não avançou.")
                    return False
                    
            logger.info("✅ Avançamos da tela de checkboxes com sucesso!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao manipular checkboxes: {str(e)}")
            return False

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

    def _accept_terms(self) -> bool:
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
                    if self._element_exists(xpath, timeout=2):
                        agree_button = self.driver.find_element(By.XPATH, xpath)
                        if agree_button.is_displayed() and agree_button.is_enabled():
                            logger.info(f"✅ Botão 'Aceitar' encontrado com XPath: {xpath}")
                            
                            # Tenta clicar com JavaScript para maior confiabilidade
                            self.driver.execute_script("arguments[0].click();", agree_button)
                            time.sleep(2)
                            
                            logger.info("✅ Termos aceitos com sucesso.")
                            self.terms_info.terms_accepted = True
                            return True
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao tentar clicar em {xpath}: {str(e)}")
                    continue
                    
            # Se chegou aqui, nenhum botão foi encontrado
            logger.error("❌ Botão de aceite dos termos não encontrado.")
            return False
            
        except Exception as e:
            logger.error(f"❌ Erro ao aceitar termos: {str(e)}")
            return False

    def _handle_confirmation_modal(self) -> bool:
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
                        return True
                except Exception as e:
                    logger.warning(f"⚠️ Tentativa de clicar no botão de confirmação falhou: {str(e)}")
                    continue

            # Se chegarmos aqui, ou não tem modal ou não conseguimos clicar
            # Vamos verificar se avançamos para a próxima tela
            if "myaccount.google.com" in self.driver.current_url:
                logger.info("✅ Já avançamos para a conta Google. Modal não está mais visível.")
                self.terms_info.confirmation_handled = True
                return True

            logger.info("✅ Nenhum modal de confirmação encontrado, continuando...")
            self.terms_info.confirmation_handled = True
            return True

        except TimeoutException:
            logger.info("✅ Nenhum modal de confirmação encontrado, continuando...")
            self.terms_info.confirmation_handled = True
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao verificar modal de confirmação: {str(e)}")
            return False

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

    def _handle_review_page(self) -> bool:
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
            button_clicked = False
            for xpath in next_button_xpaths:
                try:
                    if self._element_exists(xpath, timeout=3):
                        next_button = self.driver.find_element(By.XPATH, xpath)
                        if next_button.is_displayed() and next_button.is_enabled():
                            # Tenta clicar no botão com JavaScript para maior confiabilidade
                            self.driver.execute_script("arguments[0].click();", next_button)
                            time.sleep(2)
                            logger.info(f"✅ Clicou no botão de confirmação de telefone: {xpath}")
                            button_clicked = True
                            break
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao clicar em botão {xpath}: {str(e)}")
                    continue

            if not button_clicked:
                logger.warning("⚠️ Nenhum botão de confirmação de telefone clicado, mas continuando...")
                
            self.terms_info.review_completed = True
            return True

        except Exception as e:
            logger.error(f"❌ Erro na tela de revisão: {str(e)}")
            return False