# -*- coding: utf-8 -*-
"""
Gestionnaire de la base de données SQLite locale.
Remplace les fichiers CSV printed_serials.csv et sav_batteries.csv.
"""

import sqlite3
import json
import os
import random
import string
import threading
from datetime import datetime
from src.ui.system_utils import log

# Chemin du fichier DB à la racine du projet
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(_PROJECT_ROOT, "revaw.db")

# Lock pour les écritures concurrentes (worker + UI)
_lock = threading.Lock()


def _get_connection():
    """Retourne une connexion SQLite avec row_factory activé."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Initialise la base de données et crée les tables si elles n'existent pas.
    À appeler une seule fois au démarrage de l'UI.
    """
    log(f"SQLiteManager: Initialisation de la base de données : {DB_PATH}", level="INFO")

    with _lock:
        conn = _get_connection()
        try:
            cursor = conn.cursor()

            # --- Table batteries (remplace printed_serials.csv) ---
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS batteries (
                    numero_serie         TEXT PRIMARY KEY,
                    code_aleatoire_qr    TEXT,
                    timestamp_impression TEXT,
                    timestamp_test_done  TEXT,
                    timestamp_expedition TEXT,
                    type                 TEXT,
                    version              TEXT,
                    sav_status           INTEGER DEFAULT 0,
                    score                REAL
                )
            """)

            # --- Table sav_entries (remplace sav_batteries.csv) ---
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sav_entries (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero_serie      TEXT NOT NULL,
                    timestamp_arrivee TEXT NOT NULL,
                    timestamp_depart  TEXT
                )
            """)

            # --- Table sync_queue (file d'attente MongoDB) ---
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_queue (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation    TEXT NOT NULL,
                    payload      TEXT NOT NULL,
                    status       TEXT DEFAULT 'pending',
                    attempts     INTEGER DEFAULT 0,
                    created_at   TEXT NOT NULL,
                    last_attempt TEXT,
                    error        TEXT
                )
            """)

            conn.commit()
            log("SQLiteManager: Tables initialisées avec succès", level="INFO")

        except Exception as e:
            log(f"SQLiteManager: Erreur lors de l'initialisation : {e}", level="ERROR")
            raise
        finally:
            conn.close()


# =============================================================================
# UTILITAIRES
# =============================================================================

def generate_random_code(length=6):
    """Génère un code alphanumérique aléatoire."""
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))


def get_next_numeric_part():
    """
    Retourne le prochain numéro de série à 4 chiffres (thread-safe).
    Incrémente le MAX des 4 derniers chiffres de tous les serials existants.
    """
    with _lock:
        conn = _get_connection()
        try:
            row = conn.execute("""
                SELECT MAX(CAST(SUBSTR(numero_serie, -4) AS INTEGER)) AS max_num
                FROM batteries
            """).fetchone()
            last_num = row["max_num"] if row and row["max_num"] is not None else 0
            return str(last_num + 1).zfill(4)
        except Exception as e:
            log(f"SQLiteManager: Erreur get_next_numeric_part : {e}", level="ERROR")
            raise
        finally:
            conn.close()


# =============================================================================
# BATTERIES
# =============================================================================

def insert_battery(numero_serie, code_aleatoire_qr, timestamp_impression, type_batterie, version):
    """Insère une nouvelle batterie (commande create)."""
    with _lock:
        conn = _get_connection()
        try:
            conn.execute("""
                INSERT INTO batteries (numero_serie, code_aleatoire_qr, timestamp_impression, type, version)
                VALUES (?, ?, ?, ?, ?)
            """, (numero_serie, code_aleatoire_qr, timestamp_impression, type_batterie, version))
            conn.commit()
            log(f"SQLiteManager: Batterie insérée : {numero_serie}", level="INFO")
        except sqlite3.IntegrityError:
            log(f"SQLiteManager: Batterie déjà existante : {numero_serie}", level="WARNING")
        except Exception as e:
            log(f"SQLiteManager: Erreur insert_battery : {e}", level="ERROR")
            raise
        finally:
            conn.close()


def update_battery_finish(old_serial, new_serial, timestamp_test_done):
    """Met à jour le serial (XXX → capacité réelle) et le timestamp de test (commande finish)."""
    with _lock:
        conn = _get_connection()
        try:
            conn.execute("""
                UPDATE batteries
                SET numero_serie = ?, timestamp_test_done = ?
                WHERE numero_serie = ?
            """, (new_serial, timestamp_test_done, old_serial))
            conn.commit()
            log(f"SQLiteManager: Finish appliqué : {old_serial} → {new_serial}", level="INFO")
        except Exception as e:
            log(f"SQLiteManager: Erreur update_battery_finish : {e}", level="ERROR")
            raise
        finally:
            conn.close()


def update_battery_expedition(numero_serie, timestamp_expedition):
    """Enregistre la date d'expédition (commande expedition)."""
    with _lock:
        conn = _get_connection()
        try:
            conn.execute("""
                UPDATE batteries
                SET timestamp_expedition = ?
                WHERE numero_serie = ?
            """, (timestamp_expedition, numero_serie))
            conn.commit()
            log(f"SQLiteManager: Expédition enregistrée : {numero_serie}", level="INFO")
        except Exception as e:
            log(f"SQLiteManager: Erreur update_battery_expedition : {e}", level="ERROR")
            raise
        finally:
            conn.close()


def update_battery_sav_status(numero_serie, sav_status: bool):
    """Met à jour le statut SAV d'une batterie."""
    with _lock:
        conn = _get_connection()
        try:
            conn.execute("""
                UPDATE batteries SET sav_status = ? WHERE numero_serie = ?
            """, (1 if sav_status else 0, numero_serie))
            conn.commit()
            log(f"SQLiteManager: sav_status={sav_status} pour {numero_serie}", level="INFO")
        except Exception as e:
            log(f"SQLiteManager: Erreur update_battery_sav_status : {e}", level="ERROR")
            raise
        finally:
            conn.close()


def get_battery(numero_serie):
    """
    Retourne une batterie par son numéro de série.
    Retourne None si introuvable.
    """
    conn = _get_connection()
    try:
        row = conn.execute("""
            SELECT * FROM batteries WHERE numero_serie = ?
        """, (numero_serie,)).fetchone()
        return dict(row) if row else None
    except Exception as e:
        log(f"SQLiteManager: Erreur get_battery : {e}", level="ERROR")
        return None
    finally:
        conn.close()


def battery_exists(numero_serie):
    """Vérifie si un numéro de série existe dans la base."""
    return get_battery(numero_serie) is not None


# =============================================================================
# SAV ENTRIES
# =============================================================================

def insert_sav_entry(numero_serie, timestamp_arrivee):
    """Enregistre une entrée en SAV (commande sav)."""
    with _lock:
        conn = _get_connection()
        try:
            conn.execute("""
                INSERT INTO sav_entries (numero_serie, timestamp_arrivee)
                VALUES (?, ?)
            """, (numero_serie, timestamp_arrivee))
            conn.commit()
            log(f"SQLiteManager: Entrée SAV enregistrée : {numero_serie}", level="INFO")
        except Exception as e:
            log(f"SQLiteManager: Erreur insert_sav_entry : {e}", level="ERROR")
            raise
        finally:
            conn.close()


def close_sav_entry(numero_serie, timestamp_depart):
    """
    Ferme l'entrée SAV ouverte (timestamp_depart IS NULL) pour ce serial.
    Appelé lors d'une expédition de batterie en SAV.
    """
    with _lock:
        conn = _get_connection()
        try:
            conn.execute("""
                UPDATE sav_entries
                SET timestamp_depart = ?
                WHERE numero_serie = ? AND timestamp_depart IS NULL
            """, (timestamp_depart, numero_serie))
            conn.commit()
            log(f"SQLiteManager: Sortie SAV enregistrée : {numero_serie}", level="INFO")
        except Exception as e:
            log(f"SQLiteManager: Erreur close_sav_entry : {e}", level="ERROR")
            raise
        finally:
            conn.close()


def get_open_sav_entry(numero_serie):
    """
    Retourne l'entrée SAV ouverte (sans date de départ) pour ce serial.
    Utilisé pour récupérer le timestamp_arrivee lors d'une sortie SAV.
    Retourne None si aucune entrée ouverte.
    """
    conn = _get_connection()
    try:
        row = conn.execute("""
            SELECT * FROM sav_entries
            WHERE numero_serie = ? AND timestamp_depart IS NULL
            ORDER BY timestamp_arrivee DESC
            LIMIT 1
        """, (numero_serie,)).fetchone()
        return dict(row) if row else None
    except Exception as e:
        log(f"SQLiteManager: Erreur get_open_sav_entry : {e}", level="ERROR")
        return None
    finally:
        conn.close()


# =============================================================================
# SYNC QUEUE
# =============================================================================

def enqueue(operation, payload: dict):
    """
    Ajoute une opération dans la file d'attente de sync MongoDB.

    Args:
        operation (str): 'create' | 'finish' | 'expedition' | 'sav_in' | 'sav_out'
        payload (dict): Données de l'opération, sérialisées en JSON.
    """
    with _lock:
        conn = _get_connection()
        try:
            conn.execute("""
                INSERT INTO sync_queue (operation, payload, created_at)
                VALUES (?, ?, ?)
            """, (operation, json.dumps(payload), datetime.now().isoformat()))
            conn.commit()
            log(f"SQLiteManager: Opération '{operation}' enfilée dans sync_queue", level="DEBUG")
        except Exception as e:
            log(f"SQLiteManager: Erreur enqueue : {e}", level="ERROR")
            raise
        finally:
            conn.close()


def get_pending_operations():
    """
    Retourne toutes les opérations en attente, dans l'ordre de création.
    Utilisé par le worker MongoDB.
    """
    conn = _get_connection()
    try:
        rows = conn.execute("""
            SELECT * FROM sync_queue
            WHERE status = 'pending'
            ORDER BY id ASC
        """).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        log(f"SQLiteManager: Erreur get_pending_operations : {e}", level="ERROR")
        return []
    finally:
        conn.close()


def mark_operation_sent(operation_id):
    """Marque une opération comme envoyée avec succès."""
    with _lock:
        conn = _get_connection()
        try:
            conn.execute("""
                UPDATE sync_queue SET status = 'sent' WHERE id = ?
            """, (operation_id,))
            conn.commit()
        except Exception as e:
            log(f"SQLiteManager: Erreur mark_operation_sent : {e}", level="ERROR")
        finally:
            conn.close()


def mark_operation_attempt(operation_id, error_msg):
    """Incrémente le compteur de tentatives et enregistre l'erreur. Reste 'pending'."""
    with _lock:
        conn = _get_connection()
        try:
            conn.execute("""
                UPDATE sync_queue
                SET attempts = attempts + 1,
                    last_attempt = ?,
                    error = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), error_msg, operation_id))
            conn.commit()
        except Exception as e:
            log(f"SQLiteManager: Erreur mark_operation_attempt : {e}", level="ERROR")
        finally:
            conn.close()


# =============================================================================
# STATS (InfoPanel)
# =============================================================================

def get_last_serial():
    """Retourne le dernier numéro de série imprimé."""
    conn = _get_connection()
    try:
        row = conn.execute("""
            SELECT numero_serie FROM batteries
            ORDER BY timestamp_impression DESC
            LIMIT 1
        """).fetchone()
        return row["numero_serie"] if row else None
    except Exception as e:
        log(f"SQLiteManager: Erreur get_last_serial : {e}", level="ERROR")
        return None
    finally:
        conn.close()


def count_produced_today():
    """Retourne le nombre de batteries créées aujourd'hui."""
    today = datetime.now().strftime("%Y-%m-%d")
    conn = _get_connection()
    try:
        row = conn.execute("""
            SELECT COUNT(*) as total FROM batteries
            WHERE timestamp_impression LIKE ?
        """, (f"{today}%",)).fetchone()
        return row["total"] if row else 0
    except Exception as e:
        log(f"SQLiteManager: Erreur count_produced_today : {e}", level="ERROR")
        return 0
    finally:
        conn.close()


def count_shipped_today():
    """Retourne le nombre de batteries expédiées aujourd'hui."""
    today = datetime.now().strftime("%Y-%m-%d")
    conn = _get_connection()
    try:
        row = conn.execute("""
            SELECT COUNT(*) as total FROM batteries
            WHERE timestamp_expedition LIKE ?
        """, (f"{today}%",)).fetchone()
        return row["total"] if row else 0
    except Exception as e:
        log(f"SQLiteManager: Erreur count_shipped_today : {e}", level="ERROR")
        return 0
    finally:
        conn.close()


def count_shipped_this_month():
    """Retourne le nombre de batteries expédiées ce mois-ci."""
    month = datetime.now().strftime("%Y-%m")
    conn = _get_connection()
    try:
        row = conn.execute("""
            SELECT COUNT(*) as total FROM batteries
            WHERE timestamp_expedition LIKE ?
        """, (f"{month}%",)).fetchone()
        return row["total"] if row else 0
    except Exception as e:
        log(f"SQLiteManager: Erreur count_shipped_this_month : {e}", level="ERROR")
        return 0
    finally:
        conn.close()


def is_battery_in_sav(numero_serie):
    """Retourne True si la batterie a sav_status=1."""
    battery = get_battery(numero_serie)
    return bool(battery and battery.get("sav_status") == 1)


def get_battery_for_reprint(input_serial):
    """
    Recherche une batterie pour réimpression.
    Accepte un serial complet (RW-48v2710001) ou un temp serial (A0001).
    Retourne un dict avec les clés attendues par _handle_full_reprint, ou None.
    """
    conn = _get_connection()
    try:
        row = None

        # Essai 1 : serial exact
        row = conn.execute(
            "SELECT * FROM batteries WHERE numero_serie = ?", (input_serial,)
        ).fetchone()

        # Essai 2 : input est un temp serial (ex: "A0001") → chercher RW-48vXXX{last4}
        if not row and len(input_serial) >= 4:
            last4 = input_serial[-4:]
            row = conn.execute(
                "SELECT * FROM batteries WHERE numero_serie LIKE ?",
                (f"RW-48vXXX{last4}",)
            ).fetchone()

        # Essai 3 : partial match sur les 4 derniers chiffres
        if not row and len(input_serial) >= 4:
            last4 = input_serial[-4:]
            row = conn.execute(
                "SELECT * FROM batteries WHERE numero_serie LIKE ?",
                (f"%{last4}",)
            ).fetchone()

        if not row:
            return None

        battery = dict(row)
        numeric_part = battery["numero_serie"][-4:]
        material_type = battery.get("type") or "A"
        is_test_done = battery.get("timestamp_test_done") is not None

        return {
            "full_serial": battery["numero_serie"] if is_test_done else None,
            "short_serial": f"{material_type}{numeric_part}",
            "is_test_done": is_test_done,
            "random_code": battery.get("code_aleatoire_qr"),
            "timestamp_impression": battery.get("timestamp_impression"),
            "type": material_type,
        }
    except Exception as e:
        log(f"SQLiteManager: Erreur get_battery_for_reprint : {e}", level="ERROR")
        return None
    finally:
        conn.close()
