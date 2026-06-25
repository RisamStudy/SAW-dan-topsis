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

    # Tambah
    with st.form("form_kriteria"):
        nama = st.text_input("Nama Kriteria")
        bobot = st.number_input("Bobot", min_value=0.0)
        tipe = st.selectbox("Tipe", ["benefit", "cost"])
        submit = st.form_submit_button("Tambah")
        if submit and nama:
            cursor.execute(
                "INSERT INTO criteria(name,weight,type) VALUES(?,?,?)",
                (nama, bobot, tipe)
            )
            conn.commit()
            st.success("Kriteria ditambahkan")
            st.rerun()

    st.divider()

    criteria = get_criteria()
    st.subheader("Daftar Kriteria")

    if len(criteria) == 0:
        st.info("Belum ada data kriteria")
    else:
        for _, row in criteria.iterrows():
            with st.expander(f"{row['name']} | Bobot: {row['weight']} | Tipe: {row['type']}"):
                with st.form(f"edit_kriteria_{row['id']}"):
                    new_name = st.text_input("Nama", value=row["name"])
                    new_bobot = st.number_input("Bobot", min_value=0.0, value=float(row["weight"]))
                    new_tipe = st.selectbox("Tipe", ["benefit", "cost"],
                                            index=0 if row["type"] == "benefit" else 1)
                    col1, col2 = st.columns(2)
                    with col1:
                        update = st.form_submit_button("Update")
                    with col2:
                        delete = st.form_submit_button("Hapus", type="primary")

                if update:
                    cursor.execute(
                        "UPDATE criteria SET name=?, weight=?, type=? WHERE id=?",
                        (new_name, new_bobot, new_tipe, row["id"])
                    )
                    conn.commit()
                    st.success("Kriteria diperbarui")
                    st.rerun()

                if delete:
                    cursor.execute("DELETE FROM criteria WHERE id=?", (row["id"],))
                    cursor.execute("DELETE FROM scores WHERE criteria_id=?", (row["id"],))
                    conn.commit()
                    st.success("Kriteria dihapus")
                    st.rerun()

# ==================================
# ALTERNATIF
# ==================================

elif menu == "Alternatif":

    st.title("Data Alternatif")

    # Tambah
    with st.form("form_alt"):
        nama = st.text_input("Nama Alternatif")
        submit = st.form_submit_button("Tambah")
        if submit and nama:
            cursor.execute(
                "INSERT INTO alternatives(name) VALUES(?)",
                (nama,)
            )
            conn.commit()
            st.success("Alternatif ditambahkan")
            st.rerun()

    st.divider()

    alternatives = get_alternatives()
    st.subheader("Daftar Alternatif")

    if len(alternatives) == 0:
        st.info("Belum ada data alternatif")
    else:
        for _, row in alternatives.iterrows():
            with st.expander(f"{row['name']}"):
                with st.form(f"edit_alt_{row['id']}"):
                    new_name = st.text_input("Nama", value=row["name"])
                    col1, col2 = st.columns(2)
                    with col1:
                        update = st.form_submit_button("Update")
                    with col2:
                        delete = st.form_submit_button("Hapus", type="primary")

                if update:
                    cursor.execute(
                        "UPDATE alternatives SET name=? WHERE id=?",
                        (new_name, row["id"])
                    )
                    conn.commit()
                    st.success("Alternatif diperbarui")
                    st.rerun()

                if delete:
                    cursor.execute("DELETE FROM alternatives WHERE id=?", (row["id"],))
                    cursor.execute("DELETE FROM scores WHERE alternative_id=?", (row["id"],))
                    conn.commit()
                    st.success("Alternatif dihapus")
                    st.rerun()

# ==================================
# INPUT NILAI
# ==================================

elif menu == "Input Nilai":

    st.title("Input Nilai")

    criteria = get_criteria()
    alternatives = get_alternatives()

    if len(criteria) == 0 or len(alternatives) == 0:
        st.warning("Isi kriteria dan alternatif terlebih dahulu")
    else:
        alt = st.selectbox("Alternatif", alternatives["name"])
        alt_id = alternatives[alternatives["name"] == alt]["id"].iloc[0]

        scores = get_scores()
        existing = scores[scores["alternative_id"] == alt_id]

        st.subheader(f"Nilai untuk: {alt}")

        for _, row in criteria.iterrows():
            cid = row["id"]
            existing_row = existing[existing["criteria_id"] == cid]
            has_value = len(existing_row) > 0
            current_value = float(existing_row["value"].iloc[0]) if has_value else 0.0

            with st.expander(
                f"{row['name']} — {'✅ ' + str(current_value) if has_value else '➕ Belum diisi'}"
            ):
                with st.form(f"form_nilai_{alt_id}_{cid}"):
                    nilai = st.number_input(
                        "Nilai", min_value=0.0, value=current_value,
                        key=f"input_{alt_id}_{cid}"
                    )
                    col1, col2 = st.columns(2)
                    with col1:
                        simpan = st.form_submit_button(
                            "Update" if has_value else "Simpan"
                        )
                    with col2:
                        hapus = st.form_submit_button(
                            "Hapus", type="primary", disabled=not has_value
                        )

                if simpan:
                    if has_value:
                        score_id = int(existing_row["id"].iloc[0])
                        cursor.execute(
                            "UPDATE scores SET value=? WHERE id=?",
                            (nilai, score_id)
                        )
                    else:
                        cursor.execute(
                            "INSERT INTO scores(alternative_id,criteria_id,value) VALUES(?,?,?)",
                            (alt_id, cid, nilai)
                        )
                    conn.commit()
                    st.success("Tersimpan")
                    st.rerun()

                if hapus and has_value:
                    score_id = int(existing_row["id"].iloc[0])
                    cursor.execute("DELETE FROM scores WHERE id=?", (score_id,))
                    conn.commit()
                    st.success("Nilai dihapus")
                    st.rerun()

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