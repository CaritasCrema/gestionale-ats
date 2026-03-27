import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="ATS Connessioni 2.0", layout="wide")

# Funzione per connettersi a Google Sheets usando i "Secrets" di Streamlit
def get_gsheet_client():
    creds_info = st.secrets["gcp_service_account"]
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
    return gspread.authorize(creds)

# --- DATI E LOGICA ---
PARTNER_LIST = [
    "Fondazione Madeo", "Arci Porto Sicuro", "Mestieri Lombardia", 
    "Comunita' Papa Giovanni XXIII", "Meraki", "Servizi Per L’accoglienza", 
    "Bessimo", "Koala", "Igea", "Le Orme"
]

# Tariffe orarie estratte dal Quadro Logico
TARIFFE = {
    "Educatore/Amm": 21.84,
    "Tutor": 25.73,
    "Coordinatore": 30.50 # Valore stimato, puoi variarlo nel codice
}

# --- INTERFACCIA ---
st.title("💻 Sistema Rendicontazione ATS Connessioni 2.0")
st.markdown("---")

# Login Semplice
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.subheader("Accedi al Portale")
        user = st.selectbox("Seleziona il tuo Ente", PARTNER_LIST)
        password = st.text_input("Password", type="password")
        if st.button("Entra"):
            if password == "crema2026": # Password provvisoria per tutti
                st.session_state.authenticated = True
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Password errata")
else:
    user = st.session_state.user
    st.sidebar.write(f"Utente: **{user}**")
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()

    menu = st.sidebar.radio("Navigazione", ["Inserimento Spese", "Dashboard Monitoraggio", "Esporta Dati"])

    # --- 1. INSERIMENTO SPESE ---
    if menu == "Inserimento Spese":
        st.header(f"Nuova Registrazione - {user}")
        
        with st.form("form_inserimento"):
            c1, c2 = st.columns(2)
            with c1:
                data = st.date_input("Data Spesa", datetime.now())
                area = st.selectbox("Area Intervento", ["Area 1 - Accoglienze", "Area 2 - Prossimità", "Area 3 - Patti", "Area 4 - Sistema"])
                azione = st.text_input("Azione (es: 1.1, 2.2, 3.1)")
            with c2:
                tipo = st.selectbox("Tipologia Spesa", ["Personale", "Acquisti", "Prestazioni Terzi"])
                descrizione = st.text_input("Descrizione (es. Ore educatore Marzo, Fattura materiale...)")
                
                if tipo == "Personale":
                    profilo = st.selectbox("Profilo Professionale", list(TARIFFE.keys()))
                    ore = st.number_input("Numero Ore", min_value=0.1, step=0.5)
                    importo = round(ore * TARIFFE[profilo], 2)
                    st.warning(f"Costo calcolato: € {importo}")
                else:
                    importo = st.number_input("Importo Totale (€)", min_value=0.0)

            if st.form_submit_button("Salva Spesa"):
                try:
                    client = get_gsheet_client()
                    sheet = client.open("Rendicontazione_ATS").worksheet("Spese")
                    sheet.append_row([str(data), user, area, azione, tipo, descrizione, importo])
                    st.success("Spesa salvata correttamente su Google Sheets!")
                except Exception as e:
                    st.error(f"Errore nel salvataggio: {e}")

    # --- 2. DASHBOARD ---
    elif menu == "Dashboard Monitoraggio":
        st.header("Stato Avanzamento Budget")
        
        # Caricamento dati
        try:
            df = pd.DataFrame(get_gsheet_client().open("Rendicontazione_ATS").worksheet("Spese").get_all_records())
            
            if not df.empty:
                # Se non è admin, vede solo i suoi
                if user != "Fondazione Madeo":
                    df = df[df['Ente'] == user]
                
                total_speso = df['Importo'].sum()
                st.metric("Totale Speso Corrente", f"€ {total_speso:,.2f}")
                
                st.subheader("Dettaglio per Azione")
                progresso_azioni = df.groupby('Azione')['Importo'].sum()
                st.bar_chart(progresso_azioni)
                
                # Tabella riassuntiva
                st.dataframe(df, use_container_width=True)
            else:
                st.info("Nessuna spesa inserita al momento.")
        except:
            st.error("Assicurati che il foglio 'Spese' su Google Sheets non sia vuoto e abbia le intestazioni corrette.")

    # --- 3. ESPORTAZIONE ---
    elif menu == "Esporta Dati":
        st.header("Download Rendicontazione")
        df = pd.DataFrame(get_gsheet_client().open("Rendicontazione_ATS").worksheet("Spese").get_all_records())
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Scarica Quadro Consuntivo (CSV)",
            data=csv,
            file_name=f"rendicontazione_ats_{datetime.now().strftime('%Y%m%d')}.csv",
            mime='text/csv',
        )
