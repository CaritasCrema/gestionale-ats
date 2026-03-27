import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="ATS Connessioni 2.0 - Rendicontazione", layout="wide")

# --- CONNESSIONE GOOGLE SHEETS ---
def get_gsheet_client():
    # Carica le credenziali dai "Secrets" di Streamlit Cloud per la sicurezza online
    creds_dict = st.secrets["gcp_service_account"]
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

def load_data(sheet_name, worksheet_name):
    client = get_gsheet_client()
    sh = client.open(sheet_name)
    worksheet = sh.worksheet(worksheet_name)
    return pd.DataFrame(worksheet.get_all_records())

# --- LOGICA COSTI PERSONALE (Dati da Quadro Logico) ---
COSTI_ORARI = {
    "Fondazione Madeo": {"Educatore/Amm": 21.84, "Tutor": 25.73},
    "Servizi per l'accoglienza": {"Educatore/Amm": 21.84, "Tutor": 25.73},
    "Mestieri Lombardia": {"Educatore/Amm": 21.84, "Tutor": 25.73},
    # Aggiungi qui gli altri partner se hanno costi diversi
}

# --- INTERFACCIA ---
st.sidebar.image("https://raw.githubusercontent.com/tuo-account/tuo-repo/main/logo.jpg", width=150) # Inserire URL reale logo
st.title("Gestione Rendicontazione ATS Connessioni 2.0")

# --- SISTEMA DI LOGIN ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    with st.container():
        st.subheader("Accedi al portale")
        user = st.selectbox("Seleziona il tuo Ente", ["Fondazione Madeo", "Arci Porto Sicuro", "Mestieri Lombardia", "Servizi per l'accoglienza", "Comunita' Papa Giovanni XXIII"])
        pwd = st.text_input("Password", type="password")
        if st.button("Accedi"):
            if pwd == "crema2026": # Imposta una password provvisoria
                st.session_state.auth = True
                st.session_state.user = user
                st.rerun()
else:
    ente_loggato = st.session_state.user
    is_admin = (ente_loggato == "Fondazione Madeo")
    
    tab1, tab2, tab3 = st.tabs(["➕ Inserimento Spese", "📊 Riepilogo Consuntivo", "⚙️ Amministrazione"])

    # --- TAB 1: INSERIMENTO ---
    with tab1:
        st.header(f"Nuova registrazione per: {ente_loggato}")
        with st.form("form_spese"):
            col1, col2 = st.columns(2)
            with col1:
                data = st.date_input("Data documento", datetime.now())
                area = st.selectbox("Area", ["Area 1 - Accoglienze", "Area 2 - Prossimità", "Area 3 - Patti", "Area 4 - Sistema"])
                azione = st.text_input("Codice Azione (es: 1.1, 3.1)")
            with col2:
                tipo = st.selectbox("Tipologia", ["Personale", "Acquisti", "Prestazioni Terzi"])
                desc = st.text_input("Descrizione spesa")
                
                if tipo == "Personale":
                    ore = st.number_input("Numero di ore lavorate", min_value=0.0)
                    tariffa = COSTI_ORARI.get(ente_loggato, {"Educatore/Amm": 21.84})["Educatore/Amm"]
                    importo = ore * tariffa
                    st.info(f"Costo calcolato automaticamente: {importo:.2f}€ (Tariffa: {tariffa}€/h)")
                else:
                    importo = st.number_input("Importo Fattura/Ricevuta (€)", min_value=0.0)

            if st.form_submit_button("Invia Rendicontazione"):
                client = get_gsheet_client()
                sh = client.open("Rendicontazione_ATS").worksheet("Spese")
                sh.append_row([str(data), ente_loggato, area, azione, tipo, desc, importo])
                st.success("Spesa registrata con successo!")

    # --- TAB 2: MONITORAGGIO & ALERT ---
    with tab2:
        st.header("Stato Avanzamento Lavori")
        df_spese = load_data("Rendicontazione_ATS", "Spese")
        
        # Filtro per l'utente corrente o visione totale per admin
        view_df = df_spese if is_admin else df_spese[df_spese['Ente'] == ente_loggato]
        st.dataframe(view_df, use_container_width=True)
        
        # Esempio di Alert Budget (Logica semplificata)
        tot_speso = view_df['Importo'].sum()
        st.metric("Totale Speso ad oggi", f"€ {tot_speso:,.2f}")
        
        if is_admin:
            st.warning("⚠️ ALERT: L'azione 1.1 ha raggiunto l'85% del budget disponibile!")

    # --- TAB 3: ESPORTAZIONE ---
    with tab3:
        st.header("Esportazione Dati")
        if is_admin:
            st.write("Scarica il quadro logico aggiornato per il Comune di Crema.")
            csv = df_spese.to_csv(index=False).encode('utf-8')
            st.download_button("Genera Report Preconsuntivo (CSV)", csv, "consuntivo_ats.csv", "text/csv")
        else:
            st.info("Funzione riservata al Capofila (Fondazione Madeo).")