import os
import sys
import time
import json
import logging
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Criar diretório de logs se não existir
os.makedirs("logs", exist_ok=True)

# Configurar logging para exibir no terminal e no arquivo
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/gmail_automation.log"),
        logging.StreamHandler(sys.stdout)  # Adiciona handler para o terminal
    ]
)

# Adicionar o caminho correto do projeto antes das importações
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importações
from apis.sms_api import SMSAPI
from powerads_api.ads_power_manager import AdsPowerManager
from apis.phone_manager import PhoneManager
from credentials.credentials_manager import load_credentials, add_or_update_api_key, delete_api_key, get_credential
from powerads_api.browser_manager import start_browser, stop_browser, get_active_browser_info, connect_selenium
from powerads_api.profiles import get_profiles
from automations.data_generator import generate_gmail_credentials
from automations.gmail_creator.core import GmailCreator

# Caminho para salvar credenciais do Gmail
CREDENTIALS_PATH = "credentials/gmail.json"

# Inicializar estado da sessão para rastrear atualizações de credenciais
if 'last_credentials_update' not in st.session_state:
    st.session_state.last_credentials_update = time.time()

# Ativar recarregamento amplo na sessão para componentes gerenciados
if 'initialized' not in st.session_state:
    st.session_state.initialized = False
    st.session_state.active_profile = None
    st.session_state.profiles = {}  # Adicionar profiles ao estado da sessão
    st.session_state.last_reload = 0  # Timestamp da última recarga de perfis

# Inicializar gerenciadores
phone_manager = PhoneManager()

# Função para recarregar configurações das APIs quando necessário


def refresh_api_configurations():
    """Recarrega as configurações das APIs a partir das credenciais mais recentes."""
    logging.info("Recarregando configurações das APIs")

    # Recarregar credenciais (usar cache interno do gerenciador)
    credentials = load_credentials()

    # Configurar cabeçalhos do AdsPower com base nas credenciais atualizadas
    pa_api_key = credentials.get("PA_API_KEY", None)
    pa_base_url = credentials.get(
        "PA_BASE_URL", "http://local.adspower.net:50325")

    headers = {
        "Authorization": f"Bearer {pa_api_key}",
        "Content-Type": "application/json"
    } if pa_api_key else {}

    # Atualizar a instância da API de SMS
    sms_api = SMSAPI(api_key=None)  # Inicializa sem chave
    sms_api.refresh_credentials()   # Recarrega a chave da API das credenciais

    # Criar ou atualizar AdsPowerManager
    adspower_manager = None
    if pa_api_key:
        adspower_manager = AdsPowerManager(pa_base_url, pa_api_key)

    return {
        "sms_api": sms_api,
        "pa_base_url": pa_base_url,
        "pa_headers": headers,
        "adspower_manager": adspower_manager
    }

# Função para recarregar perfis do AdsPower


def reload_profiles():
    """Recarrega a lista de perfis do AdsPower."""
    logging.info("Recarregando perfis do AdsPower")
    try:
        if adspower_manager:
            profiles_list = adspower_manager.get_all_profiles(
                force_refresh=True)
            if profiles_list:
                # Atualizar o estado da sessão
                st.session_state.profiles = {
                    p["user_id"]: p["name"] for p in profiles_list}
                st.session_state.last_reload = time.time()
                return st.session_state.profiles
            else:
                logging.warning("Nenhum perfil encontrado no AdsPower")
                return {}
        else:
            logging.warning("Gerenciador AdsPower não inicializado")
            return {}
    except Exception as e:
        logging.error(f"Erro ao recarregar perfis: {str(e)}")
        return {}


# Obter configurações iniciais das APIs
api_config = refresh_api_configurations()
sms_api = api_config["sms_api"]
PA_BASE_URL = api_config["pa_base_url"]
HEADERS = api_config["pa_headers"]
adspower_manager = api_config["adspower_manager"]

# Função para remover uma conta da lista


def delete_account(idx):
    logging.info(f"Tentando remover conta no índice {idx}")
    try:
        # Carregar lista atual
        if os.path.exists(CREDENTIALS_PATH) and os.path.getsize(CREDENTIALS_PATH) > 0:
            with open(CREDENTIALS_PATH, "r") as file:
                accounts = json.load(file)

            # Remover a conta pelo índice
            if 0 <= idx < len(accounts):
                removed_account = accounts.pop(idx)

                # Salvar a lista atualizada
                with open(CREDENTIALS_PATH, "w") as file:
                    json.dump(accounts, file, indent=4)

                logging.info(
                    f"Conta {removed_account.get('email', 'Conta desconhecida')} removida com sucesso")
                return True, removed_account.get('email', 'Conta desconhecida')
            return False, "Índice inválido"
        return False, "Arquivo não encontrado"
    except Exception as e:
        logging.error(f"Erro ao remover conta: {str(e)}")
        return False, str(e)

# Função para limpar todas as contas


def clear_all_accounts():
    logging.info("Tentando limpar todas as contas")
    try:
        if os.path.exists(CREDENTIALS_PATH):
            with open(CREDENTIALS_PATH, "w") as file:
                json.dump([], file)
            logging.info("Todas as contas foram removidas com sucesso")
            return True
        return False
    except Exception as e:
        logging.error(f"Erro ao limpar contas: {str(e)}")
        st.error(f"Erro ao limpar contas: {str(e)}")
        return False


# Criar menu lateral no Streamlit
st.sidebar.title("🔧 Menu de Navegação")

# Definir a página atual se não estiver no estado da sessão
if 'current_page' not in st.session_state:
    st.session_state.current_page = "🔑 Gerenciar Credenciais"

# Criar links de navegação em vez de radio buttons
if st.sidebar.button("🔑 Gerenciar Credenciais"):
    st.session_state.current_page = "🔑 Gerenciar Credenciais"

if st.sidebar.button("📩 Automação Gmail"):
    st.session_state.current_page = "📩 Automação Gmail"

if st.sidebar.button("📜 Contas Criadas"):
    st.session_state.current_page = "📜 Contas Criadas"

if st.sidebar.button("📱 Gerenciar Números"):
    st.session_state.current_page = "📱 Gerenciar Números"

# Adicionar informações de saldo na barra lateral
try:
    sms_balance = sms_api.get_balance()
    if sms_balance is not None:
        saldo_color = "green" if sms_balance > 20 else "orange" if sms_balance > 5 else "red"
        st.sidebar.markdown(
            f"💰 **Saldo SMS:** <span style='color:{saldo_color}'>{sms_balance:.2f} RUB</span>", unsafe_allow_html=True)
    else:
        st.sidebar.warning("⚠️ Não foi possível obter o saldo SMS")
except Exception as e:
    logging.error(f"Erro ao obter saldo SMS: {str(e)}")

# Adicionar status do AdsPower na barra lateral
if adspower_manager:
    api_health = adspower_manager.check_api_health()
    if api_health:
        st.sidebar.success("✅ AdsPower conectado")
    else:
        st.sidebar.error("❌ AdsPower não disponível")
else:
    st.sidebar.warning("⚠️ Chave de API do AdsPower não configurada")

# **ABA 1 - GERENCIAMENTO DE CREDENCIAIS**
if st.session_state.current_page == "🔑 Gerenciar Credenciais":
    st.title("🔑 Gerenciamento de Credenciais")
    logging.info("Acessando aba de Gerenciamento de Credenciais")

    # Botão para recarregar credenciais manualmente (para debugging)
    if st.button("🔄 Recarregar Credenciais"):
        logging.info("Recarregando credenciais manualmente")
        st.session_state.last_credentials_update = time.time()
        api_config = refresh_api_configurations()
        sms_api = api_config["sms_api"]
        PA_BASE_URL = api_config["pa_base_url"]
        HEADERS = api_config["pa_headers"]
        adspower_manager = api_config["adspower_manager"]
        st.success("✅ Credenciais recarregadas com sucesso!")

    # Carregar credenciais existentes
    credentials = load_credentials(force_reload=True)
    st.subheader("📜 Credenciais Atuais")
    if credentials:
        for key, value in credentials.items():
            st.write(f"**{key}**: `{value}`")
    else:
        st.warning("⚠️ Nenhuma credencial encontrada.")

    # Formulário para adicionar/atualizar chave
    st.subheader("➕ Adicionar/Atualizar Chave de API")
    with st.form("add_key_form"):
        key_name = st.text_input("Nome da Chave (ex: PA_API_KEY)")
        key_value = st.text_input("Valor da Chave", type="password")
        submit_button = st.form_submit_button("💾 Salvar Chave")

        if submit_button:
            if key_name and key_value:
                logging.info(f"Tentando adicionar/atualizar chave: {key_name}")
                if add_or_update_api_key(key_name, key_value):
                    st.session_state.last_credentials_update = time.time()
                    api_config = refresh_api_configurations()
                    sms_api = api_config["sms_api"]
                    PA_BASE_URL = api_config["pa_base_url"]
                    HEADERS = api_config["pa_headers"]
                    adspower_manager = api_config["adspower_manager"]
                    st.success(
                        f"✅ Chave '{key_name}' adicionada/atualizada com sucesso!")
                    logging.info(
                        f"Chave '{key_name}' adicionada/atualizada com sucesso")
                else:
                    st.error("❌ Erro ao salvar a chave. Verifique os logs.")
                    logging.error(f"Erro ao salvar a chave '{key_name}'")
            else:
                st.error("❌ Nome e valor da chave são obrigatórios.")
                logging.warning("Tentativa de salvar chave sem nome ou valor")

    # Seção para excluir chave
    st.subheader("🗑️ Remover Chave de API")
    key_to_delete = st.selectbox("Selecione a chave para remover", options=list(
        credentials.keys()) if credentials else [])

    if st.button("🗑️ Excluir Chave"):
        if key_to_delete:
            logging.info(f"Tentando excluir chave: {key_to_delete}")
            if delete_api_key(key_to_delete):
                st.session_state.last_credentials_update = time.time()
                api_config = refresh_api_configurations()
                sms_api = api_config["sms_api"]
                PA_BASE_URL = api_config["pa_base_url"]
                HEADERS = api_config["pa_headers"]
                adspower_manager = api_config["adspower_manager"]
                st.success(f"✅ Chave '{key_to_delete}' removida com sucesso!")
                logging.info(f"Chave '{key_to_delete}' removida com sucesso")
            else:
                st.error("❌ Erro ao remover a chave. Verifique os logs.")
                logging.error(f"Erro ao remover a chave '{key_to_delete}'")
        else:
            st.warning("⚠️ Nenhuma chave selecionada.")
            logging.warning("Tentativa de excluir chave sem selecionar uma")

    # Mostrar informações sobre as APIs configuradas
    st.subheader("🔌 Status das APIs")

    # Status da API SMS
    sms_balance = None
    try:
        sms_balance = sms_api.get_balance()
        if sms_balance is not None:
            st.success(f"✅ API SMS conectada. Saldo: {sms_balance} RUB")
            logging.info(f"API SMS conectada. Saldo: {sms_balance} RUB")
        else:
            st.error("❌ API SMS não conectada. Verifique sua chave de API.")
            logging.error("API SMS não conectada")
    except Exception as e:
        st.error(f"❌ Erro ao conectar à API SMS: {str(e)}")
        logging.error(f"Erro ao conectar à API SMS: {str(e)}")

    # Status da API AdsPower
    if HEADERS.get("Authorization"):
        try:
            # Tentar uma requisição simples para verificar conexão
            if adspower_manager:
                api_health = adspower_manager.check_api_health()
                if api_health:
                    profiles = adspower_manager.get_all_profiles()
                    st.success(
                        f"✅ API AdsPower conectada. Total de perfis: {len(profiles)}")
                    logging.info(
                        f"API AdsPower conectada. Total de perfis: {len(profiles)}")
                else:
                    st.warning(
                        "⚠️ API AdsPower não responde corretamente. Verifique a conexão.")
                    logging.warning("API AdsPower não responde corretamente")
            else:
                st.warning("⚠️ Gerenciador AdsPower não inicializado.")
                logging.warning("Gerenciador AdsPower não inicializado")
        except Exception as e:
            st.error(f"❌ Erro ao conectar à API AdsPower: {str(e)}")
            logging.error(f"Erro ao conectar à API AdsPower: {str(e)}")
    else:
        st.warning(
            "⚠️ API AdsPower não configurada. Adicione a chave 'PA_API_KEY'.")
        logging.warning("API AdsPower não configurada")


# **ABA 2 - AUTOMAÇÃO GMAIL**
elif st.session_state.current_page == "📩 Automação Gmail":
    # Verificar se é necessário recarregar as configurações das APIs
    api_config = refresh_api_configurations()
    sms_api = api_config["sms_api"]
    PA_BASE_URL = api_config["pa_base_url"]
    HEADERS = api_config["pa_headers"]
    adspower_manager = api_config["adspower_manager"]

    st.title("📩 Automação no Gmail - Criar Conta")
    logging.info("Acessando aba de Automação Gmail")

    # Listar perfis disponíveis no AdsPower
    profiles_list = []
    profile_options = {}

    # Botão para recarregar perfis
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Recarregar Perfis"):
            logging.info("Recarregando perfis manualmente")
            profile_options = reload_profiles()
            st.success("✅ Perfis recarregados com sucesso!")

    try:
        if adspower_manager:
            # Verificar saúde da API
            if adspower_manager.check_api_health():
                # Usar perfis em cache se disponíveis e recentes
                if st.session_state.profiles and time.time() - st.session_state.last_reload < 300:  # 5 minutos
                    profile_options = st.session_state.profiles
                    logging.info(
                        f"Usando {len(profile_options)} perfis em cache")
                else:
                    profiles_list = adspower_manager.get_all_profiles()
                    profile_options = {p["user_id"]: p["name"]
                                       for p in profiles_list}
                    st.session_state.profiles = profile_options
                    st.session_state.last_reload = time.time()
                    logging.info(
                        f"Carregados {len(profiles_list)} perfis do AdsPower")
            else:
                st.warning(
                    "⚠️ AdsPower API não está respondendo corretamente. Verifique a conexão.")
                logging.warning(
                    "AdsPower API não está respondendo corretamente")
        else:
            # Fallback para o método antigo
            profiles_list = get_profiles(
                PA_BASE_URL, HEADERS) if HEADERS.get("Authorization") else []
            profile_options = {p["user_id"]: p["name"]
                               for p in profiles_list} if profiles_list else {}
            logging.info(
                f"Carregados {len(profiles_list)} perfis via método tradicional")

        if not profile_options:
            st.warning(
                "⚠️ Nenhum perfil encontrado no AdsPower. Verifique suas credenciais.")
            logging.warning("Nenhum perfil encontrado no AdsPower")

    except Exception as e:
        profile_options = {}
        st.error(f"Erro ao carregar perfis: {e}")
        logging.error(f"Erro ao carregar perfis: {e}")

    # Verificar se há números de telefone reutilizáveis
    reusable_numbers = []
    try:
        for number in phone_manager._load_numbers():
            time_since_first_use = time.time() - number["first_used"]
            if time_since_first_use < phone_manager.reuse_window:
                # Converter tempo para minutos e segundos
                minutes_left = int(
                    (phone_manager.reuse_window - time_since_first_use) / 60)
                reusable_numbers.append(number)

        if reusable_numbers:
            st.info(
                f"♻️ {len(reusable_numbers)} números disponíveis para reutilização, economizando em custos SMS.")
            logging.info(
                f"{len(reusable_numbers)} números disponíveis para reutilização")
    except Exception as e:
        st.error(f"Erro ao verificar números reutilizáveis: {e}")
        logging.error(f"Erro ao verificar números reutilizáveis: {e}")

    # UI para criação de contas
    if profile_options:
        # Seleção do perfil
        selected_profile = st.selectbox(
            "Selecione um perfil:",
            options=list(profile_options.keys()),
            format_func=lambda x: profile_options[x]
        )

        # Opção para reutilizar número de telefone
        use_existing_number = False
        if reusable_numbers:
            use_existing_number = st.checkbox("♻️ Reutilizar número de telefone existente", value=True,
                                              help="Economize créditos usando um número já comprado que ainda está válido")

        # Botão para iniciar a automação do Gmail
        if st.button("🚀 Criar Conta Gmail"):
            logging.info(
                f"Iniciando criação de conta Gmail para perfil: {profile_options[selected_profile]}")
            # Verificar se API SMS está configurada
            if not get_credential("SMS_ACTIVATE_API_KEY"):
                st.error(
                    "❌ API SMS não configurada. Adicione a chave 'SMS_ACTIVATE_API_KEY' primeiro.")
                logging.error("API SMS não configurada")
                st.stop()

            # Verificar saldo da API SMS
            sms_balance = sms_api.get_balance()
            if sms_balance is None or sms_balance <= 0:
                st.error(
                    f"❌ Saldo insuficiente na API SMS. Saldo atual: {sms_balance} RUB")
                logging.error(
                    f"Saldo insuficiente na API SMS: {sms_balance} RUB")
                st.stop()

            st.write(
                f"🚀 Criando conta Gmail para o perfil: {profile_options[selected_profile]}")

            # Status para acompanhamento
            status_container = st.empty()
            status = status_container.status("Iniciando processo...")

            # Se estamos usando o AdsPowerManager
            driver = None
            if adspower_manager:
                with status:
                    st.write("Iniciando navegador AdsPower...")
                    logging.info("Iniciando navegador AdsPower")
                    start_success, browser_info = adspower_manager.start_browser(
                        selected_profile)

                    if not start_success:
                        st.error("❌ Erro ao iniciar navegador AdsPower.")
                        status.update(
                            label="Erro ao iniciar navegador", state="error")
                        logging.error("Erro ao iniciar navegador AdsPower")
                        st.stop()

                    driver = adspower_manager.connect_selenium(browser_info)
                    if not driver:
                        st.error("❌ Erro ao conectar ao WebDriver.")
                        status.update(
                            label="Erro ao conectar ao WebDriver", state="error")
                        logging.error("Erro ao conectar ao WebDriver")
                        st.stop()
            else:
                # Método tradicional (fallback)
                with status:
                    st.write("Iniciando navegador via API tradicional...")
                    logging.info("Iniciando navegador via API tradicional")
                    start_browser(PA_BASE_URL, HEADERS, selected_profile)
                    time.sleep(5)

                    # Obter informações do navegador ativo
                    browser_info = get_active_browser_info(
                        PA_BASE_URL, HEADERS, selected_profile)
                    if not browser_info or browser_info["status"] != "success":
                        st.error(
                            "❌ Erro ao obter informações do navegador ativo.")
                        status.update(
                            label="Erro ao obter informações do navegador", state="error")
                        logging.error(
                            "Erro ao obter informações do navegador ativo")
                        st.stop()

                    selenium_ws = browser_info["selenium_ws"]
                    webdriver_path = browser_info["webdriver_path"]

                    if not selenium_ws or not webdriver_path:
                        st.error("⚠️ WebSocket ou WebDriver não encontrados!")
                        status.update(
                            label="WebSocket ou WebDriver não encontrados", state="error")
                        logging.error("WebSocket ou WebDriver não encontrados")
                        st.stop()

                    # Conectar ao WebDriver
                    driver = connect_selenium(selenium_ws, webdriver_path)
                    if not driver:
                        st.error("❌ Erro ao conectar ao WebDriver!")
                        status.update(
                            label="Erro ao conectar ao WebDriver", state="error")
                        logging.error("Erro ao conectar ao WebDriver")
                        st.stop()

            status.update(
                label="Navegador iniciado. Gerando credenciais...", state="running")

            # Gerar credenciais para a conta Gmail
            credentials = generate_gmail_credentials()

            # Configurar parâmetros para reutilização de números
            params = {}
            if use_existing_number and reusable_numbers:
                reusable_number = phone_manager.get_reusable_number(
                    service="go")
                if reusable_number:
                    params = {
                        "reuse_number": True,
                        "phone_number": reusable_number["phone_number"],
                        "activation_id": reusable_number["activation_id"],
                        "country_code": reusable_number["country_code"]
                    }
                    status.update(
                        label=f"Reutilizando número {reusable_number['phone_number']}...", state="running")
                    logging.info(
                        f"Reutilizando número {reusable_number['phone_number']}")

            # Criar instância do Gmail Creator (passando o perfil do AdsPower)
            gmail_creator = GmailCreator(
                driver, credentials, sms_api, selected_profile)

            status.update(label="Iniciando criação de conta...",
                          state="running")

            # Iniciar automação e capturar progresso
            sucesso, account_data = gmail_creator.create_account(
                phone_params=params)

            # Encerrar navegador após a automação
            if adspower_manager:
                adspower_manager.stop_browser(selected_profile)
                logging.info("Navegador AdsPower encerrado")
            else:
                stop_browser(PA_BASE_URL, HEADERS, selected_profile)
                logging.info("Navegador encerrado via API tradicional")

            if sucesso and account_data:
                status.update(label="Conta criada com sucesso!",
                              state="complete")
                st.success("✅ Conta Gmail criada com sucesso!")
                logging.info(
                    f"Conta Gmail criada com sucesso: {account_data.get('email', 'email desconhecido')}")

                # Mostrar informações mais completas sobre a conta criada
                st.write(f"""
                📧 **Email:** {account_data['email']}  
                📱 **Telefone:** {account_data['phone']} ({account_data.get('country_name', 'Desconhecido')})  
                👤 **Nome:** {account_data.get('first_name', '')} {account_data.get('last_name', '')}
                """)

                # Registrar número no PhoneManager para possível reutilização
                # Isto só acontece quando a verificação de SMS foi bem-sucedida
                if not use_existing_number and 'phone' in account_data and 'activation_id' in account_data:
                    try:
                        phone_manager.add_number(
                            phone_number=account_data['phone'],
                            country_code=account_data.get('country_code', '0'),
                            activation_id=account_data['activation_id'],
                            service="go"
                        )
                        st.info(
                            "✅ Número verificado e registrado para possível reutilização.")
                        logging.info(
                            f"Número {account_data['phone']} registrado para reutilização")
                    except Exception as e:
                        st.warning(
                            f"⚠️ Não foi possível registrar o número para reutilização: {str(e)}")
                        logging.warning(
                            f"Não foi possível registrar o número para reutilização: {str(e)}")

                # Salvar credenciais com todos os dados
                try:
                    existing_credentials = []
                    if os.path.exists(CREDENTIALS_PATH) and os.path.getsize(CREDENTIALS_PATH) > 0:
                        with open(CREDENTIALS_PATH, "r") as file:
                            try:
                                existing_credentials = json.load(file)
                                if not isinstance(existing_credentials, list):
                                    existing_credentials = []
                            except json.JSONDecodeError:
                                existing_credentials = []

                    # Adicionar timestamp de criação
                    account_data["creation_date"] = time.strftime(
                        "%Y-%m-%d %H:%M:%S")

                    # Garantir que todos os campos importantes estejam presentes
                    required_fields = [
                        "email", "password", "phone", "profile",
                        "country_code", "country_name", "activation_id",
                        "first_name", "last_name"
                    ]

                    for field in required_fields:
                        if field not in account_data:
                            account_data[field] = "unknown"

                    existing_credentials.append(account_data)

                    with open(CREDENTIALS_PATH, "w") as file:
                        json.dump(existing_credentials, file, indent=4)

                    st.success(f"📂 Credenciais salvas em `{CREDENTIALS_PATH}`")
                    logging.info(f"Credenciais salvas em {CREDENTIALS_PATH}")
                except Exception as e:
                    st.error(f"Erro ao salvar credenciais: {e}")
                    logging.error(f"Erro ao salvar credenciais: {e}")

            else:
                status.update(label="Erro na criação da conta", state="error")
                st.error("❌ Erro na criação da conta.")
                logging.error("Erro na criação da conta Gmail")

# **ABA 3 - CONTAS CRIADAS**
elif st.session_state.current_page == "📜 Contas Criadas":
    st.title("📜 Contas Criadas")
    logging.info("Acessando aba de Contas Criadas")

    # Carregar a lista de contas
    credentials_list = []
    if os.path.exists(CREDENTIALS_PATH) and os.path.getsize(CREDENTIALS_PATH) > 0:
        with open(CREDENTIALS_PATH, "r") as file:
            try:
                credentials_list = json.load(file)
                logging.info(
                    f"Carregadas {len(credentials_list)} contas do arquivo")
            except json.JSONDecodeError:
                st.error(
                    "❌ Erro ao carregar o arquivo de contas. O formato JSON pode estar corrompido.")
                logging.error(
                    "Erro ao carregar o arquivo de contas - JSON inválido")

    # Mostrar contagem e botão para limpar todas
    if credentials_list:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info(f"Total de contas: {len(credentials_list)}")
        with col2:
            if st.button("🗑️ Limpar Todas", help="Apagar todas as contas"):
                if st.checkbox("Confirmar exclusão de todas as contas", key="confirm_clear"):
                    if clear_all_accounts():
                        st.success(
                            "Todas as contas foram removidas com sucesso!")
                        logging.info(
                            "Todas as contas foram removidas com sucesso")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Erro ao remover todas as contas.")
                        logging.error("Erro ao remover todas as contas")

        # Adicionar campo de busca
        search_term = st.text_input(
            "🔍 Buscar conta", placeholder="Digite email, telefone ou data")

        # Mostrar contas da mais recente para a mais antiga
        reversed_list = list(reversed(credentials_list))

        # Filtrar contas baseado na busca
        filtered_list = reversed_list
        if search_term:
            filtered_list = [
                cred for cred in reversed_list
                if search_term.lower() in str(cred.get('email', '')).lower() or
                search_term.lower() in str(cred.get('phone', '')).lower() or
                search_term.lower() in str(cred.get('creation_date', '')).lower() or
                search_term.lower() in str(cred.get('profile', '')).lower()
            ]

            st.info(
                f"Encontradas {len(filtered_list)} contas contendo '{search_term}'")
            logging.info(
                f"Busca por '{search_term}' encontrou {len(filtered_list)} contas")

        # Mostrar as contas filtradas
        for idx, cred in enumerate(filtered_list):
            # Encontrar o índice original na lista completa
            original_idx = credentials_list.index(cred)

            creation_date = cred.get('creation_date', 'Data desconhecida')
            email = cred.get('email', 'N/A')
            telefone = cred.get('phone', 'N/A')
            profile = cred.get('profile', 'N/A')

            # Usar índice único para cada conta
            account_id = f"acc_{idx}"

            # Criar cabeçalho com botão de apagar
            col1, col2 = st.columns([5, 1])
            with col1:
                expander = st.expander(f"{email} - {creation_date}")
            with col2:
                if st.button("🗑️", key=f"delete_{account_id}", help="Apagar esta conta"):
                    success, message = delete_account(original_idx)
                    if success:
                        st.success(f"Conta {message} removida com sucesso!")
                        logging.info(f"Conta {message} removida com sucesso")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Erro ao remover conta: {message}")
                        logging.error(f"Erro ao remover conta: {message}")

            # Conteúdo do expander
            with expander:
                # Informações da conta em um formato mais organizado
                st.markdown(f"""
                | Detalhes da Conta | |
                |----------------|--------------|
                | **Email:** | `{email}` |
                | **Senha:** | `{cred.get('password', 'N/A')}` |
                | **Telefone:** | `{telefone}` |
                | **País:** | `{cred.get('country_name', 'N/A')}` |
                | **ID de Ativação:** | `{cred.get('activation_id', 'N/A')}` |
                | **Nome:** | `{cred.get('first_name', 'N/A')} {cred.get('last_name', 'N/A')}` |
                | **Perfil:** | `{profile}` |
                | **Data de Criação:** | `{creation_date}` |
                """)

                # Adicionar botões para copiar email/senha com chaves únicas baseadas no índice
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"📋 Copiar Email", key=f"copy_email_{account_id}"):
                        st.code(email, language=None)
                        st.info("Email copiado para a área de transferência")
                        logging.info(
                            f"Email {email} copiado para a área de transferência")
                with col2:
                    if st.button(f"📋 Copiar Senha", key=f"copy_senha_{account_id}"):
                        st.code(cred.get('password', ''), language=None)
                        st.info("Senha copiada para a área de transferência")
                        logging.info(
                            f"Senha para {email} copiada para a área de transferência")
    else:
        st.warning("⚠️ Nenhuma conta de Gmail encontrada.")
        logging.warning("Nenhuma conta de Gmail encontrada")

# **ABA 4 - GERENCIAR NÚMEROS**
elif st.session_state.current_page == "📱 Gerenciar Números":
    st.title("📱 Gerenciamento de Números de Telefone")
    logging.info("Acessando aba de Gerenciamento de Números")

    # Carregar todos os números disponíveis
    números = phone_manager._load_numbers()

    if not números:
        st.warning("⚠️ Nenhum número de telefone disponível para gerenciamento.")
        logging.info("Nenhum número de telefone disponível para gerenciamento")
    else:
        # Mostrar estatísticas básicas
        st.subheader("📊 Estatísticas de Números")
        stats = phone_manager.get_stats()
        logging.info(f"Estatísticas de números: {stats}")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Números", stats["total_numbers"])
        with col2:
            st.metric("Números Ativos", stats["active_numbers"])
        with col3:
            st.metric("Economia Estimada", stats["estimated_savings"])

        # Listar todos os números com detalhes
        st.subheader("📋 Lista de Números")

        # Adicionar busca
        search_number = st.text_input(
            "🔍 Filtrar por número", placeholder="Digite parte do número...")

        # Filtrar números
        filtered_numbers = números
        if search_number:
            filtered_numbers = [
                n for n in números if search_number in n.get("phone_number", "")]
            st.info(
                f"Encontrados {len(filtered_numbers)} números contendo '{search_number}'")
            logging.info(
                f"Busca por '{search_number}' encontrou {len(filtered_numbers)} números")

        # Mostrar os números disponíveis
        for i, número in enumerate(filtered_numbers):
            phone = número.get("phone_number", "N/A")
            country = número.get("country_code", "N/A")
            first_used = datetime.fromtimestamp(número.get("first_used", 0))
            last_used = datetime.fromtimestamp(número.get("last_used", 0))
            services = número.get("services", [])
            times_used = número.get("times_used", 0)

            # Verificar se o número ainda está ativo
            now = time.time()
            time_since_first_use = now - número.get("first_used", 0)
            is_active = time_since_first_use < phone_manager.reuse_window

            # Calcular tempo restante se estiver ativo
            time_left = ""
            if is_active:
                remaining_seconds = phone_manager.reuse_window - time_since_first_use
                minutes = int(remaining_seconds // 60)
                seconds = int(remaining_seconds % 60)
                time_left = f"{minutes}m {seconds}s"

            # Criar um card para o número
            status_color = "green" if is_active else "gray"
            status_text = "Ativo" if is_active else "Expirado"

            with st.expander(f"☎️ {phone} - {status_text} {'(' + time_left + ')' if time_left else ''}"):
                st.markdown(f"""
                | Detalhes do Número | |
                |----------------|--------------|
                | **Número:** | `{phone}` |
                | **País:** | `{country}` |
                | **Status:** | <span style='color:{status_color}'>{status_text}</span> |
                | **Tempo restante:** | {time_left if is_active else "Expirado"} |
                | **ID de Ativação:** | `{número.get('activation_id', 'N/A')}` |
                | **Primeira Utilização:** | {first_used.strftime('%Y-%m-%d %H:%M:%S')} |
                | **Última Utilização:** | {last_used.strftime('%Y-%m-%d %H:%M:%S')} |
                | **Serviços Utilizados:** | {', '.join(services)} |
                | **Vezes Utilizado:** | {times_used} |
                """, unsafe_allow_html=True)

                # Adicionar botão para remover número
                if st.button("🗑️ Remover Número", key=f"remove_number_{i}"):
                    try:
                        # Implementar lógica para remover o número
                        phone_manager.remove_number(phone)
                        st.success(f"✅ Número {phone} removido com sucesso!")
                        logging.info(f"Número {phone} removido com sucesso")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro ao remover número: {str(e)}")
                        logging.error(
                            f"Erro ao remover número {phone}: {str(e)}")

