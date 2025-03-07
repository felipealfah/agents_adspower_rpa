import imaplib
import logging
from datetime import datetime, timedelta
from enum import Enum


class EmailFolder(Enum):
    INBOX = "INBOX"
    SPAM = "[Gmail]/Spam"
    JUNK = "Junk"
    ALL = "[Gmail]/All Mail"


class EmailReader:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.imap_server = "imap.gmail.com"
        self.mail = None

    def connect(self):
        """Estabelece conexão com servidor IMAP"""
        try:
            self.mail = imaplib.IMAP4_SSL(self.imap_server)
            self.mail.login(self.email, self.password)
            return True
        except Exception as e:
            logging.error(f"Erro ao conectar ao email: {str(e)}")
            return False

    def list_folders(self):
        """Lista todas as pastas disponíveis no email"""
        try:
            _, folders = self.mail.list()
            return [folder.decode().split('"/" ')[-1].strip('"') for folder in folders]
        except Exception as e:
            logging.error(f"Erro ao listar pastas: {str(e)}")
            return []

    def get_verification_code(self, sender=None, minutes=5, folders=[EmailFolder.INBOX, EmailFolder.SPAM]):
        """
        Busca código de verificação em emails recentes nas pastas especificadas
        Args:
            sender: Email do remetente (opcional)
            minutes: Tempo máximo em minutos para buscar emails
            folders: Lista de pastas onde procurar (EmailFolder)
        """
        for folder in folders:
            try:
                self.mail.select(folder.value)
                date = (datetime.now() - timedelta(minutes=minutes)
                        ).strftime("%d-%b-%Y")

                search_criteria = f'(SINCE "{date}")'
                if sender:
                    search_criteria = f'(FROM "{sender}" SINCE "{date}")'

                _, messages = self.mail.search(None, search_criteria)

                # Se encontrar nas mensagens desta pasta
                if messages[0]:
                    # Lógica para extrair o código do email
                    # ...
                    return code

            except Exception as e:
                logging.error(
                    f"Erro ao buscar código na pasta {folder.value}: {str(e)}")
                continue

        return None


# Exemplo de uso
email_reader = EmailReader("seu@email.com", "sua_senha")
if email_reader.connect():
    pastas = email_reader.list_folders()
    print(f"Pastas disponíveis: {pastas}")
