-- ============================================================
-- Database: spk_saw_topsis
-- Dibuat berdasarkan struktur tabel di app.py
-- ============================================================

CREATE DATABASE IF NOT EXISTS spk_saw_topsis
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE spk_saw_topsis;

-- ------------------------------------------------------------
-- Tabel: user
-- Menyimpan akun login (role selalu 'admin')
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user (
    id_user  INT          PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,          -- SHA-256 hash
    role     VARCHAR(50)  NOT NULL DEFAULT 'admin'
);

-- Akun admin default  (password: admin123)
-- SHA-256("admin123") = 240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a
INSERT INTO user (username, password, role)
SELECT 'admin',
       '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a',
       'admin'
WHERE NOT EXISTS (
    SELECT 1 FROM user WHERE role = 'admin'
);

-- ------------------------------------------------------------
-- Tabel: criteria
-- Menyimpan kriteria penilaian (nama, bobot, tipe benefit/cost)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS criteria (
    id     INT          PRIMARY KEY AUTO_INCREMENT,
    name   VARCHAR(255),
    weight DOUBLE,
    type   VARCHAR(50)   -- 'benefit' atau 'cost'
);

-- ------------------------------------------------------------
-- Tabel: alternatives
-- Menyimpan daftar alternatif yang akan dinilai
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alternatives (
    id   INT          PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255)
);

-- ------------------------------------------------------------
-- Tabel: scores
-- Menyimpan nilai setiap alternatif untuk setiap kriteria
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scores (
    id             INT    PRIMARY KEY AUTO_INCREMENT,
    alternative_id INT,
    criteria_id    INT,
    value          DOUBLE,
    FOREIGN KEY (alternative_id) REFERENCES alternatives(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (criteria_id)    REFERENCES criteria(id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

-- ------------------------------------------------------------
-- Tabel: results
-- Menyimpan riwayat hasil perhitungan SAW & TOPSIS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS results (
    id          INT          PRIMARY KEY AUTO_INCREMENT,
    method      VARCHAR(50),              -- 'SAW' atau 'TOPSIS'
    alternative VARCHAR(255),
    score       DOUBLE,
    ranking     INT,
    created_at  VARCHAR(50)               -- format: YYYY-MM-DD HH:MM:SS
);
