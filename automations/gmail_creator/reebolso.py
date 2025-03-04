import time
import logging
from typing import List, Dict
import requests
from datetime import datetime, timedelta
import pytz
from collections import defaultdict
import sys
import os

# Adiciona o diretório raiz do projeto ao sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from credentials.credentials_manager import load_credentials

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SMSActivationStatus:
    """Constantes para status de ativação"""
    WAITING = '4'  # Aguardando SMS
    CANCELED = 'Status_Cancel'
    REFUND_SUCCESS = 'ACCESS_ACTIVATION_STATUS_OK'
    REFUND_STATUS = '8'

class SMSRefundManager:
    def __init__(self):
        # Carregar API Key do arquivo JSON
        credentials = load_credentials()
        self.api_key = credentials.get("SMS_ACTIVATE_API_KEY", None)
        
        if not self.api_key:
            raise ValueError("❌ ERRO: A chave 'SMS_ACTIVATE_API_KEY' não foi encontrada em credentials.json.")

        self.base_url = "https://api.sms-activate.org/stubs/handler_api.php"
        self.timezone = pytz.timezone('America/Santiago')
        self.max_refund_time = 20  # minutos

    def get_all_activations(self) -> List[Dict]:
        """Obtém todas as ativações ativas."""
        params = {
            'api_key': self.api_key,
            'action': 'getActiveActivations'
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            logger.info(f"Resposta da API: {response.text}")  # Debug
            
            if response.status_code == 200:
                if response.text == "NO_ACTIVATIONS":
                    logger.info("Nenhuma ativação ativa encontrada")
                    return []
                    
                try:
                    data = response.json()
                    if data.get('status') == 'success' and 'activeActivations' in data:
                        activations = data['activeActivations']
                        logger.info(f"Encontradas {len(activations)} ativações ativas")
                        return activations
                    return []
                except ValueError as e:
                    logger.error(f"Erro ao processar resposta: {str(e)}")
                    return []
            else:
                logger.error(f"Erro na requisição. Status: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Erro na requisição: {str(e)}")
            return []

    def analyze_activations(self) -> Dict:
        """Analisa todas as ativações e retorna estatísticas."""
        activations = self.get_all_activations()
        stats = defaultdict(int)
        eligible_for_refund = []
        
        logger.info(f"\n{'='*50}")
        logger.info("ANÁLISE DE ATIVAÇÕES")
        logger.info(f"{'='*50}")
        
        for activation in activations:
            try:
                activation_id = activation['activationId']
                phone_number = activation['phoneNumber']
                status = activation['activationStatus']
                activation_time = datetime.strptime(
                    activation['activationTime'],
                    '%Y-%m-%d %H:%M:%S'
                )
                current_time = datetime.now()
                time_diff = abs((current_time - activation_time).total_seconds() / 60)

                stats['total'] += 1
                stats[f'status_{status}'] += 1

                logger.info(f"\nAnalisando ativação {activation_id}")
                logger.info(f"Número: {phone_number}")
                logger.info(f"Status: {status}")
                logger.info(f"Tempo desde ativação: {time_diff:.2f} minutos")

                # Se está aguardando SMS (status 4) e passou mais de 20 minutos
                if status == '4' and time_diff >= 20:
                    stats['eligible_for_refund'] += 1
                    eligible_for_refund.append({
                        'id': activation_id,
                        'phone': phone_number,
                        'time': time_diff
                    })
                    logger.info("✅ ELEGÍVEL PARA REEMBOLSO (passou do tempo limite)")
                else:
                    if time_diff < 20:
                        reason = f"ainda dentro do tempo limite ({time_diff:.2f} min)"
                    else:
                        reason = f"status não elegível ({status})"
                    logger.info(f"❌ Não elegível: {reason}")

            except Exception as e:
                logger.error(f"Erro ao processar ativação: {str(e)}")
                stats['errors'] += 1
                continue

        # Exibir resumo
        logger.info(f"\n{'='*50}")
        logger.info("RESUMO FINAL")
        logger.info(f"{'='*50}")
        logger.info(f"Total de ativações: {stats['total']}")
        logger.info(f"Elegíveis para reembolso: {stats['eligible_for_refund']}")
        logger.info(f"Erros de processamento: {stats['errors']}")
        
        if eligible_for_refund:
            logger.info("\nAtivações elegíveis para reembolso:")
            for activation in eligible_for_refund:
                logger.info(f"ID: {activation['id']}, Número: {activation['phone']}, Tempo: {activation['time']:.2f} min")

        return eligible_for_refund

    def request_refund(self, activation_id: str) -> bool:
        """Solicita reembolso de uma ativação."""
        params = {
            'api_key': self.api_key,
            'action': 'setStatus',
            'id': activation_id,
            'status': SMSActivationStatus.REFUND_STATUS
        }

        try:
            response = requests.get(self.base_url, params=params)
            logger.info(f"Resposta do reembolso para {activation_id}: {response.text}")  # Debug
            if SMSActivationStatus.REFUND_SUCCESS in response.text:
                return True
            return False
        except Exception as e:
            logger.error(f"Erro ao solicitar reembolso: {str(e)}")
            return False

    def process_refunds(self):
        """Processa reembolsos para ativações elegíveis."""
        logger.info("\nINICIANDO PROCESSO DE REEMBOLSO")
        logger.info(f"{'='*50}")
        
        eligible_activations = self.analyze_activations()
        
        if not eligible_activations:
            logger.info("Nenhuma ativação elegível para reembolso encontrada.")
            return 0

        logger.info(f"\nProcessando {len(eligible_activations)} reembolsos...")
        refund_count = 0
        
        for activation in eligible_activations:
            try:
                logger.info(f"\nSolicitando reembolso para {activation['phone']}")
                if self.request_refund(activation['id']):
                    refund_count += 1
                    logger.info("✅ Reembolso bem-sucedido")
                else:
                    logger.warning("❌ Falha no reembolso")
            except Exception as e:
                logger.error(f"Erro ao processar reembolso: {str(e)}")

        logger.info(f"\n{'='*50}")
        logger.info(f"REEMBOLSOS CONCLUÍDOS: {refund_count}/{len(eligible_activations)}")
        logger.info(f"{'='*50}")
        
        return refund_count

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    try:
        refund_manager = SMSRefundManager()
        total_refunded = refund_manager.process_refunds()
    except Exception as e:
        logger.error(f"Erro no processo de reembolso: {str(e)}")

if __name__ == "__main__":
    main()
