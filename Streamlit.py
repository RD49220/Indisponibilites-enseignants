import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ======================
# CONFIG
# ======================
NOM_SHEET = "Indisponibilites-enseignants"
ONGLET_DONNEES = "Feuille 1"
ONGLET_USERS = "Utilisateurs"

JOURS = {
    "Lundi": "LUN",
    "Mardi": "MAR",
    "Mercredi": "MER",
    "Jeudi": "JEU",
    "Vendredi": "VEN"
}

CRENEAUX = {
    "1": "8h-9h30",
    "2": "9h30-11h",
    "3": "11h-12h30",
    "5": "14h-15h30",
    "6": "15h30-17h",
    "7": "17h-18h30"
}

# ======================
# AUTH GOOGLE SHEETS
# ======================
creds_dict = st.secrets["gcp_service_account"]

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
client = gspread.authorize(creds)

sheet = client.open(NOM_SHEET).worksheet(ONGLET_DONNEES)
users_sheet = client.open(NOM_SHEET).worksheet(ONGLET_USERS)

# ======================
# CHARGER UTILISATEURS
# ======================
users_data = users_sheet.get_all_values()[1:]  # skip header
users = [{"code": row[0], "nom": row[1], "prenom": row[2]} for row in users_data if row]

options = {f"{u['code']} – {u['nom']} {u['prenom']}": u["code"] for u in users}

# ======================
# SESSION STATE
# ======================
if "user_code" not in st.session_state:
    st.session_state.user_code = None
if "ponctuels" not in st.session_state:
    st.session_state.ponctuels = []

# ======================
# SELECTBOX UTILISATEUR
# ======================
selected_label = st.selectbox("Choisissez votre nom", options.keys())
if st.session_state.user_code != options[selected_label]:
    st.session_state.user_code = options[selected_label]
user_code = st.session_state.user_code

# ======================
# LECTURE DONNÉES EXISTANTES
# ======================
all_data = sheet.get_all_values()
user_rows = [row for row in all_data[1:] if row[0] == user_code]

existing_codes = set()
for row in user_rows:
    if len(row) > 3:
        existing_codes.add(row[3].strip())
existing_comment = user_rows[0][4] if user_rows and len(user_rows[0]) > 4 else ""
rows_to_delete = [i for i, row in enumerate(all_data[1:], start=2) if row[0] == user_code]

# ======================
# MESSAGE SI DÉJÀ ENREGISTRÉ
# ======================
if rows_to_delete:
    st.warning("⚠️ Vous avez déjà enregistré vos indisponibilités.")

# ======================
# FORMULAIRE
# ======================
with st.form(key=f"form_{user_code}"):

    selections = []

    # ======================
    # INDISPONIBILITÉS RÉGULIÈRES
    # ======================
    for jour, jour_code in JOURS.items():
        st.subheader(jour)
        cols = st.columns(3)
        for i, (num, label) in enumerate(CRENEAUX.items()):
            code_creneau = f"{jour_code}_{num}"
            code_cr_streamlit = f"{user_code}_{code_creneau}"  # nouvelle colonne
            key = f"{user_code}_{jour_code}_{num}"

            checked = code_creneau in existing_codes

            if cols[i % 3].checkbox(label, value=checked, key=key):
                selections.append([
                    user_code,
                    jour,
                    label,
                    code_creneau,
                    "",  # commentaire ajouté plus bas
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    code_cr_streamlit
                ])

    # ======================
    # CRENEAUX PONCTUELS MULTI-SÉLECTION
    # ======================
    st.subheader("📌 Créneaux ponctuels")

    semaines = st.multiselect("Numéros de semaine", list(range(1, 53)))
    jours_ponctuels = st.multiselect("Jours", list(JOURS.keys()))
    creneaux_ponctuels = st.multiselect("Créneaux", list(CRENEAUX.values()))

    submit_ponctuel = st.form_submit_button("➕ Ajouter ce(s) créneau(x) ponctuel(s)")
    if submit_ponctuel:
        for semaine in semaines:
            for jour_ponctuel in jours_ponctuels:
                for creneau_ponctuel in creneaux_ponctuels:
                    code_jour = JOURS[jour_ponctuel]
                    num_creneau = [k for k, v in CRENEAUX.items() if v == creneau_ponctuel][0]
                    code_cr_streamlit = f"{user_code}_{code_jour}_{num_creneau}_P"

                    st.session_state.ponctuels.append({
                        "Semaine": semaine,
                        "Jour": jour_ponctuel,
                        "Créneau": creneau_ponctuel,
                        "Code_cr_streamlit": code_cr_streamlit
                    })

    # Affichage dynamique des créneaux ponctuels ajoutés sans la colonne code_cr_streamlit
    if st.session_state.ponctuels:
        st.subheader("📝 Créneaux ponctuels ajoutés")
        df_display = [{k: v for k, v in row.items() if k != "Code_cr_streamlit"} for row in st.session_state.ponctuels]
        st.table(df_display)

    # ======================
    # COMMENTAIRE
    # ======================
    commentaire = st.text_area("💬 Commentaire", value=existing_comment, height=100)

    # ======================
    # CONFIRMATION ÉCRASEMENT
    # ======================
    confirm = False
    if rows_to_delete:
        confirm = st.checkbox("Je confirme l’écrasement des anciennes données")

    submit = st.form_submit_button("💾 Enregistrer / Écraser" if rows_to_delete else "💾 Enregistrer")

# ======================
# ENREGISTREMENT
# ======================
if submit:
    if not selections and not st.session_state.ponctuels:
        st.warning("Aucun créneau sélectionné.")
        st.stop()

    if rows_to_delete and not confirm:
        st.warning("Vous devez confirmer l’écrasement des anciennes données pour continuer.")
        st.stop()

    # suppression des anciennes lignes si nécessaire
    for row_index in sorted(rows_to_delete, reverse=True):
        sheet.delete_rows(row_index)

    # ajout des créneaux réguliers
    for row in selections:
        sheet.append_row([
            row[0],  # Code enseignant
            row[1],  # Jour
            row[2],  # Créneau
            row[3],  # Code créneau
            commentaire,  # Commentaire
            row[5],  # Timestamp
            row[6]   # code_cr_streamlit
        ])

    # ajout des créneaux ponctuels
    for row in st.session_state.ponctuels:
        code_jour, num_creneau = row["Code_cr_streamlit"].split("_")[1:3]
        sheet.append_row([
            user_code,
            f"{row['Jour']} (Semaine {row['Semaine']})",
            row['Créneau'],
            f"{code_jour}_{num_creneau}",
            "",  # commentaire vide pour ponctuel
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            row['Code_cr_streamlit']
        ])

    # vider la liste ponctuels après enregistrement
    st.session_state.ponctuels = []
    st.success("✅ Indisponibilités et créneaux ponctuels enregistrés avec succès")
