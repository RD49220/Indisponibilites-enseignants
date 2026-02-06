import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ---------------- CONFIG ---------------- #
st.set_page_config(page_title="Indisponibilités enseignants", layout="wide")

# ---------------- CONSTANTES ---------------- #
JOURS = {
    "Lundi": "LUN",
    "Mardi": "MAR",
    "Mercredi": "MER",
    "Jeudi": "JEU",
    "Vendredi": "VEN",
}

CRENEAUX = {
    "8h-9h30": 1,
    "9h30-11h": 2,
    "11h-12h30": 3,
    "13h30-15h": 5,
    "15h-16h30": 6,
    "16h30-18h": 7,
}

# Créneaux étendus
CRENEAUX_EXT = {
    "Matin": [1, 2, 3],
    "Après-midi": [5, 6, 7],
}

# ---------------- GOOGLE SHEET ---------------- #
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

sheet = client.open("Indisponibilites_enseignants").sheet1

# ---------------- SESSION STATE ---------------- #
for k in [
    "enseignant_sel", "semaine_sel", "jour_sel", "creneau_sel",
    "raison_sel", "commentaire_global", "creneaux"
]:
    if k not in st.session_state:
        st.session_state[k] = "" if k != "creneaux" else []

# ---------------- ENSEIGNANT ---------------- #
enseignant = st.selectbox(
    "Code enseignant",
    ["", "ENS_AAA", "ENS_BBB", "ENS_CCC"],
    key="enseignant_sel"
)

# Reset champs si changement enseignant
if st.session_state.get("enseignant_prev") != enseignant:
    st.session_state.semaine_sel = ""
    st.session_state.jour_sel = ""
    st.session_state.creneau_sel = ""
    st.session_state.raison_sel = ""
    st.session_state.creneaux = []
    st.session_state.enseignant_prev = enseignant

# ---------------- MESSAGE EXISTANT ---------------- #
if enseignant:
    data = sheet.get_all_values()[1:]
    rows_user = [r for r in data if r and r[0] == enseignant]

    if rows_user:
        last_ts = rows_user[-1][8]
        st.warning(
            f"⚠️ Des indisponibilités sont déjà enregistrées pour vous.\n\n"
            f"Toute modification (ajout ou suppression) effacera les anciennes données lors de l'enregistrement.\n\n"
            f"Dernière modification effectuée le : {last_ts}"
        )

# ---------------- SELECTION CRENEAU ---------------- #
c1, c2, c3, c4 = st.columns(4)

with c1:
    semaine = st.selectbox("Semaine", [""] + list(range(1, 53)), key="semaine_sel")
with c2:
    jour = st.selectbox("Jour", [""] + list(JOURS.keys()), key="jour_sel")
with c3:
    creneau = st.selectbox(
        "Créneau",
        [""] + list(CRENEAUX_EXT.keys()) + list(CRENEAUX.keys()),
        key="creneau_sel"
    )
with c4:
    raison = st.text_area("Raisons / Commentaires", key="raison_sel", height=80)

# ---------------- AJOUT ---------------- #
if st.button("➕ Ajouter"):
    if not all([enseignant, semaine, jour, creneau]):
        st.error("Tous les champs doivent être renseignés.")
    else:
        jour_code = JOURS[jour]

        # Dépliage Matin / Après-midi
        if creneau in CRENEAUX_EXT:
            liste_creneaux = CRENEAUX_EXT[creneau]
        else:
            liste_creneaux = [CRENEAUX[creneau]]

        added = False

        for num in liste_creneaux:
            code_streamlit = f"{enseignant}_{jour_code}_{num}_P"

            # Anti doublon local
            if any(c["code"] == code_streamlit for c in st.session_state.creneaux):
                continue

            # Anti doublon Google Sheet
            if any(r[5] == code_streamlit for r in sheet.get_all_values()):
                continue

            st.session_state.creneaux.append({
                "semaine": semaine,
                "jour": jour,
                "creneau": num,
                "code": code_streamlit,
                "raison": raison
            })
            added = True

        if not added:
            st.warning("⚠️ Créneau déjà existant.")
        else:
            st.session_state.semaine_sel = ""
            st.session_state.jour_sel = ""
            st.session_state.creneau_sel = ""
            st.session_state.raison_sel = ""
            st.rerun()
            st.rerun()

# ---------------- TABLEAU ---------------- #
st.subheader("Récapitulatif")

for i, c in enumerate(st.session_state.creneaux):
    h1, h2, h3, h4, h5 = st.columns([1, 1, 1, 2, 0.5])

    h1.write(c["semaine"])
    h2.write(c["jour"])
    h3.write(c["creneau"])
    h4.write(c["raison"])

    if h5.button("🗑️", key=f"del_{i}"):
        st.session_state.creneaux.pop(i)
        st.rerun()
        st.rerun()

# ---------------- COMMENTAIRE GLOBAL ---------------- #
st.text_area("Commentaire global", key="commentaire_global", height=100)

# ---------------- ENREGISTRER ---------------- #
if st.button("💾 Enregistrer"):
    # Suppression anciennes données
    data = sheet.get_all_values()
    for idx in range(len(data) - 1, 0, -1):
        if data[idx][0] == enseignant:
            sheet.delete_rows(idx + 1)

    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")

    if not st.session_state.creneaux:
        sheet.append_row([
            enseignant, "", "", "", "",
            f"{enseignant}_0_P",
            "Aucune indisponibilité enregistrée",
            st.session_state.commentaire_global,
            timestamp
        ])
    else:
        for c in st.session_state.creneaux:
            sheet.append_row([
                enseignant,
                c["semaine"],
                c["jour"],
                c["creneau"],
                "",
                c["code"],
                c["raison"],
                st.session_state.commentaire_global,
                timestamp
            ])

    st.success("Enregistrement effectué.")
    st.session_state.creneaux = []
