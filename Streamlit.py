import streamlit as st
import pandas as pd
from datetime import datetime
import uuid
import gspread
from google.oauth2.service_account import Credentials

# ----------------------------
# CONFIG
# ----------------------------
st.set_page_config(page_title="Indisponibilités enseignants", layout="wide")

CRENEAUX = {
    "1": "8h-9h30",
    "2": "9h30-11h",
    "3": "11h-12h30",
    "5": "14h-15h30",
    "6": "15h30-17h",
    "7": "17h-18h30"
}

JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]
SEMAINES = list(range(1, 53))

# ----------------------------
# GOOGLE SHEETS
# ----------------------------
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES
)
gc = gspread.authorize(creds)
sheet = gc.open_by_key(st.secrets["spreadsheet_id"]).sheet1

# ----------------------------
# SESSION STATE
# ----------------------------
if "ponctuels" not in st.session_state:
    st.session_state.ponctuels = []

# ----------------------------
# UI
# ----------------------------
st.title("Déclaration des indisponibilités")

user_code = st.text_input("Code enseignant")

st.subheader("Créneaux ponctuels")

col1, col2, col3, col4 = st.columns(4)

with col1:
    semaines_sel = st.multiselect("Semaine(s)", SEMAINES)

with col2:
    jours_sel = st.multiselect("Jour(s)", JOURS)

with col3:
    creneaux_sel = st.multiselect(
        "Créneau(x)",
        list(CRENEAUX.keys()),
        format_func=lambda x: f"{x} – {CRENEAUX[x]}"
    )

with col4:
    if st.button("➕ Ajouter"):
        for s in semaines_sel:
            for j in jours_sel:
                for c in creneaux_sel:
                    st.session_state.ponctuels.append({
                        "semaine": s,
                        "jour": j,
                        "creneau": CRENEAUX[c],
                        "code_creneau": c,
                        "code_streamlit": str(uuid.uuid4())
                    })

# ----------------------------
# TABLEAU COMPACT
# ----------------------------
if st.session_state.ponctuels:
    st.markdown("### Créneaux ajoutés")

    for idx, row in enumerate(st.session_state.ponctuels):
        c1, c2, c3, c4 = st.columns([1, 2, 3, 0.5])

        c1.write(row["semaine"])
        c2.write(row["jour"])
        c3.write(row["creneau"])

        if c4.button("🗑️", key=f"del_{idx}"):
            st.session_state.ponctuels.pop(idx)
            st.rerun()

# ----------------------------
# COMMENTAIRE
# ----------------------------
commentaire = st.text_area("Commentaire")

# ----------------------------
# ENREGISTREMENT
# ----------------------------
if st.button("💾 Enregistrer"):
    if not user_code:
        st.error("Code enseignant obligatoire")
    else:
        for p in st.session_state.ponctuels:
            sheet.append_row(
                [
                    user_code,                     # A Code enseignant
                    p["semaine"],                  # B Semaine
                    p["jour"],                     # C Jour
                    p["creneau"],                  # D Créneau
                    p["code_creneau"],             # E Code créneau
                    p["code_streamlit"],            # F Code streamlit
                    commentaire,                   # G Commentaire
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # H Timestamp
                ],
                value_input_option="RAW"
            )

        st.success("Indisponibilités enregistrées")
        st.session_state.ponctuels = []
