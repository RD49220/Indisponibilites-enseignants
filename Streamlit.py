import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# ==============================
# CONFIG
# ==============================

NOM_FICHIER = "Indisponibilites-enseignants"
ONGLET_DATA = "Feuille 1"
ONGLET_USERS = "Utilisateurs"

JOURS = {
    "Lundi": "LUN",
    "Mardi": "MAR",
    "Mercredi": "MER",
    "Jeudi": "JEU",
    "Vendredi": "VEN"
}

CRENEAUX = [
    "8h-9h30",
    "9h30-11h",
    "11h-12h30",
    "14h-15h30",
    "15h30-17h",
    "17h-18h30"
]

# ==============================
# AUTH GOOGLE
# ==============================

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

credentials = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES
)

client = gspread.authorize(credentials)

sheet = client.open(NOM_FICHIER).worksheet(ONGLET_DATA)
sheet_users = client.open(NOM_FICHIER).worksheet(ONGLET_USERS)

# ==============================
# CHARGEMENT UTILISATEURS
# ==============================

users_df = pd.DataFrame(sheet_users.get_all_records())

users_df["label"] = (
    users_df["Code"] + " (" +
    users_df["Nom"] + " " +
    users_df["Prenom"] + ")"
)

user_map = dict(zip(users_df["label"], users_df["Code"]))

# ==============================
# INTERFACE
# ==============================

st.set_page_config(page_title="Indisponibilités", layout="centered")
st.title("📅 Saisie des indisponibilités")

selected_label = st.selectbox(
    "Enseignant",
    options=users_df["label"].tolist()
)

user_code = user_map[selected_label]

st.divider()

# ==============================
# DONNÉES EXISTANTES
# ==============================

existing_rows = sheet.get_all_records()
existing_df = pd.DataFrame(existing_rows)

existing_user = existing_df[existing_df["Code"] == user_code]

existing_codes = set(existing_user["Code_creneau"]) if not existing_user.empty else set()

# ==============================
# SAISIE DES CRENEAUX
# ==============================

selected = []

for jour, jour_code in JOURS.items():
    st.subheader(jour)

    options = []
    default = []

    for i, c in enumerate(CRENEAUX, start=1):
        code = f"{jour_code}_{i}"
        options.append(c)
        if code in existing_codes:
            default.append(c)

    choix = st.multiselect(
        "Créneaux indisponibles",
        options,
        default=default,
        key=jour
    )

    for c in choix:
        idx = CRENEAUX.index(c) + 1
        selected.append((jour, jour_code, c, idx))

st.divider()

commentaire = st.text_area("💬 Commentaire (optionnel)")

# ==============================
# ENREGISTREMENT
# ==============================

if st.button("💾 Enregistrer"):
    if not selected:
        st.warning("Aucun créneau sélectionné.")
        st.stop()

    # --- confirmation si données existantes ---
    if not existing_user.empty:
        st.warning(
            "⚠️ Vous avez déjà enregistré des indisponibilités.\n\n"
            "Enregistrer à nouveau **écrasera les données précédentes**."
        )

        confirm = st.checkbox("Je confirme l’écrasement")

        if not confirm:
            st.stop()

        # suppression des anciennes lignes (de bas en haut)
        rows_to_delete = [
            i + 2
            for i, r in existing_df.iterrows()
            if r["Code"] == user_code
        ]

        for r in reversed(rows_to_delete):
            sheet.delete_rows(r)

    # --- ajout nouvelles lignes ---
    now = datetime.now().isoformat()

    rows = []
    for jour, jour_code, creneau, idx in selected:
        rows.append([
            user_code,
            jour,
            creneau,
            f"{jour_code}_{idx}",
            commentaire,
            now
        ])

    # entête si feuille vide
    if sheet.row_count == 0 or sheet.get_all_values() == []:
        sheet.append_row(
            ["Code", "Jour", "Créneau", "Code_creneau", "Commentaire", "Timestamp"]
        )

    sheet.append_rows(rows)

    st.success("✅ Indisponibilités enregistrées avec succès")
