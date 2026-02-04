import streamlit as st
import pandas as pd
from datetime import datetime
import os

# ==============================
# CONFIGURATION
# ==============================

JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]

CRENEAUX = [
    "8h-9h30",
    "9h30-11h",
    "11h-12h30",
    "14h-15h30",
    "15h30-17h",
    "17h-18h30"
]

FICHIER = "indisponibilites.csv"

# ==============================
# INTERFACE
# ==============================

st.set_page_config(page_title="Indisponibilités", layout="centered")

st.title("📅 Saisie des indisponibilités")
st.write("Cochez les créneaux où vous êtes **indisponible** puis cliquez sur **Enregistrer**.")

user = st.text_input("Vos initiales / votre nom")

st.divider()

selections = []

for jour in JOURS:
    st.subheader(jour)
    cols = st.columns(3)
    for i, creneau in enumerate(CRENEAUX):
        if cols[i % 3].checkbox(creneau, key=f"{jour}_{creneau}"):
            selections.append({
                "utilisateur": user,
                "jour": jour,
                "creneau": creneau,
                "timestamp": datetime.now().isoformat()
            })

st.divider()

# ==============================
# ENREGISTREMENT
# ==============================

if st.button("💾 Enregistrer"):
    if not user:
        st.error("Merci d’indiquer votre nom ou vos initiales.")
    elif not selections:
        st.warning("Aucun créneau sélectionné.")
    else:
        df_new = pd.DataFrame(selections)

        if os.path.exists(FICHIER):
            df_old = pd.read_csv(FICHIER)
            df = pd.concat([df_old, df_new], ignore_index=True)
        else:
            df = df_new

        df.to_csv(FICHIER, index=False)
        st.success("✅ Vos indisponibilités ont été enregistrées.")
