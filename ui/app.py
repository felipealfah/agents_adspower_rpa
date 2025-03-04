import streamlit as st
import os
import sys
import time
import json
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 🔹 Adicionar o caminho correto do projeto antes das importações
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importações
from apis.sms_api import SMSAPI  
from automations.gmail_creator.core import GmailCreator
from automations.data_generator import generate_gmail_credentials
from powerads_api.profiles import get_profiles
from powerads_api.browser_manager import start_browser, stop_browser, get_active_browser_info, connect_selenium
from credentials.credentials_manager import load_credentials, add_or_update_api_key, delete_api_key, get_credential
from apis.phone_manager import PhoneManager
from powerads_api.ads_power_manager import AdsPowerManager

# 🔹 Caminho para salvar credenciais do Gmail
CREDENTIALS_PATH = "credentials/gmail.json"

# Inicializar estado da sessão para rastrear atualizações de credenciais
if 'last_credentials_update' not in st.session_state:
    st.session_state.last_credentials_update = time.time()

# Ativar recarregamento amplo na sessão para componentes gerenciados
if 'initialized' not in st.session_state:
    st.session_state.initialized = False
    st.session_state.active_profile = None

# Inicializar gerenciadores
phone_manager = PhoneManager()

# Função para recarregar configurações das APIs quando necessário
def refresh_api_configurations():
    """Recarrega as configurações das APIs a partir das credenciais mais recentes."""
    
    # Recarregar credenciais (usar cache interno do gerenciador)
    credentials = load_credentials()
    
    # Configurar cabeçalhos do AdsPower com base nas credenciais atualizadas
    pa_api_key = credentials.get("PA_API_KEY", None)
    pa_base_url = credentials.get("PA_BASE_URL", "http://local.adspower.net:50325")
    
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

# Obter configurações iniciais das APIs
api_config = refresh_api_configurations()
sms_api = api_config["sms_api"]
PA_BASE_URL = api_config["pa_base_url"]
HEADERS = api_config["pa_headers"]
adspower_manager = api_config["adspower_manager"]

# 🔹 Função para remover uma conta da lista
def delete_account(idx):
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
                
                return True, removed_account.get('email', 'Conta desconhecida')
            return False, "Índice inválido"
        return False, "Arquivo não encontrado"
    except Exception as e:
        return False, str(e)

# Função para limpar todas as contas
def clear_all_accounts():
    try:
        if os.path.exists(CREDENTIALS_PATH):
            with open(CREDENTIALS_PATH, "w") as file:
                json.dump([], file)
            return True
        return False
    except Exception as e:
        st.error(f"Erro ao limpar contas: {str(e)}")
        return False

# 🔹 Criar menu lateral no Streamlit
st.sidebar.title("🔧 Menu de Navegação")
aba_selecionada = st.sidebar.radio("Selecione uma opção:", 
                                 ["🔑 Gerenciar Credenciais", "📩 Automação Gmail", 
                                  "📊 Dashboard", "📱 Gerenciar Números"])

# Adicionar informações de saldo na barra lateral
try:
    sms_balance = sms_api.get_balance()
    if sms_balance is not None:
        saldo_color = "green" if sms_balance > 20 else "orange" if sms_balance > 5 else "red"
        st.sidebar.markdown(f"💰 **Saldo SMS:** <span style='color:{saldo_color}'>{sms_balance:.2f} RUB</span>", unsafe_allow_html=True)
    else:
        st.sidebar.warning("⚠️ Não foi possível obter o saldo SMS")
except:
    pass

# Adicionar status do AdsPower na barra lateral
if adspower_manager:
    api_health = adspower_manager.check_api_health()
    if api_health:
        st.sidebar.success("✅ AdsPower conectado")
    else:
        st.sidebar.error("❌ AdsPower não disponível")
else:
    st.sidebar.warning("⚠️ Chave de API do AdsPower não configurada")

# 🔹 **ABA 1 - GERENCIAMENTO DE CREDENCIAIS**
if aba_selecionada == "🔑 Gerenciar Credenciais":
    st.title("🔑 Gerenciamento de Credenciais")
    
    # Botão para recarregar credenciais manualmente (para debugging)
    if st.button("🔄 Recarregar Credenciais"):
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

    # 🔹 Formulário para adicionar/atualizar chave
    st.subheader("➕ Adicionar/Atualizar Chave de API")
    with st.form("add_key_form"):
        key_name = st.text_input("Nome da Chave (ex: PA_API_KEY)")
        key_value = st.text_input("Valor da Chave", type="password")
        submit_button = st.form_submit_button("💾 Salvar Chave")
        
        if submit_button:
            if key_name and key_value:
                if add_or_update_api_key(key_name, key_value):
                    st.session_state.last_credentials_update = time.time()
                    api_config = refresh_api_configurations()
                    sms_api = api_config["sms_api"]
                    PA_BASE_URL = api_config["pa_base_url"]
                    HEADERS = api_config["pa_headers"]
                    adspower_manager = api_config["adspower_manager"]
                    st.success(f"✅ Chave '{key_name}' adicionada/atualizada com sucesso!")
                else:
                    st.error("❌ Erro ao salvar a chave. Verifique os logs.")
            else:
                st.error("❌ Nome e valor da chave são obrigatórios.")

    # 🔹 Seção para excluir chave
    st.subheader("🗑️ Remover Chave de API")
    key_to_delete = st.selectbox("Selecione a chave para remover", options=list(credentials.keys()) if credentials else [])

    if st.button("🗑️ Excluir Chave"):
        if key_to_delete:
            if delete_api_key(key_to_delete):
                st.session_state.last_credentials_update = time.time()
                api_config = refresh_api_configurations()
                sms_api = api_config["sms_api"]
                PA_BASE_URL = api_config["pa_base_url"]
                HEADERS = api_config["pa_headers"]
                adspower_manager = api_config["adspower_manager"]
                st.success(f"✅ Chave '{key_to_delete}' removida com sucesso!")
            else:
                st.error("❌ Erro ao remover a chave. Verifique os logs.")
        else:
            st.warning("⚠️ Nenhuma chave selecionada.")

    # Mostrar informações sobre as APIs configuradas
    st.subheader("🔌 Status das APIs")
    
    # Status da API SMS
    sms_balance = None
    try:
        sms_balance = sms_api.get_balance()
        if sms_balance is not None:
            st.success(f"✅ API SMS conectada. Saldo: {sms_balance} RUB")
        else:
            st.error("❌ API SMS não conectada. Verifique sua chave de API.")
    except Exception as e:
        st.error(f"❌ Erro ao conectar à API SMS: {str(e)}")
    
    # Status da API AdsPower
    if HEADERS.get("Authorization"):
        try:
            # Tentar uma requisição simples para verificar conexão
            if adspower_manager:
                api_health = adspower_manager.check_api_health()
                if api_health:
                    profiles = adspower_manager.get_all_profiles()
                    st.success(f"✅ API AdsPower conectada. Total de perfis: {len(profiles)}")
                else:
                    st.warning("⚠️ API AdsPower não responde corretamente. Verifique a conexão.")
            else:
                st.warning("⚠️ Gerenciador AdsPower não inicializado.")
        except Exception as e:
            st.error(f"❌ Erro ao conectar à API AdsPower: {str(e)}")
    else:
        st.warning("⚠️ API AdsPower não configurada. Adicione a chave 'PA_API_KEY'.")


# 🔹 **ABA 2 - AUTOMAÇÃO GMAIL**
elif aba_selecionada == "📩 Automação Gmail":
    # Verificar se é necessário recarregar as configurações das APIs
    api_config = refresh_api_configurations()
    sms_api = api_config["sms_api"]
    PA_BASE_URL = api_config["pa_base_url"]
    HEADERS = api_config["pa_headers"]
    adspower_manager = api_config["adspower_manager"]
    
    st.title("📩 Automação no Gmail - Criar Conta")

    # 🔹 Listar perfis disponíveis no AdsPower
    profiles_list = []
    profile_options = {}
    
    try:
        if adspower_manager:
            # Verificar saúde da API
            if adspower_manager.check_api_health():
                profiles_list = adspower_manager.get_all_profiles()
                profile_options = {p["user_id"]: p["name"] for p in profiles_list}
            else:
                st.warning("⚠️ AdsPower API não está respondendo corretamente. Verifique a conexão.")
        else:
            # Fallback para o método antigo
            profiles_list = get_profiles(PA_BASE_URL, HEADERS) if HEADERS.get("Authorization") else []
            profile_options = {p["user_id"]: p["name"] for p in profiles_list} if profiles_list else {}

        if not profile_options:
            st.warning("⚠️ Nenhum perfil encontrado no AdsPower. Verifique suas credenciais.")

    except Exception as e:
        profile_options = {}
        st.error(f"Erro ao carregar perfis: {e}")

    # Verificar se há números de telefone reutilizáveis
    reusable_numbers = []
    try:
        for number in phone_manager._load_numbers():
            time_since_first_use = time.time() - number["first_used"]
            if time_since_first_use < phone_manager.reuse_window:
                # Converter tempo para minutos e segundos
                minutes_left = int((phone_manager.reuse_window - time_since_first_use) / 60)
                reusable_numbers.append(number)
        
        if reusable_numbers:
            st.info(f"♻️ {len(reusable_numbers)} números disponíveis para reutilização, economizando em custos SMS.")
    except Exception as e:
        st.error(f"Erro ao verificar números reutilizáveis: {e}")

    # UI para criação de contas
    if profile_options:
        # 🔹 Seleção do perfil
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

        # 🔥 Botão para iniciar a automação do Gmail
        if st.button("🚀 Criar Conta Gmail"):
            # Verificar se API SMS está configurada
            if not get_credential("SMS_ACTIVATE_API_KEY"):
                st.error("❌ API SMS não configurada. Adicione a chave 'SMS_ACTIVATE_API_KEY' primeiro.")
                st.stop()
                
            # Verificar saldo da API SMS
            sms_balance = sms_api.get_balance()
            if sms_balance is None or sms_balance <= 0:
                st.error(f"❌ Saldo insuficiente na API SMS. Saldo atual: {sms_balance} RUB")
                st.stop()
            
            st.write(f"🚀 Criando conta Gmail para o perfil: {profile_options[selected_profile]}")

            # Status para acompanhamento
            status_container = st.empty()
            status = status_container.status("Iniciando processo...")
            
            # 🔹 Se estamos usando o AdsPowerManager
            driver = None
            if adspower_manager:
                with status:
                    st.write("Iniciando navegador AdsPower...")
                    start_success, browser_info = adspower_manager.start_browser(selected_profile)
                    
                    if not start_success:
                        st.error("❌ Erro ao iniciar navegador AdsPower.")
                        status.update(label="Erro ao iniciar navegador", state="error")
                        st.stop()
                    
                    driver = adspower_manager.connect_selenium(browser_info)
                    if not driver:
                        st.error("❌ Erro ao conectar ao WebDriver.")
                        status.update(label="Erro ao conectar ao WebDriver", state="error")
                        st.stop()
            else:
                # Método tradicional (fallback)
                with status:
                    st.write("Iniciando navegador via API tradicional...")
                    start_browser(PA_BASE_URL, HEADERS, selected_profile)
                    time.sleep(5)

                    # Obter informações do navegador ativo
                    browser_info = get_active_browser_info(PA_BASE_URL, HEADERS, selected_profile)
                    if not browser_info or browser_info["status"] != "success":
                        st.error("❌ Erro ao obter informações do navegador ativo.")
                        status.update(label="Erro ao obter informações do navegador", state="error")
                        st.stop()

                    selenium_ws = browser_info["selenium_ws"]
                    webdriver_path = browser_info["webdriver_path"]

                    if not selenium_ws or not webdriver_path:
                        st.error("⚠️ WebSocket ou WebDriver não encontrados!")
                        status.update(label="WebSocket ou WebDriver não encontrados", state="error")
                        st.stop()

                    # Conectar ao WebDriver
                    driver = connect_selenium(selenium_ws, webdriver_path)
                    if not driver:
                        st.error("❌ Erro ao conectar ao WebDriver!")
                        status.update(label="Erro ao conectar ao WebDriver", state="error")
                        st.stop()
            
            status.update(label="Navegador iniciado. Gerando credenciais...", state="running")
            
            # 🔹 Gerar credenciais para a conta Gmail
            credentials = generate_gmail_credentials()
            
            # Configurar parâmetros para reutilização de números
            params = {}
            if use_existing_number and reusable_numbers:
                reusable_number = phone_manager.get_reusable_number(service="go")
                if reusable_number:
                    params = {
                        "reuse_number": True,
                        "phone_number": reusable_number["phone_number"],
                        "activation_id": reusable_number["activation_id"],
                        "country_code": reusable_number["country_code"]
                    }
                    status.update(label=f"Reutilizando número {reusable_number['phone_number']}...", state="running")

            # 🔹 Criar instância do Gmail Creator (passando o perfil do AdsPower)
            gmail_creator = GmailCreator(driver, credentials, sms_api, selected_profile)
            
            status.update(label="Iniciando criação de conta...", state="running")
            
            # 🔹 Iniciar automação e capturar progresso
            sucesso, account_data = gmail_creator.create_account(phone_params=params)
            
            # 🔥 Encerrar navegador após a automação
            if adspower_manager:
                adspower_manager.stop_browser(selected_profile)
            else:
                stop_browser(PA_BASE_URL, HEADERS, selected_profile)
            
            if sucesso and account_data:
                status.update(label="Conta criada com sucesso!", state="complete")
                st.success("✅ Conta Gmail criada com sucesso!")
                st.write(f"📧 **Email:** {account_data['email']} - 📱 **Telefone:** {account_data['phone']}")

                # Registrar número no PhoneManager para possível reutilização
                if not use_existing_number and 'phone' in account_data and 'activation_id' in account_data:
                    try:
                        phone_manager.add_number(
                            phone_number=account_data['phone'],
                            country_code=account_data.get('country_code', '0'),
                            activation_id=account_data['activation_id'],
                            service="go"
                        )
                        st.info("✅ Número registrado para possível reutilização.")
                    except Exception as e:
                        st.warning(f"⚠️ Não foi possível registrar o número para reutilização: {str(e)}")

                # 🔹 Salvar credenciais
                try:
                    existing_credentials = []
                    if os.path.exists(CREDENTIALS_PATH) and os.path.getsize(CREDENTIALS_PATH) > 0:
                        with open(CREDENTIALS_PATH, "r") as file:
                            existing_credentials = json.load(file)

                    # Adicionar timestamp de criação
                    account_data["creation_date"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    existing_credentials.append(account_data)

                    with open(CREDENTIALS_PATH, "w") as file:
                        json.dump(existing_credentials, file, indent=4)

                    st.success(f"📂 Credenciais salvas em `{CREDENTIALS_PATH}`")
                except Exception as e:
                    st.error(f"Erro ao salvar credenciais: {e}")

            else:
                status.update(label="Erro na criação da conta", state="error")
                st.error("❌ Erro na criação da conta.")

    # 🔹 Exibir contas criadas
    st.subheader("📜 Contas Criadas")
    
    # Carregar a lista de contas
    credentials_list = []
    if os.path.exists(CREDENTIALS_PATH) and os.path.getsize(CREDENTIALS_PATH) > 0:
        with open(CREDENTIALS_PATH, "r") as file:
            credentials_list = json.load(file)
    
    # Mostrar contagem e botão para limpar todas
    if credentials_list:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info(f"Total de contas: {len(credentials_list)}")
        with col2:
            if st.button("🗑️ Limpar Todas", help="Apagar todas as contas"):
                if st.checkbox("Confirmar exclusão de todas as contas", key="confirm_clear"):
                    if clear_all_accounts():
                        st.success("Todas as contas foram removidas com sucesso!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Erro ao remover todas as contas.")

    if credentials_list:
        # Adicionar campo de busca
        search_term = st.text_input("🔍 Buscar conta", placeholder="Digite email, telefone ou data")
        
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
            
            st.info(f"Encontradas {len(filtered_list)} contas contendo '{search_term}'")
        
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
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Erro ao remover conta: {message}")
            
            # Conteúdo do expander
            with expander:
                # Informações da conta em um formato mais organizado
                st.markdown(f"""
                | Detalhes da Conta | |
                |----------------|--------------|
                | **Email:** | `{email}` |
                | **Senha:** | `{cred.get('password', 'N/A')}` |
                | **Telefone:** | `{telefone}` |
                | **Perfil:** | `{profile}` |
                | **Data de Criação:** | `{creation_date}` |
                """)
                
                # Adicionar botões para copiar email/senha com chaves únicas baseadas no índice
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"📋 Copiar Email", key=f"copy_email_{account_id}"):
                        st.code(email, language=None)
                        st.info("Email copiado para a área de transferência")
                with col2:
                    if st.button(f"📋 Copiar Senha", key=f"copy_senha_{account_id}"):
                        st.code(cred.get('password', ''), language=None)
                        st.info("Senha copiada para a área de transferência")
    else:
        st.info("📝 Nenhuma conta criada ainda. Use a funcionalidade 'Criar Conta Gmail' para adicionar contas.")


# 🔹 **ABA 3 - DASHBOARD**
elif aba_selecionada == "📊 Dashboard":
    st.title("📊 Dashboard de Estatísticas")
    
    # Coletar dados das contas criadas
    accounts = []
    if os.path.exists(CREDENTIALS_PATH) and os.path.getsize(CREDENTIALS_PATH) > 0:
        try:
            with open(CREDENTIALS_PATH, "r") as file:
                accounts = json.load(file)
        except json.JSONDecodeError:
            st.error("❌ Erro ao carregar arquivo de contas. Formato inválido.")
    
    if not accounts:
        st.warning("⚠️ Nenhuma conta encontrada para gerar estatísticas.")
        st.stop()
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Contas", len(accounts))
    
    with col2:
        # Contas criadas nos últimos 7 dias
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        recent_accounts = 0
        
        for account in accounts:
            if "creation_date" in account:
                try:
                    creation_date = datetime.strptime(account["creation_date"], "%Y-%m-%d %H:%M:%S")
                    if creation_date > week_ago:
                        recent_accounts += 1
                except (ValueError, TypeError):
                    pass
        
        st.metric("Últimos 7 dias", recent_accounts)
    
    with col3:
        # Taxa de sucesso (se tivermos os dados necessários)
        # Aqui você precisaria de um log de tentativas
        st.metric("Telefones Reutilizados", len(phone_manager._load_numbers()))
    
    with col4:
        # Saldo da API SMS
        balance = sms_api.get_balance() or 0
        st.metric("Saldo SMS API", f"{balance:.2f} RUB")
    
    # Gráfico de criação ao longo do tempo
    st.subheader("📈 Criação de Contas ao Longo do Tempo")
    
    # Preparar dados para o gráfico
    date_counts = {}
    
    for account in accounts:
        if "creation_date" in account:
            try:
                date_str = account["creation_date"].split()[0]  # Apenas a data
                date_counts[date_str] = date_counts.get(date_str, 0) + 1
            except (AttributeError, IndexError):
                pass
    
    if date_counts:
        # Converter para DataFrame
        df_dates = pd.DataFrame({
            "Data": list(date_counts.keys()),
            "Contas": list(date_counts.values())
        })
        
        # Ordenar por data
        df_dates["Data"] = pd.to_datetime(df_dates["Data"])
        df_dates = df_dates.sort_values("Data")
        
        # Criar gráfico
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.bar(df_dates["Data"], df_dates["Contas"], color='#1f77b4')
        ax.set_xlabel("Data")
        ax.set_ylabel("Número de Contas")
        ax.set_title("Contas Criadas por Dia")
        
        # Adicionar rótulos de dados
        for i, v in enumerate(df_dates["Contas"]):
            ax.text(i, v + 0.1, str(v), ha='center')
            
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        st.pyplot(fig)
    else:
        st.info("Não há dados suficientes para gerar o gráfico de criação ao longo do tempo.")
    
    # Estatísticas de uso de telefone
    st.subheader("📱 Estatísticas de Uso de Números")