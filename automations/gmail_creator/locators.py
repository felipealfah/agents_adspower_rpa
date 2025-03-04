from dataclasses import dataclass

@dataclass
class AccountCreationLocators:
    """Localizadores para criação de conta."""
    # Tela "Choose an account"
    CHOOSE_ACCOUNT_SCREEN: str = "//div[contains(text(), 'Choose an account')]"
    USE_ANOTHER_ACCOUNT_BUTTON: str = "/html/body/div[1]/div[1]/div[2]/div/div/div[2]/div/div/div/form/span/section/div/div/div/div/ul/li[3]/div"
    USE_ANOTHER_ACCOUNT_ALT: str = "//div[text()='Use another account']"
    
    # Botões iniciais
    FIRST_BUTTON: str = "//*[@id='yDmH0d']/c-wiz/div/div[3]/div/div[2]/div/div/div[1]/div/button"
    PERSONAL_USE_OPTION: str = "//*[@id='yDmH0d']/c-wiz/div/div[3]/div/div[2]/div/div/div[2]/div/ul/li[1]"
    NEXT_BUTTON: str = "//span[contains(text(),'Next')]"

    # Campos de informação básica
    FIRST_NAME: str = "firstName"
    LAST_NAME: str = "lastName"
    MONTH: str = "month"
    DAY: str = "day"
    YEAR: str = "year"
    GENDER: str = "gender"

@dataclass
class UsernameLocators:
    """Localizadores relacionados ao username."""
    SUGGESTION_OPTION: str = "/html/body/div[1]/div[1]/div[2]/c-wiz/div/div[2]/div/div/div/form/span/section/div/div/div[1]/div[1]/div/span/div[3]/div"
    USERNAME_FIELD: str = "/html/body/div[1]/div[1]/div[2]/c-wiz/div/div[2]/div/div/div/form/span/section/div/div/div/div[1]/div/div[1]/div/div[1]/input"
    USERNAME_TAKEN_ERROR: str = "//div[contains(text(), 'That username is taken. Try another')]"

@dataclass
class PasswordLocators:
    """Localizadores relacionados à senha."""
    PASSWORD_FIELD: str = "/html/body/div[1]/div[1]/div[2]/c-wiz/div/div[2]/div/div/div/form/span/section/div/div/div/div[1]/div/div/div[1]/div/div[1]/div/div[1]/input"
    CONFIRM_PASSWORD: str = "/html/body/div[1]/div[1]/div[2]/c-wiz/div/div[2]/div/div/div/form/span/section/div/div/div/div[1]/div/div/div[2]/div/div[1]/div/div[1]/input"

@dataclass
class PhoneVerificationLocators:
    """Localizadores para verificação de telefone."""
    PHONE_INPUT: str = "/html/body/div[1]/div[1]/div[2]/c-wiz/div/div[2]/div/div/div[1]/form/span/section/div/div/div[2]/div/div[2]/div[1]/label/input"
    ERROR_VERIFICATION: str = "//div[contains(text(),'There was a problem verifying your phone number')]"
    CODE_INPUT: str = "//*[@id='code']"
    RESEND_CODE_BUTTON: str = "//span[contains(text(),'Reenviar código')]"
    NEXT_BUTTON: str = "//span[contains(text(),'Next')]"
    GET_NEW_CODE_BUTTON: str = "//*[@id='yDmH0d']/c-wiz/div/div[3]/div/div[2]/div/div/button/div[3]"
    GET_NEW_CODE_BUTTON_ALT: str = "//*[@id='yDmH0d']/c-wiz/div/div[3]/div/div[2]/div/div/button"  # Versão alternativa sem o div[3]

@dataclass
class TermsLocators:
    """Localizadores para termos e condições."""
    AGREE_BUTTON: str = "/html/body/div[1]/div[1]/div[2]/c-wiz/div/div[3]/div/div[1]/div/div/button/div[3]"
    CONFIRM_BUTTON: str = "//*[@id='yDmH0d']/div[2]/div[2]/div/div[2]/button[2]/div[3]"
    RECOVERY_EMAIL_SKIP: str = "/html/body/div[1]/div[1]/div[2]/c-wiz/div/div[3]/div/div/div[1]/div/div/button"

@dataclass
class VerificationLocators:
    """Localizadores para a verificação de conta"""
    VERIFY_PAGE_URL: str = "https://myaccount.google.com/"
    GMAIL_LOGIN_URL: str = "https://mail.google.com/"
    NEXT_BUTTON: str = "//button[contains(text(), 'Next')]"
    EMAIL_FIELD: str = "//input[@type='email']"

# Criar instâncias para acesso global, assim como os outros localizadores
account_locators = AccountCreationLocators()
username_locators = UsernameLocators()
password_locators = PasswordLocators()
phone_locators = PhoneVerificationLocators()
terms_locators = TermsLocators()
verification_locators = VerificationLocators()  # Agora corretamente definido