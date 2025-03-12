"""
Locators para elementos da página do TikTok.
Organize por seção/funcionalidade para facilitar manutenção.
"""

class SignupLocators:
    """Locators para a página de cadastro."""
    SIGNUP_BUTTON = "//button[contains(@class, 'signup-button')]"  # Botão de cadastro
    USERNAME_INPUT = "//input[@name='username']"  # Campo de nome de usuário
    PASSWORD_INPUT = "//input[@type='password']"  # Campo de senha
    PHONE_INPUT = "//input[@name='mobile']"  # Campo de telefone
    BIRTHDAY_MONTH = "//select[@name='month']"  # Selecionar mês de aniversário
    BIRTHDAY_DAY = "//select[@name='day']"  # Selecionar dia de aniversário
    BIRTHDAY_YEAR = "//select[@name='year']"  # Selecionar ano de aniversário
    NEXT_BUTTON = "//button[contains(@class, 'next-button')]"  # Botão para avançar

    # Novos locators para o fluxo de criação de conta
    TIKTOK_SIGNUP_URL = "https://www.tiktok.com/signup"  # URL de cadastro
    INITIAL_SIGNUP_BUTTON = "/html/body/div[1]/div/div[2]/div/div[1]/div/div[2]/div[2]"  # Botão de cadastro inicial
    CONTINUE_LINK = "/html/body/div[1]/div/div[2]/div[1]/form/div[4]/a"  # Link para continuar o cadastro

class VerificationLocators:
    """Locators para a verificação de telefone."""
    PHONE_INPUT = "//input[@name='mobile']"  # Campo de telefone para verificação
    SMS_CODE_INPUT = "//input[@name='code']"  # Campo para código SMS
    VERIFY_BUTTON = "//button[contains(@class, 'verify-button')]"  # Botão de verificação
    RESEND_CODE = "//button[contains(@class, 'resend-code')]"  # Botão para reenviar código