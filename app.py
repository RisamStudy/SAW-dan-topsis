import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime

# ==================================
# DATABASE
# ==================================

conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS criteria(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    weight REAL,
    type TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS alternatives(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS scores(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alternative_id INTEGER,
    criteria_id INTEGER,
    value REAL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS results(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    method TEXT,
    alternative TEXT,
    score REAL,
    ranking INTEGER,
    created_at TEXT
)
""")

conn.commit()

# ==================================
# HELPER
# ==================================

def get_criteria():
    return pd.read_sql("SELECT * FROM criteria", conn)

def get_alternatives():
    return pd.read_sql("SELECT * FROM alternatives", conn)

def get_scores():
    return pd.read_sql("SELECT * FROM scores", conn)

# ==================================
# SIDEBAR
# ==================================

st.sidebar.title("SPK SAW & TOPSIS")

menu = st.sidebar.radio(
    "Menu",
    [
        "Kriteria",
        "Alternatif",
        "Input Nilai",
        "SAW",
        "TOPSIS",
        "Riwayat"
    ]
)

# ==================================
# KRITERIA
# ==================================

if menu == "Kriteria":

    st.title("Data Kriteria")

    with st.form("form_kriteria"):
        nama = st.text_input("Nama Kriteria")
        bobot = st.number_input("Bobot", min_value=0.0)
        tipe = st.selectbox("Tipe", ["benefit", "cost"])

        submit = st.form_submit_button("Simpan")

        if submit:
            cursor.execute(
                "INSERT INTO criteria(name,weight,type) VALUES(?,?,?)",
                (nama,bobot,tipe)
            )
            conn.commit()
            st.success("Kriteria ditambahkan")

    st.dataframe(get_criteria())

# ==================================
# ALTERNATIF
# ==================================

elif menu == "Alternatif":

    st.title("Data Alternatif")

    with st.form("form_alt"):
        nama = st.text_input("Nama Alternatif")

        submit = st.form_submit_button("Simpan")

        if submit:
            cursor.execute(
                "INSERT INTO alternatives(name) VALUES(?)",
                (nama,)
            )
            conn.commit()

            st.success("Alternatif ditambahkan")

    st.dataframe(get_alternatives())

# ==================================
# INPUT NILAI
# ==================================

elif menu == "Input Nilai":

    st.title("Input Nilai")

    criteria = get_criteria()
    alternatives = get_alternatives()

    if len(criteria)==0 or len(alternatives)==0:
        st.warning("Isi kriteria dan alternatif terlebih dahulu")
    else:

        alt = st.selectbox(
            "Alternatif",
            alternatives["name"]
        )

        alt_id = alternatives[
            alternatives["name"]==alt
        ]["id"].iloc[0]

        for _, row in criteria.iterrows():

            nilai = st.number_input(
                f"{row['name']}",
                min_value=0.0,
                key=row["id"]
            )

            if st.button(
                f"Simpan {row['name']}",
                key=f"btn{row['id']}"
            ):

                cursor.execute("""
                INSERT INTO scores(
                alternative_id,
                criteria_id,
                value
                )
                VALUES(?,?,?)
                """,
                (
                    alt_id,
                    row["id"],
                    nilai
                ))

                conn.commit()

                st.success("Tersimpan")

# ==================================
# SAW
# ==================================

elif menu == "SAW":

    st.title("Metode SAW")

    criteria = get_criteria()
    alternatives = get_alternatives()
    scores = get_scores()

    if len(scores)==0:
        st.warning("Belum ada data")
    else:

        matrix = scores.pivot_table(
            index="alternative_id",
            columns="criteria_id",
            values="value",
            aggfunc="last"
        )

        norm = matrix.copy()

        for i,row in criteria.iterrows():

            cid = row["id"]

            if row["type"]=="benefit":
                norm[cid] = matrix[cid] / matrix[cid].max()
            else:
                norm[cid] = matrix[cid].min() / matrix[cid]

        weights = criteria["weight"].values

        result = norm * weights

        final = result.sum(axis=1)

        ranking = pd.DataFrame({
            "alternative_id": final.index,
            "score": final.values
        })

        ranking = ranking.sort_values(
            by="score",
            ascending=False
        )

        ranking["ranking"] = range(
            1,
            len(ranking)+1
        )

        ranking = ranking.merge(
            alternatives,
            left_on="alternative_id",
            right_on="id"
        )

        st.dataframe(
            ranking[[
                "name",
                "score",
                "ranking"
            ]]
        )

        if st.button("Simpan Hasil SAW"):

            for _, row in ranking.iterrows():

                cursor.execute("""
                INSERT INTO results(
                method,
                alternative,
                score,
                ranking,
                created_at
                )
                VALUES(?,?,?,?,?)
                """,
                (
                    "SAW",
                    row["name"],
                    float(row["score"]),
                    int(row["ranking"]),
                    datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                ))

            conn.commit()

            st.success("Hasil disimpan")

# ==================================
# TOPSIS
# ==================================

elif menu == "TOPSIS":

    st.title("Metode TOPSIS")

    criteria = get_criteria()
    alternatives = get_alternatives()
    scores = get_scores()

    if len(scores)==0:
        st.warning("Belum ada data")
    else:

        matrix = scores.pivot_table(
            index="alternative_id",
            columns="criteria_id",
            values="value",
            aggfunc="last"
        )

        r = matrix / np.sqrt(
            (matrix**2).sum()
        )

        weights = criteria["weight"].values

        y = r * weights

        ideal_plus = []
        ideal_minus = []

        for _, row in criteria.iterrows():

            cid = row["id"]

            if row["type"]=="benefit":

                ideal_plus.append(
                    y[cid].max()
                )

                ideal_minus.append(
                    y[cid].min()
                )

            else:

                ideal_plus.append(
                    y[cid].min()
                )

                ideal_minus.append(
                    y[cid].max()
                )

        ideal_plus = np.array(
            ideal_plus
        )

        ideal_minus = np.array(
            ideal_minus
        )

        d_plus = np.sqrt(
            ((y-ideal_plus)**2).sum(axis=1)
        )

        d_minus = np.sqrt(
            ((y-ideal_minus)**2).sum(axis=1)
        )

        pref = d_minus / (
            d_plus + d_minus
        )

        ranking = pd.DataFrame({
            "alternative_id": matrix.index,
            "score": pref
        })

        ranking = ranking.sort_values(
            by="score",
            ascending=False
        )

        ranking["ranking"] = range(
            1,
            len(ranking)+1
        )

        ranking = ranking.merge(
            alternatives,
            left_on="alternative_id",
            right_on="id"
        )

        st.dataframe(
            ranking[
                ["name","score","ranking"]
            ]
        )

        if st.button("Simpan Hasil TOPSIS"):

            for _, row in ranking.iterrows():

                cursor.execute("""
                INSERT INTO results(
                method,
                alternative,
                score,
                ranking,
                created_at
                )
                VALUES(?,?,?,?,?)
                """,
                (
                    "TOPSIS",
                    row["name"],
                    float(row["score"]),
                    int(row["ranking"]),
                    datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                ))

            conn.commit()

            st.success("Hasil disimpan")

# ==================================
# RIWAYAT
# ==================================

elif menu == "Riwayat":

    st.title("Riwayat Perhitungan")

    data = pd.read_sql(
        "SELECT * FROM results ORDER BY id DESC",
        conn
    )

    st.dataframe(data)