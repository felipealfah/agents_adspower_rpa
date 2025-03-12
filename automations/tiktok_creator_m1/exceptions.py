class TikTokCreatorException(Exception):
    """Exceção base para todas as exceções do TikTokCreator."""
    pass


class AccountSetupError(TikTokCreatorException):
    """Exceções relacionadas à configuração inicial da conta."""
    pass


class PhoneVerificationError(TikTokCreatorException):
    """Exceções relacionadas à verificação de telefone."""
    pass


class TikTokCreationError(Exception):
    """Erro genérico para falhas na criação de conta TikTok."""

    def __init__(self, message="Erro na criação da conta TikTok"):
        self.message = message
        super().__init__(self.message)


class ElementInteractionError(TikTokCreatorException):
    """Erros de interação com elementos da página."""

    def __init__(self, element_type, action, details=None):
        message = f"Erro ao {action} {element_type}"
        if details:
            message += f": {details}"
        super().__init__(message)
