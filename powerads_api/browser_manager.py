import requests
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

def start_browser(base_url, headers, user_id):
    """
    Inicia o navegador do AdsPower para um perfil específico e obtém o WebSocket do Selenium.

    Args:
        base_url (str): URL base da API do AdsPower.
        headers (dict): Cabeçalhos da requisição, incluindo autorização.
        user_id (str): ID do perfil no AdsPower.

    Returns:
        dict: Contém `selenium_ws` e `webdriver_path` se bem-sucedido, ou `None` em caso de erro.
    """
    # 1️⃣ Iniciar o navegador do perfil
    url_start = f"{base_url}/api/v1/browser/start?user_id={user_id}"
    response = requests.get(url_start, headers=headers)

    if response.status_code != 200:
        print(f"❌ Erro ao iniciar o navegador: {response.status_code} - {response.text}")
        return None

    try:
        response_json = response.json()
        if response_json.get("code") != 0:
            print(f"❌ Erro ao iniciar o navegador: {response_json.get('msg')}")
            return None
    except requests.exceptions.JSONDecodeError:
        print(f"❌ Erro ao converter resposta em JSON: {response.text}")
        return None

    print(f"🚀 Navegador iniciado para o perfil {user_id}. Aguardando WebDriver...")

    # 2️⃣ Aguardar até 15 segundos para obter WebSocket Selenium
    for tentativa in range(15):
        time.sleep(1.5)

        # Obter informações do navegador ativo
        browser_info = get_active_browser_info(base_url, headers, user_id)

        if browser_info["status"] == "success" and browser_info["selenium_ws"]:
            print(f"✅ WebSocket Selenium obtido: {browser_info['selenium_ws']}")
            print(f"✅ Caminho do WebDriver: {browser_info['webdriver_path']}")
            return browser_info  # Retorna WebSocket Selenium e caminho do WebDriver

        print(f"⚠️ Tentativa {tentativa + 1}: WebDriver ainda não disponível...")

    print("❌ Não foi possível obter o WebSocket do Selenium.")
    return None


def stop_browser(base_url, headers, user_id):
    """
    Fecha o navegador do AdsPower para um perfil específico.

    Args:
        base_url (str): URL base da API do AdsPower.
        headers (dict): Cabeçalhos da requisição, incluindo autorização.
        user_id (str): ID do perfil no AdsPower.

    Returns:
        bool: True se o navegador foi fechado com sucesso, False caso contrário.
    """
    url_stop = f"{base_url}/api/v1/browser/stop?user_id={user_id}"
    response = requests.get(url_stop, headers=headers)

    if response.status_code != 200:
        print(f"❌ Erro ao fechar o navegador: {response.status_code} - {response.text}")
        return False

    try:
        response_json = response.json()
        if response_json.get("code") != 0:
            print(f"❌ Erro ao fechar o navegador: {response_json.get('msg')}")
            return False
    except requests.exceptions.JSONDecodeError:
        print(f"❌ Erro ao converter resposta em JSON: {response.text}")
        return False

    print(f"✅ Navegador do perfil {user_id} fechado com sucesso!")
    return True


def get_active_browser_info(base_url, headers, user_id):
    """
    Obtém informações do navegador ativo no AdsPower para um perfil específico.

    Args:
        base_url (str): URL base da API do AdsPower.
        headers (dict): Cabeçalhos da requisição.
        user_id (str): ID do perfil no AdsPower.

    Returns:
        dict: Contém `selenium_ws` e `webdriver_path`, ou `None` se não encontrado.
    """
    url = f"{base_url}/api/v1/browser/local-active"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return {"status": "error", "message": f"Erro ao verificar navegadores ativos: {response.status_code} - {response.text}"}

    try:
        response_json = response.json()
    except requests.exceptions.JSONDecodeError:
        return {"status": "error", "message": "Erro ao converter resposta para JSON."}

    if response_json.get("code") != 0:
        return {"status": "error", "message": response_json.get("msg", "Erro desconhecido.")}

    # 🔍 Buscar o navegador correspondente ao user_id
    for browser in response_json.get("data", {}).get("list", []):
        if browser.get("user_id") == user_id:
            return {
                "status": "success",
                "selenium_ws": browser.get("ws", {}).get("selenium"),
                "webdriver_path": browser.get("webdriver")
            }

    return {"status": "error", "message": "Nenhum navegador ativo encontrado para este perfil."}

def connect_selenium(selenium_ws, webdriver_path):
    """
    Conecta ao WebDriver do AdsPower.

    Args:
        selenium_ws (str): Endereço WebSocket do Selenium.
        webdriver_path (str): Caminho do WebDriver.

    Returns:
        WebDriver: Instância do Selenium WebDriver conectada.
    """
    try:
        service = Service(executable_path=webdriver_path)
        options = webdriver.ChromeOptions()
        options.add_experimental_option("debuggerAddress", selenium_ws)

        driver = webdriver.Chrome(service=service, options=options)
        print("✅ Conectado ao WebDriver Selenium do AdsPower!")
        return driver
    except Exception as e:
        print(f"❌ Erro ao conectar ao WebDriver: {e}")
        return None