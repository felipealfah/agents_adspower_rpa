import json
import os
import time
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class PhoneManager:
    """
    Gerencia números de telefone, permitindo reutilização de números recentes.
    Otimiza uso de créditos do serviço SMS guardando números que ainda podem ser usados.
    """
    
    def __init__(self, storage_path="credentials/phone_numbers.json"):
        """
        Inicializa o gerenciador de números de telefone.
        
        Args:
            storage_path: Caminho para o arquivo JSON de armazenamento
        """
        self.storage_path = storage_path
        self.numbers = self._load_numbers()
        self.reuse_window = 30 * 60  # 30 minutos em segundos - janela de reutilização
        
    def _load_numbers(self):
        """Carrega os números do arquivo de armazenamento."""
        if not os.path.exists(self.storage_path):
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            return []
            
        try:
            with open(self.storage_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
            
    def _save_numbers(self):
        """Salva os números no arquivo de armazenamento."""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        with open(self.storage_path, 'w') as f:
            json.dump(self.numbers, f, indent=4)
            
    def add_number(self, phone_number, country_code, activation_id, service="go"):
        """
        Adiciona um número ao gerenciador.
        
        Args:
            phone_number: Número de telefone
            country_code: Código do país
            activation_id: ID da ativação no serviço SMS
            service: Código do serviço (ex: "go" para Gmail)
        """
        current_time = time.time()
        
        # Verificar se o número já existe e atualizar
        for number in self.numbers:
            if number["phone_number"] == phone_number:
                number["last_used"] = current_time
                number["services"].append(service) if service not in number["services"] else None
                self._save_numbers()
                return
                
        # Adicionar novo número
        self.numbers.append({
            "phone_number": phone_number,
            "country_code": country_code,
            "activation_id": activation_id,
            "first_used": current_time,
            "last_used": current_time,
            "services": [service],
            "times_used": 1
        })
        self._save_numbers()
        logger.info(f"✅ Número {phone_number} adicionado ao gerenciador.")
        
    def get_reusable_number(self, service="go"):
        """
        Obtém um número reutilizável que ainda está dentro da janela de validade.
        
        Args:
            service: Código do serviço para o qual o número será usado
            
        Returns:
            dict: Informações do número reutilizável ou None se não houver
        """
        current_time = time.time()
        valid_numbers = []
        
        # Limpar números expirados
        self._cleanup_expired_numbers()
        
        # Buscar números válidos
        for number in self.numbers:
            time_since_last_use = current_time - number["last_used"]
            
            # Verificar se está dentro da janela de reutilização
            if time_since_last_use < self.reuse_window:
                # Verificar se o número não foi usado para este serviço
                if service not in number["services"]:
                    valid_numbers.append(number)
        
        # Ordenar por menos utilizado primeiro
        valid_numbers.sort(key=lambda x: x["times_used"])
        
        if valid_numbers:
            # Atualizar o número selecionado
            selected = valid_numbers[0]
            selected["last_used"] = current_time
            selected["times_used"] += 1
            selected["services"].append(service)
            self._save_numbers()
            
            time_left = self.reuse_window - (current_time - selected["first_used"])
            minutes_left = int(time_left / 60)
            
            logger.info(f"♻️ Reutilizando número {selected['phone_number']} ({minutes_left} minutos restantes)")
            return selected
        
        return None
        
    def _cleanup_expired_numbers(self):
        """Remove números que já expiraram da janela de reutilização."""
        current_time = time.time()
        self.numbers = [
            number for number in self.numbers 
            if (current_time - number["first_used"]) < self.reuse_window
        ]
        self._save_numbers()
        
    def mark_number_used(self, phone_number, service="go"):
        """
        Marca um número como usado para um determinado serviço.
        
        Args:
            phone_number: Número de telefone
            service: Código do serviço
        """
        for number in self.numbers:
            if number["phone_number"] == phone_number:
                number["last_used"] = time.time()
                number["times_used"] += 1
                if service not in number["services"]:
                    number["services"].append(service)
                self._save_numbers()
                return True
        return False
    
    def get_stats(self):
        """
        Retorna estatísticas sobre os números gerenciados.
        
        Returns:
            dict: Estatísticas de uso dos números
        """
        total_numbers = len(self.numbers)
        total_uses = sum(number["times_used"] for number in self.numbers)
        services_used = set()
        
        for number in self.numbers:
            for service in number["services"]:
                services_used.add(service)
        
        current_time = time.time()
        active_numbers = sum(1 for number in self.numbers if (current_time - number["last_used"]) < self.reuse_window)
        
        return {
            "total_numbers": total_numbers,
            "active_numbers": active_numbers,
            "total_uses": total_uses,
            "services_used": list(services_used),
            "average_uses_per_number": total_uses / total_numbers if total_numbers > 0 else 0,
            "estimated_savings": total_uses - total_numbers if total_numbers > 0 else 0
        }