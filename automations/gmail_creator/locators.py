from dataclasses import dataclass

@dataclass
class AccountCreationLocators:
    """Localizadores para criação de conta."""
    # Tela "Choose an account"
    CHOOSE_ACCOUNT_SCREEN: str = "//div[contains(text(), 'Choose an account') or contains(text(), 'Escolha uma conta') or contains(text(), 'Elegir una cuenta')]"
    USE_ANOTHER_ACCOUNT_BUTTON: str = "/html/body/div[1]/div[1]/div[2]/div/div/div[2]/div/div/div/form/span/section/div/div/div/div/ul/li[3]/div"
    USE_ANOTHER_ACCOUNT_ALT: str = "//div[text()='Use another account' or text()='Usar outra conta' or text()='Usar otra cuenta']"
    
    # Botões iniciais
    FIRST_BUTTON: str = "//*[@id='yDmH0d']/c-wiz/div/div[3]/div/div[2]/div/div/div[1]/div/button"
    PERSONAL_USE_OPTION: str = "//*[@id='yDmH0d']/c-wiz/div/div[3]/div/div[2]/div/div/div[2]/div/ul/li[1]"
    NEXT_BUTTON: str = "//button[contains(text(), 'Next') or contains(text(), 'Próximo') or contains(text(), 'Siguiente') or contains(text(), 'Avançar') or contains(@class, 'VfPpkd-LgbsSe')]"

    # Campos de informação básica
    FIRST_NAME: str = "firstName"
    LAST_NAME: str = "lastName"
    MONTH: str = "month"
    DAY: str = "day"
    YEAR: str = "year"
    GENDER: str = "gender"

    # Substitua pelo XPath exato obtido da página
    GENDER_NEUTRAL_OPTION: str = "/html/body/div[1]/div[1]/div[2]/c-wiz/div/div[2]/div/div/div/form/span/section/div/div/div[2]/div[1]/div/div[2]/select/option[4]"

@dataclass
class UsernameLocators:
    """Localizadores relacionados ao username."""
    SUGGESTION_OPTION: str = "/html/body/div[1]/div[1]/div[2]/c-wiz/div/div[2]/div/div/div/form/span/section/div/div/div[1]/div[1]/div/span/div[3]/div"
    USERNAME_FIELD: str = "/html/body/div[1]/div[1]/div[2]/c-wiz/div/div[2]/div/div/div/form/span/section/div/div/div/div[1]/div/div[1]/div/div[1]/input"
    USERNAME_TAKEN_ERROR: str = "//div[contains(text(), 'That username is taken') or contains(text(), 'nome de usuário já está em uso') or contains(text(), 'nombre de usuario ya está en uso') or contains(@jsname, 'B34EJ') or contains(@class, 'error')]"

@dataclass
class PasswordLocators:
    """Localizadores relacionados à senha."""
    PASSWORD_FIELD: str = "/html/body/div[1]/div[1]/div[2]/c-wiz/div/div[2]/div/div/div/form/span/section/div/div/div/div[1]/div/div/div[1]/div/div[1]/div/div[1]/input"
    CONFIRM_PASSWORD: str = "/html/body/div[1]/div[1]/div[2]/c-wiz/div/div[2]/div/div/div/form/span/section/div/div/div/div[1]/div/div/div[2]/div/div[1]/div/div[1]/input"

@dataclass
class PhoneVerificationLocators:
    """Localizadores para verificação de telefone."""
    PHONE_INPUT: str = "/html/body/div[1]/div[1]/div[2]/c-wiz/div/div[2]/div/div/div[1]/form/span/section/div/div/div[2]/div/div[2]/div[1]/label/input"
    ERROR_VERIFICATION: str = "//div[contains(text(),'There was a problem verifying your phone number') or contains(text(),'Houve um problema ao verificar') or contains(text(),'Hubo un problema al verificar') or contains(@class, 'error')]"
    CODE_INPUT: str = "//*[@id='code']"
    RESEND_CODE_BUTTON: str = "//span[contains(text(),'Resend code') or contains(text(),'Reenviar código') or contains(text(),'Reenviar código') or contains(text(),'Get a new code') or contains(text(),'Obter novo código')]"
    NEXT_BUTTON: str = "//button[contains(text(), 'Next') or contains(text(), 'Próximo') or contains(text(), 'Siguiente') or contains(text(), 'Avançar') or contains(@class, 'VfPpkd-LgbsSe')] | //span[contains(text(),'Next') or contains(text(),'Próximo') or contains(text(),'Siguiente') or contains(text(),'Avançar')]/ancestor::button"
    GET_NEW_CODE_BUTTON: str = "//button[contains(text(), 'Get a new code') or contains(text(), 'Obter novo código') or contains(text(), 'Obtener nuevo código')] | //*[@id='yDmH0d']/c-wiz/div/div[3]/div/div[2]/div/div/button"
    GET_NEW_CODE_BUTTON_ALT: str = "//button[contains(@class, 'VfPpkd-LgbsSe') and (contains(., 'new code') or contains(., 'novo código') or contains(., 'nuevo código'))]"

@dataclass
class TermsLocators:
    """Localizadores para termos e condições."""
    AGREE_BUTTON: str = "//button[contains(@class, 'VfPpkd-LgbsSe') or contains(@jsname, 'LgbsSe')] | //button[contains(text(), 'Aceito') or contains(text(), 'I agree') or contains(text(), 'Aceitar') or contains(text(), 'Concordo')]"
    CONFIRM_BUTTON: str = "//button[contains(text(), 'Confirm') or contains(text(), 'Confirmar') or contains(text(), 'Confirmar') or contains(@jsname, 'j6LnEc')] | //*[@id='yDmH0d']/div[2]/div[2]/div/div[2]/button[2]"
    RECOVERY_EMAIL_SKIP: str = "//button[contains(text(), 'Skip') or contains(text(), 'Pular') or contains(text(), 'Omitir')] | //div[contains(@class, 'VfPpkd-RLmnJb')]/ancestor::button"
    
    # Localizadores para a tela alternativa com checkboxes
    TERMS_CHECKBOX1: str = "/html/body/div[1]/div[1]/div[2]/c-wiz/div/div[2]/div/div/div/form/span/div/div[2]/div/div[2]/div[1]/div/div"
    TERMS_CHECKBOX2: str = "/html/body/div[1]/div[1]/div[2]/c-wiz/div/div[2]/div/div/div/form/span/section[2]/div/div/div[1]/div[1]/div/div"
    TERMS_CHECKBOX3: str = "/html/body/div[1]/div[1]/div[2]/c-wiz/div/div[2]/div/div/div/form/span/section[2]/div/div/div[2]/div[1]/div/div/div[2]"
    TERMS_CONFIRM_BUTTON: str = "/html/body/div[1]/div[1]/div[2]/c-wiz/div/div[3]/div/div[1]/div/div/button/div[3]"
    SECOND_AGREE_BUTTON: str = "/html/body/div[1]/div[1]/div[2]/c-wiz/div/div[3]/div/div[1]/div/div/button/div[3]"  # Segundo botão I agree específico
    CONFIRM_BUTTON: str = "//button[contains(@class, 'confirm')]"
    RECOVERY_EMAIL_SKIP: str = "//button[contains(@class, 'VfPpkd-LgbsSe')]/span[contains(text(), 'Skip')]"
# ... outros locators ...
@dataclass
class VerificationLocators:
    """Localizadores para a verificação de conta"""
    VERIFY_PAGE_URL: str = "https://myaccount.google.com/"
    GMAIL_LOGIN_URL: str = "https://mail.google.com/"
    NEXT_BUTTON: str = "//button[contains(text(), 'Next') or contains(text(), 'Próximo') or contains(text(), 'Siguiente') or contains(text(), 'Avançar') or contains(@class, 'VfPpkd-LgbsSe')]"
    EMAIL_FIELD: str = "//input[@type='email']"

# Criar instâncias para acesso global
account_locators = AccountCreationLocators()
username_locators = UsernameLocators()
password_locators = PasswordLocators()
phone_locators = PhoneVerificationLocators()
terms_locators = TermsLocators()
verification_locators = VerificationLocators()