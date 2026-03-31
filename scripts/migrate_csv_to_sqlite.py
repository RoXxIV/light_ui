#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de migration one-shot : CSV -> SQLite

Importe printed_serials.csv -> table batteries
Importe sav_batteries.csv   -> table sav_entries

Usage :
    python scripts/migrate_csv_to_sqlite.py

Le script est idempotent : il peut être relancé sans risque
(INSERT OR IGNORE sur les clés primaires existantes).
"""

import csv
import os
import sys
import sqlite3

# Ajouter la racine du projet au path pour les imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.db.sqlite_manager import DB_PATH, init_db

CSV_BATTERIES = os.path.join(PROJECT_ROOT, "printed_serials.csv")
CSV_SAV       = os.path.join(PROJECT_ROOT, "sav_batteries.csv")


def _parse_sav_status(value):
    """Convertit 'True'/'False' (string CSV) en 0/1 (SQLite)."""
    if isinstance(value, str):
        return 1 if value.strip().lower() == "true" else 0
    return 0


def _empty_to_none(value):
    """Convertit une chaîne vide en None (NULL SQLite)."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def migrate_batteries(conn, cursor):
    """Importe printed_serials.csv dans la table batteries."""
    print(f"\n[1/2] Migration batteries : {CSV_BATTERIES}")

    if not os.path.exists(CSV_BATTERIES):
        print(f"  [SKIP] Fichier introuvable, migration batteries ignoree.")
        return 0, 0

    inserted = 0
    skipped  = 0

    with open(CSV_BATTERIES, mode="r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            serial = _empty_to_none(row.get("NumeroSerie"))
            if not serial:
                skipped += 1
                continue

            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO batteries (
                        numero_serie,
                        code_aleatoire_qr,
                        timestamp_impression,
                        timestamp_test_done,
                        timestamp_expedition,
                        type,
                        version,
                        sav_status,
                        score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    serial,
                    _empty_to_none(row.get("CodeAleatoireQR")),
                    _empty_to_none(row.get("TimestampImpression")),
                    _empty_to_none(row.get("TimestampTestDone")),
                    _empty_to_none(row.get("TimestampExpedition")),
                    _empty_to_none(row.get("type")),
                    _empty_to_none(row.get("version")),
                    _parse_sav_status(row.get("sav_status", "False")),
                    _empty_to_none(row.get("score")),
                ))

                if cursor.rowcount == 1:
                    inserted += 1
                else:
                    skipped += 1  # Déjà présent (INSERT OR IGNORE)

            except Exception as e:
                print(f"  [WARN] Erreur sur la ligne {serial} : {e}")
                skipped += 1

    conn.commit()
    return inserted, skipped


def migrate_sav(conn, cursor):
    """Importe sav_batteries.csv dans la table sav_entries."""
    print(f"\n[2/2] Migration SAV : {CSV_SAV}")

    if not os.path.exists(CSV_SAV):
        print(f"  [SKIP] Fichier introuvable, migration SAV ignoree.")
        return 0, 0

    inserted = 0
    skipped  = 0

    with open(CSV_SAV, mode="r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            serial   = _empty_to_none(row.get("NumeroSerie"))
            arrivee  = _empty_to_none(row.get("TimestampArrivee"))

            if not serial or not arrivee:
                skipped += 1
                continue

            try:
                # Pas de PK naturelle sur sav_entries → on vérifie l'unicité
                # sur (numero_serie, timestamp_arrivee) pour l'idempotence
                exists = cursor.execute("""
                    SELECT 1 FROM sav_entries
                    WHERE numero_serie = ? AND timestamp_arrivee = ?
                """, (serial, arrivee)).fetchone()

                if exists:
                    skipped += 1
                    continue

                cursor.execute("""
                    INSERT INTO sav_entries (numero_serie, timestamp_arrivee, timestamp_depart)
                    VALUES (?, ?, ?)
                """, (
                    serial,
                    arrivee,
                    _empty_to_none(row.get("TimestampDepart")),
                ))
                inserted += 1

            except Exception as e:
                print(f"  [WARN] Erreur sur la ligne {serial} / {arrivee} : {e}")
                skipped += 1

    conn.commit()
    return inserted, skipped


def print_summary(conn):
    """Affiche le nombre de lignes dans chaque table après migration."""
    print("\n--- Résumé base de données ---")
    for table in ("batteries", "sav_entries", "sync_queue"):
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table:<15} : {count} ligne(s)")


def main():
    print("=" * 50)
    print(" Migration CSV -> SQLite")
    print("=" * 50)
    print(f"Base de données : {DB_PATH}")

    # Initialiser la DB (crée les tables si besoin)
    init_db()

    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # --- Batteries ---
        bat_inserted, bat_skipped = migrate_batteries(conn, cursor)
        print(f"  [OK]     Inserees  : {bat_inserted}")
        print(f"  [SKIP]   Ignorees  : {bat_skipped}")

        # --- SAV ---
        sav_inserted, sav_skipped = migrate_sav(conn, cursor)
        print(f"  [OK]     Inserees  : {sav_inserted}")
        print(f"  [SKIP]   Ignorees  : {sav_skipped}")

        print_summary(conn)
        print("\n[OK] Migration terminee avec succes.")

    except Exception as e:
        print(f"\n[ERREUR] Erreur critique : {e}")
        conn.rollback()
        sys.exit(1)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
