import streamlit as st
import mysql.connector
import pandas as pd
import numpy as np
from datetime import datetime
import os
import hashlib

# Load environmental variables from .env if present
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", 3306))
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_DATABASE = os.environ.get("DB_DATABASE", "spk_saw_topsis")

# Step 1: Connect to MySQL Server to ensure the database exists
try:
    init_conn = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD
    )
    init_cursor = init_conn.cursor()
    init_cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_DATABASE}")
    init_conn.commit()
    init_cursor.close()
    init_conn.close()
except Exception as e:
    st.error(f"Gagal menghubungkan ke MySQL Server: {e}")
    st.info("Pastikan MySQL server sudah berjalan dan kredensial di file `.env` sudah benar.")
    st.stop()

# Step 2: Establish the persistent connection to the target database
try:
    conn = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_DATABASE
    )
except Exception as e:
    st.error(f"Gagal menghubungkan ke database MySQL `{DB_DATABASE}`: {e}")
    st.stop()

# Helpers for execution to handle auto-reconnect and convert NumPy type parameters
def execute_write(query, params=None):
    if params:
        params = tuple(
            int(p) if isinstance(p, (np.int64, np.int32))
            else float(p) if isinstance(p, (np.float64, np.float32))
            else p
            for p in params
        )
    conn.ping(reconnect=True)
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    cur.close()

def read_sql(query, params=None):
    if params:
        params = tuple(
            int(p) if isinstance(p, (np.int64, np.int32))
            else float(p) if isinstance(p, (np.float64, np.float32))
            else p
            for p in params
        )
    conn.ping(reconnect=True)
    cur = conn.cursor()
    cur.execute(query, params)
    columns = [col[0] for col in cur.description]
    data = cur.fetchall()
    cur.close()
    return pd.DataFrame(data, columns=columns)

# Initialize tables
execute_write("""
CREATE TABLE IF NOT EXISTS criteria(
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255),
    weight DOUBLE,
    type VARCHAR(50)
)
""")

execute_write("""
CREATE TABLE IF NOT EXISTS alternatives(
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255)
)
""")

execute_write("""
CREATE TABLE IF NOT EXISTS scores(
    id INT PRIMARY KEY AUTO_INCREMENT,
    alternative_id INT,
    criteria_id INT,
    value DOUBLE
)
""")

execute_write("""
CREATE TABLE IF NOT EXISTS results(
    id INT PRIMARY KEY AUTO_INCREMENT,
    method VARCHAR(50),
    alternative VARCHAR(255),
    score DOUBLE,
    ranking INT,
    created_at VARCHAR(50)
)
""")

execute_write("""
CREATE TABLE IF NOT EXISTS user(
    id_user INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'admin'
)
""")

# Buat akun admin default jika belum ada
def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

existing_admin = read_sql("SELECT COUNT(*) as cnt FROM user WHERE role='admin'")
if existing_admin["cnt"].iloc[0] == 0:
    execute_write(
        "INSERT INTO user(username, password, role) VALUES(%s, %s, %s)",
        ("admin", hash_password("admin123"), "admin")
    )

def get_criteria():
    df = read_sql("SELECT * FROM criteria")
    if not df.empty:
        df["id"] = df["id"].astype(int)
        df["weight"] = df["weight"].astype(float)
    return df

def get_alternatives():
    df = read_sql("SELECT * FROM alternatives")
    if not df.empty:
        df["id"] = df["id"].astype(int)
    return df

def get_scores():
    df = read_sql("SELECT * FROM scores")
    if not df.empty:
        df["id"] = df["id"].astype(int)
        df["alternative_id"] = df["alternative_id"].astype(int)
        df["criteria_id"] = df["criteria_id"].astype(int)
        df["value"] = df["value"].astype(float)
    return df

def tampilkan_tabel_ranking(ranking):
    df_display = ranking[["ranking", "name", "score"]].copy()
    df_display.columns = ["Peringkat", "Nama Alternatif", "Skor"]
    
    html_table = """
    <style>
        .custom-table {
            width: 100%;
            border-collapse: collapse;
            font-family: 'Inter', sans-serif;
            font-size: 20px; /* Font size enlarged */
            margin-top: 15px;
            margin-bottom: 15px;
        }
        .custom-table th {
            background-color: rgba(46, 139, 87, 0.15);
            color: #2E8B57;
            border-bottom: 3px solid #2E8B57;
            padding: 12px 15px;
            text-align: left;
            font-weight: bold;
        }
        .custom-table td {
            padding: 12px 15px;
            border-bottom: 1px solid rgba(128, 128, 128, 0.2);
        }
        .custom-table tr:hover {
            background-color: rgba(128, 128, 128, 0.05);
        }
        .rank-1 {
            font-weight: bold;
            background-color: rgba(255, 215, 0, 0.15) !important;
            border-left: 5px solid #FFD700;
        }
    </style>
    <table class="custom-table">
        <thead>
            <tr>
                <th>Peringkat</th>
                <th>Nama Alternatif</th>
                <th>Skor</th>
            </tr>
        </thead>
        <tbody>
    """
    for _, row in df_display.iterrows():
        row_class = "rank-1" if row["Peringkat"] == 1 else ""
        formatted_score = f"{row['Skor']:.4f}"
        html_table += f"<tr class='{row_class}'>"
        if row['Peringkat'] == 1:
            html_table += "<td> <b>1 (Terbaik)</b></td>"
        else:
            html_table += f"<td>{row['Peringkat']}</td>"
        html_table += f"<td>{row['Nama Alternatif']}</td>"
        html_table += f"<td>{formatted_score}</td>"
        html_table += "</tr>"
    html_table += "</tbody></table>"
    st.markdown(html_table, unsafe_allow_html=True)

# ==================================
# AUTENTIKASI / LOGIN
# ==================================

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""

def do_login(username, password):
    hashed = hash_password(password)
    result = read_sql(
        "SELECT * FROM user WHERE username=%s AND password=%s",
        (username, hashed)
    )
    if not result.empty:
        st.session_state["logged_in"] = True
        st.session_state["username"] = username
        return True
    return False

if not st.session_state["logged_in"]:
    st.title("Login")
    st.markdown("Masuk menggunakan akun admin Anda.")

    with st.form("form_login"):
        uname = st.text_input("Username")
        pw    = st.text_input("Password", type="password")
        login_btn = st.form_submit_button("Login")

        if login_btn:
            if uname and pw:
                if do_login(uname, pw):
                    st.success("Login berhasil!")
                    st.rerun()
                else:
                    st.error("Username atau password salah.")
            else:
                st.warning("Username dan password tidak boleh kosong.")
    st.stop()

# ==================================
# SIDEBAR
# ==================================

st.sidebar.title("SPK SAW & TOPSIS")
st.sidebar.markdown(f"👤 **{st.session_state['username']}**")
if st.sidebar.button("Logout"):
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.rerun()
st.sidebar.divider()

menu = st.sidebar.radio(
    "Menu",
    [
        "Kriteria",
        "Alternatif",
        "Input Nilai",
        "Perhitungan",
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
            execute_write(
                "INSERT INTO criteria(name,weight,type) VALUES(%s,%s,%s)",
                (nama, bobot, tipe)
            )
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
                    execute_write(
                        "UPDATE criteria SET name=%s, weight=%s, type=%s WHERE id=%s",
                        (new_name, new_bobot, new_tipe, row["id"])
                    )
                    st.success("Kriteria diperbarui")
                    st.rerun()

                if delete:
                    execute_write("DELETE FROM criteria WHERE id=%s", (row["id"],))
                    execute_write("DELETE FROM scores WHERE criteria_id=%s", (row["id"],))
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
            execute_write(
                "INSERT INTO alternatives(name) VALUES(%s)",
                (nama,)
            )
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
                    execute_write(
                        "UPDATE alternatives SET name=%s WHERE id=%s",
                        (new_name, row["id"])
                    )
                    st.success("Alternatif diperbarui")
                    st.rerun()

                if delete:
                    execute_write("DELETE FROM alternatives WHERE id=%s", (row["id"],))
                    execute_write("DELETE FROM scores WHERE alternative_id=%s", (row["id"],))
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
                f"{row['name']} — {str(current_value) if has_value else 'Belum diisi'}"
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
                        execute_write(
                            "UPDATE scores SET value=%s WHERE id=%s",
                            (nilai, score_id)
                        )
                    else:
                        execute_write(
                            "INSERT INTO scores(alternative_id,criteria_id,value) VALUES(%s,%s,%s)",
                            (alt_id, cid, nilai)
                        )
                    st.success("Tersimpan")
                    st.rerun()

                if hapus and has_value:
                    score_id = int(existing_row["id"].iloc[0])
                    execute_write("DELETE FROM scores WHERE id=%s", (score_id,))
                    st.success("Nilai dihapus")
                    st.rerun()

# ==================================
# PERHITUNGAN
# ==================================

elif menu == "Perhitungan":

    st.title("Langkah-Langkah Perhitungan")

    criteria     = get_criteria()
    alternatives = get_alternatives()
    scores       = get_scores()

    if len(criteria) == 0 or len(alternatives) == 0 or len(scores) == 0:
        st.warning("Lengkapi data Kriteria, Alternatif, dan Nilai terlebih dahulu.")
    else:
        # Bangun matriks keputusan
        matrix = scores.pivot_table(
            index="alternative_id",
            columns="criteria_id",
            values="value",
            aggfunc="last"
        )

        # Ganti index/kolom dengan nama agar tabel mudah dibaca
        alt_map  = dict(zip(alternatives["id"], alternatives["name"]))
        crit_map = dict(zip(criteria["id"],     criteria["name"]))
        matrix_display = matrix.rename(index=alt_map, columns=crit_map)

        tab_saw, tab_topsis = st.tabs(["SAW", "TOPSIS"])

        # ──────────────────────────────────────────────
        # TAB SAW
        # ──────────────────────────────────────────────
        with tab_saw:
            st.header("Metode SAW (Simple Additive Weighting)")
            st.markdown(
                "SAW menormalisasi setiap nilai terhadap nilai terbaik pada "
                "kolom kriteria, lalu mengalikan dengan bobot dan menjumlahkannya."
            )

            # --- Langkah 1: Matriks Keputusan ---
            st.subheader("Langkah 1 — Matriks Keputusan (X)")
            st.dataframe(matrix_display.style.format("{:.4f}"), use_container_width=True)

            # --- Langkah 2: Normalisasi ---
            st.subheader("Langkah 2 — Normalisasi Matriks (R)")
            st.markdown(
                "- **Benefit**: $r_{ij} = \\dfrac{x_{ij}}{\\max_i(x_{ij})}$\n"
                "- **Cost**   : $r_{ij} = \\dfrac{\\min_i(x_{ij})}{x_{ij}}$"
            )

            norm = matrix.copy().astype(float)
            for _, crow in criteria.iterrows():
                cid = crow["id"]
                if crow["type"] == "benefit":
                    norm[cid] = matrix[cid] / matrix[cid].max()
                else:
                    norm[cid] = matrix[cid].min() / matrix[cid]

            norm_display = norm.rename(index=alt_map, columns=crit_map)
            st.dataframe(norm_display.style.format("{:.4f}"), use_container_width=True)

            # Tabel referensi max/min
            ref_rows = []
            for _, crow in criteria.iterrows():
                cid = crow["id"]
                ref_rows.append({
                    "Kriteria" : crow["name"],
                    "Tipe"     : crow["type"],
                    "Max"      : f"{matrix[cid].max():.4f}",
                    "Min"      : f"{matrix[cid].min():.4f}",
                    "Acuan Normalisasi": (
                        f"max = {matrix[cid].max():.4f}" if crow["type"] == "benefit"
                        else f"min = {matrix[cid].min():.4f}"
                    )
                })
            st.caption("Nilai acuan normalisasi per kriteria:")
            st.dataframe(pd.DataFrame(ref_rows), use_container_width=True, hide_index=True)

            # --- Langkah 3: Bobot ---
            st.subheader("Langkah 3 — Bobot Kriteria (W)")
            w_df = criteria[["name", "weight", "type"]].copy()
            w_df.columns = ["Kriteria", "Bobot", "Tipe"]
            st.dataframe(w_df, use_container_width=True, hide_index=True)

            # --- Langkah 4: Nilai Terbobot ---
            st.subheader("Langkah 4 — Matriks Terbobot (R × W)")
            weights      = criteria["weight"].values
            weighted     = norm * weights
            weighted_disp = weighted.rename(index=alt_map, columns=crit_map)
            st.dataframe(weighted_disp.style.format("{:.4f}"), use_container_width=True)

            # --- Langkah 5: Skor Akhir & Ranking ---
            st.subheader("Langkah 5 — Skor Akhir & Peringkat")
            st.markdown("$V_i = \\sum_j w_j \\cdot r_{ij}$")

            final_saw = weighted.sum(axis=1)
            rank_saw  = pd.DataFrame({
                "Alternatif": [alt_map[i] for i in final_saw.index],
                "Skor SAW"  : final_saw.values
            }).sort_values("Skor SAW", ascending=False).reset_index(drop=True)
            rank_saw.index     += 1
            rank_saw.index.name = "Peringkat"
            st.dataframe(rank_saw.style.format({"Skor SAW": "{:.4f}"}), use_container_width=True)

        # ──────────────────────────────────────────────
        # TAB TOPSIS
        # ──────────────────────────────────────────────
        with tab_topsis:
            st.header("Metode TOPSIS (Technique for Order Preference by Similarity to Ideal Solution)")
            st.markdown(
                "TOPSIS memilih alternatif yang jaraknya paling dekat ke solusi ideal positif "
                "dan paling jauh dari solusi ideal negatif."
            )

            # --- Langkah 1: Matriks Keputusan ---
            st.subheader("Langkah 1 — Matriks Keputusan (X)")
            st.dataframe(matrix_display.style.format("{:.4f}"), use_container_width=True)

            # --- Langkah 2: Normalisasi Vektor ---
            st.subheader("Langkah 2 — Normalisasi Vektor (R)")
            st.markdown(
                "$r_{ij} = \\dfrac{x_{ij}}{\\sqrt{\\sum_i x_{ij}^2}}$"
            )
            r = matrix / np.sqrt((matrix ** 2).sum())
            r_display = r.rename(index=alt_map, columns=crit_map)
            st.dataframe(r_display.style.format("{:.4f}"), use_container_width=True)

            # Tampilkan pembagi (akar jumlah kuadrat)
            denom_rows = []
            for _, crow in criteria.iterrows():
                cid = crow["id"]
                denom_rows.append({
                    "Kriteria"           : crow["name"],
                    "√Σx²"               : f"{np.sqrt((matrix[cid]**2).sum()):.4f}"
                })
            st.caption("Pembagi normalisasi per kriteria (√Σx²):")
            st.dataframe(pd.DataFrame(denom_rows), use_container_width=True, hide_index=True)

            # --- Langkah 3: Bobot ---
            st.subheader("Langkah 3 — Bobot Kriteria (W)")
            st.dataframe(w_df, use_container_width=True, hide_index=True)

            # --- Langkah 4: Matriks Terbobot ---
            st.subheader("Langkah 4 — Matriks Terbobot (Y = R × W)")
            st.markdown("$y_{ij} = w_j \\cdot r_{ij}$")
            y         = r * weights
            y_display = y.rename(index=alt_map, columns=crit_map)
            st.dataframe(y_display.style.format("{:.4f}"), use_container_width=True)

            # --- Langkah 5: Solusi Ideal ---
            st.subheader("Langkah 5 — Solusi Ideal Positif (A⁺) & Negatif (A⁻)")
            ideal_plus  = []
            ideal_minus = []
            for _, crow in criteria.iterrows():
                cid = crow["id"]
                if crow["type"] == "benefit":
                    ideal_plus.append(y[cid].max())
                    ideal_minus.append(y[cid].min())
                else:
                    ideal_plus.append(y[cid].min())
                    ideal_minus.append(y[cid].max())

            ideal_df = pd.DataFrame({
                "Kriteria": [crit_map[c] for c in matrix.columns],
                "Tipe"    : criteria["type"].values,
                "A⁺ (Ideal Positif)" : [f"{v:.4f}" for v in ideal_plus],
                "A⁻ (Ideal Negatif)" : [f"{v:.4f}" for v in ideal_minus],
            })
            st.dataframe(ideal_df, use_container_width=True, hide_index=True)

            ideal_plus  = np.array(ideal_plus)
            ideal_minus = np.array(ideal_minus)

            # --- Langkah 6: Jarak ---
            st.subheader("Langkah 6 — Jarak ke Solusi Ideal")
            st.markdown(
                "- $D_i^+ = \\sqrt{\\sum_j (y_{ij} - A_j^+)^2}$\n"
                "- $D_i^- = \\sqrt{\\sum_j (y_{ij} - A_j^-)^2}$"
            )
            d_plus  = np.sqrt(((y - ideal_plus)  ** 2).sum(axis=1))
            d_minus = np.sqrt(((y - ideal_minus) ** 2).sum(axis=1))

            dist_df = pd.DataFrame({
                "Alternatif": [alt_map[i] for i in y.index],
                "D⁺"        : d_plus.values,
                "D⁻"        : d_minus.values,
            })
            st.dataframe(dist_df.style.format({"D⁺": "{:.4f}", "D⁻": "{:.4f}"}),
                         use_container_width=True, hide_index=True)

            # --- Langkah 7: Nilai Preferensi & Ranking ---
            st.subheader("Langkah 7 — Nilai Preferensi (V) & Peringkat")
            st.markdown("$V_i = \\dfrac{D_i^-}{D_i^+ + D_i^-}$")

            pref = d_minus / (d_plus + d_minus)
            rank_topsis = pd.DataFrame({
                "Alternatif"      : [alt_map[i] for i in y.index],
                "D⁺"              : d_plus.values,
                "D⁻"              : d_minus.values,
                "Skor TOPSIS (V)" : pref.values,
            }).sort_values("Skor TOPSIS (V)", ascending=False).reset_index(drop=True)
            rank_topsis.index      += 1
            rank_topsis.index.name  = "Peringkat"
            st.dataframe(
                rank_topsis.style.format({
                    "D⁺": "{:.4f}", "D⁻": "{:.4f}", "Skor TOPSIS (V)": "{:.4f}"
                }),
                use_container_width=True
            )

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
            "alternative_id": final.index.values,
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

        tampilkan_tabel_ranking(ranking)

        if st.button("Simpan Hasil SAW"):

            for _, row in ranking.iterrows():

                execute_write("""
                INSERT INTO results(
                method,
                alternative,
                score,
                ranking,
                created_at
                )
                VALUES(%s,%s,%s,%s,%s)
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
            "alternative_id": matrix.index.values,
            "score": pref.values
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

        tampilkan_tabel_ranking(ranking)

        if st.button("Simpan Hasil TOPSIS"):

            for _, row in ranking.iterrows():

                execute_write("""
                INSERT INTO results(
                method,
                alternative,
                score,
                ranking,
                created_at
                )
                VALUES(%s,%s,%s,%s,%s)
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

            st.success("Hasil disimpan")

# ==================================
# RIWAYAT
# ==================================

elif menu == "Riwayat":

    st.title("Riwayat Perhitungan")

    data = read_sql(
        "SELECT * FROM results ORDER BY id DESC"
    )

    st.dataframe(data)