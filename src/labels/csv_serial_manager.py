# -*- coding: utf-8 -*-
"""
Gestionnaire pour les fichiers CSV et la génération de numéros de série.
"""
import csv
import os
import random
import string
import re
from datetime import datetime
from src.ui.system_utils import log
from .printer_config import PrinterConfig

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV_FILE_PATH = os.path.join(PROJECT_ROOT, "printed_serials.csv")
SAV_CSV_FILE_PATH = os.path.join(PROJECT_ROOT, "sav_batteries.csv")


class CSVSerialManager:
    """
    Classe pour gérer les opérations CSV et la génération de numéros de série.
    """
    # Configuration
    SERIAL_PREFIX_BASE = "RW-48v"
    SERIAL_NUMERIC_LENGTH = 4
    SERIAL_CSV_FILE = CSV_FILE_PATH
    SAV_CSV_FILE = SAV_CSV_FILE_PATH

    @staticmethod
    def generate_random_code(length=6):
        """Génère une chaîne alphanumérique aléatoire de la longueur spécifiée."""
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for i in range(length))

    @staticmethod
    def initialize_serial_csv():
        """Crée le fichier CSV avec les entêtes s'il n'existe pas ou s'il est vide."""
        file_needs_header = False

        # Cas 1: Fichier n'existe pas
        if not os.path.exists(CSVSerialManager.SERIAL_CSV_FILE):
            file_needs_header = True
            log(f"Fichier CSV '{CSVSerialManager.SERIAL_CSV_FILE}' n'existe pas, création avec en-têtes.",
                level="INFO")

        # Cas 2: Fichier existe mais est vide ou n'a pas d'en-tête
        else:
            try:
                with open(CSVSerialManager.SERIAL_CSV_FILE,
                          mode='r',
                          newline='',
                          encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:  # Fichier vide
                        file_needs_header = True
                        log(f"Fichier CSV '{CSVSerialManager.SERIAL_CSV_FILE}' est vide, ajout des en-têtes.",
                            level="INFO")
                    elif not content.startswith(
                            "TimestampImpression"):  # Pas d'en-tête
                        file_needs_header = True
                        log(f"Fichier CSV '{CSVSerialManager.SERIAL_CSV_FILE}' sans en-têtes, ajout des en-têtes.",
                            level="INFO")
            except Exception as e:
                log(f"Erreur vérification CSV '{CSVSerialManager.SERIAL_CSV_FILE}': {e}. Recréation.",
                    level="WARNING")
                file_needs_header = True

        # Écrire les en-têtes si nécessaire
        if file_needs_header:
            try:
                with open(CSVSerialManager.SERIAL_CSV_FILE,
                          mode='w',
                          newline='',
                          encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "TimestampImpression", "NumeroSerie",
                        "CodeAleatoireQR", "TimestampTestDone",
                        "TimestampExpedition", "type", "version", "sav_status"
                    ])
                log(f"En-têtes CSV ajoutés dans '{CSVSerialManager.SERIAL_CSV_FILE}'.",
                    level="INFO")
            except IOError as e:
                log(f"Impossible de créer/modifier le fichier CSV '{CSVSerialManager.SERIAL_CSV_FILE}': {e}",
                    level="ERROR")
                raise

    @staticmethod
    def initialize_sav_csv():
        """Crée le fichier CSV SAV avec les entêtes s'il n'existe pas ou s'il est vide."""
        file_needs_header = False

        # Cas 1: Fichier n'existe pas
        if not os.path.exists(CSVSerialManager.SAV_CSV_FILE):
            file_needs_header = True
            log(f"Fichier CSV SAV '{CSVSerialManager.SAV_CSV_FILE}' n'existe pas, création avec en-têtes.",
                level="INFO")

        # Cas 2: Fichier existe mais est vide ou n'a pas d'en-tête
        else:
            try:
                with open(CSVSerialManager.SAV_CSV_FILE,
                          mode='r',
                          newline='',
                          encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:  # Fichier vide
                        file_needs_header = True
                        log(f"Fichier CSV SAV '{CSVSerialManager.SAV_CSV_FILE}' est vide, ajout des en-têtes.",
                            level="INFO")
                    elif not content.startswith(
                            "TimestampArrivee"):  # Pas d'en-tête SAV
                        file_needs_header = True
                        log(f"Fichier CSV SAV '{CSVSerialManager.SAV_CSV_FILE}' sans en-têtes, ajout des en-têtes.",
                            level="INFO")
            except Exception as e:
                log(f"Erreur vérification CSV SAV '{CSVSerialManager.SAV_CSV_FILE}': {e}. Recréation.",
                    level="WARNING")
                file_needs_header = True

        # Écrire les en-têtes SAV si nécessaire
        if file_needs_header:
            try:
                with open(CSVSerialManager.SAV_CSV_FILE,
                          mode='w',
                          newline='',
                          encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(
                        ["TimestampArrivee", "NumeroSerie", "TimestampDepart"])
                log(f"En-têtes CSV SAV ajoutés dans '{CSVSerialManager.SAV_CSV_FILE}'.",
                    level="INFO")
            except IOError as e:
                log(f"Impossible de créer/modifier le fichier CSV SAV '{CSVSerialManager.SAV_CSV_FILE}': {e}",
                    level="ERROR")
                raise

    @staticmethod
    def get_last_serial_from_csv():
        """Lit le CSV et retourne le dernier NumeroSerie enregistré en se basant sur la partie numérique.
           Retourne None si le fichier est vide, n'existe pas, ou en cas d'erreur."""
        last_numeric_part = -1
        last_full_serial = None
        # CORRECTION: Regex plus flexible qui accepte "XXX" ou des chiffres pour la capacité
        pattern = re.compile(r"RW-48v(XXX|\d+)(\d{4})")

        try:
            if not os.path.exists(CSVSerialManager.SERIAL_CSV_FILE):
                log(f"Le fichier CSV '{CSVSerialManager.SERIAL_CSV_FILE}' n'existe pas. Aucun dernier sérial.",
                    level="INFO")
                return None

            with open(CSVSerialManager.SERIAL_CSV_FILE,
                      mode='r',
                      newline='',
                      encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    serial = row.get("NumeroSerie")
                    if serial:
                        # On ne cherche plus au début de la chaine, mais n'importe où
                        match = pattern.search(serial)
                        if match:
                            numeric_part = int(match.group(
                                2))  # Le groupe 2 contient les 4 chiffres
                            if numeric_part > last_numeric_part:
                                last_numeric_part = numeric_part
                                last_full_serial = serial

            if last_full_serial:
                log(f"Dernier sérial trouvé dans le CSV: {last_full_serial}",
                    level="DEBUG")
                return last_full_serial
            else:
                log(f"Aucun sérial correspondant au format trouvé dans '{CSVSerialManager.SERIAL_CSV_FILE}'.",
                    level="INFO")
                return None

        except (IOError, FileNotFoundError) as e:
            log(f"Erreur d'IO lors de la lecture de '{CSVSerialManager.SERIAL_CSV_FILE}': {e}",
                level="ERROR")
            return None
        except Exception as e:
            log(f"Erreur inattendue lors de la lecture du dernier sérial: {e}",
                level="ERROR")
            return None

    @staticmethod
    def validate_and_update_serial(temp_serial_to_find, final_model_key):
        """
        Trouve une batterie par son QR code temporaire, met à jour son numéro de série et retourne les détails.
        """
        if not os.path.exists(CSVSerialManager.SERIAL_CSV_FILE):
            log(f"Fichier CSV '{CSVSerialManager.SERIAL_CSV_FILE}' non trouvé pour la validation.",
                level="ERROR")
            return None, None, None, None, None, None, None

        rows_to_write = []
        updated_in_memory = False
        details_for_print = {}
        header = []

        try:
            with open(CSVSerialManager.SERIAL_CSV_FILE,
                      mode='r',
                      newline='',
                      encoding='utf-8') as f_read:
                reader = csv.reader(f_read)
                header = next(reader, None)
                if not header:
                    return None, None, None, None, None, None, None
                rows_to_write.append(header)

                # Obtenir les index des colonnes importantes
                serial_col = header.index("NumeroSerie")
                type_col = header.index("type")
                qr_col = header.index("CodeAleatoireQR")
                ts_impression_col = header.index("TimestampImpression")
                ts_testdone_col = header.index("TimestampTestDone")

                for row in reader:
                    # Reconstituer le QR code temporaire à partir des données du CSV
                    material_letter = row[type_col]
                    numeric_part = row[serial_col][-4:]
                    current_temp_serial = f"{material_letter}{numeric_part}"

                    if current_temp_serial == temp_serial_to_find:
                        model_info = PrinterConfig.BATTERY_MODELS.get(
                            final_model_key)
                        if not model_info:
                            raise ValueError(
                                f"Modèle final '{final_model_key}' non trouvé."
                            )

                        # Construire le nouveau sérial
                        new_serial = f"RW-48v{model_info['ah']}{numeric_part}"

                        original_ah_match = re.search(r"RW-48v(\w+)",
                                                      row[serial_col])
                        original_model_changed = (
                            original_ah_match.group(1)
                            != 'XXX') if original_ah_match else True

                        # Mettre à jour la ligne
                        row[serial_col] = new_serial
                        row[ts_testdone_col] = datetime.now().isoformat()
                        updated_in_memory = True

                        details_for_print = {
                            "new_serial": new_serial,
                            "random_qr_code": row[qr_col],
                            "timestamp_impression": row[ts_impression_col],
                            "original_model_changed": original_model_changed,
                            "kwh": model_info['energy'],
                            "ah": model_info['ah'],
                            "type": row[type_col]
                        }
                        log(f"Validation: {temp_serial_to_find} -> {new_serial}. Changement modèle: {original_model_changed}",
                            level="INFO")

                    rows_to_write.append(row)

            if updated_in_memory:
                with open(CSVSerialManager.SERIAL_CSV_FILE,
                          mode='w',
                          newline='',
                          encoding='utf-8') as f_write:
                    writer = csv.writer(f_write)
                    writer.writerows(rows_to_write)

                log(f"Fichier CSV mis à jour avec le sérial validé: {details_for_print['new_serial']}",
                    level="INFO")
                return (details_for_print["new_serial"],
                        details_for_print["random_qr_code"],
                        details_for_print["timestamp_impression"],
                        details_for_print["original_model_changed"],
                        details_for_print["kwh"], details_for_print["ah"],
                        details_for_print["type"])
            else:
                log(f"Aucun sérial initial correspondant à '{temp_serial_to_find}' trouvé pour validation.",
                    level="WARNING")
                return None, None, None, None, None, None, None

        except Exception as e:
            log(f"Erreur lors de la validation du sérial: {e}", level="ERROR")
            return None, None, None, None, None, None, None

    @staticmethod
    def is_battery_in_sav(serial_number):
        """
        Vérifie si une batterie est actuellement en SAV (via le CSV principal).
        
        Args:
            serial_number (str): Numéro de série à vérifier
            
        Returns:
            bool: True si la batterie est en SAV, False sinon
        """
        try:
            if not os.path.exists(CSVSerialManager.SERIAL_CSV_FILE):
                log(f"Fichier CSV principal '{CSVSerialManager.SERIAL_CSV_FILE}' non trouvé pour vérification SAV de {serial_number}.",
                    level="DEBUG")
                return False

            with open(CSVSerialManager.SERIAL_CSV_FILE,
                      mode='r',
                      newline='',
                      encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("NumeroSerie") == serial_number:
                        # Vérifier le statut SAV
                        sav_status = row.get("sav_status", "False").strip()
                        is_sav = sav_status.lower() == "true"
                        log(f"Batterie {serial_number} - statut SAV: {sav_status} -> {is_sav}",
                            level="DEBUG")
                        return is_sav

            # Pas trouvé dans le CSV principal
            log(f"Batterie {serial_number} non trouvée dans le CSV principal",
                level="DEBUG")
            return False

        except Exception as e:
            log(f"Erreur lors de la vérification SAV pour {serial_number}: {e}",
                level="ERROR")
            return False

    @staticmethod
    def add_sav_entry(timestamp_arrivee, numero_serie):
        """Ajoute une nouvelle entrée SAV (arrivée)."""
        # Initialisation du CSV SAV si besoin
        log("DEBUG: Début de add_sav_entry()", level="INFO")
        CSVSerialManager.initialize_sav_csv()

        # 1. Ajouter dans le CSV SAV
        try:
            with open(CSVSerialManager.SAV_CSV_FILE,
                      mode='a',
                      newline='',
                      encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp_arrivee, numero_serie,
                                 ""])  # TimestampDepart vide au début
            log(f"Ajouté au CSV SAV: {timestamp_arrivee}, {numero_serie}",
                level="INFO")
        except IOError as e:
            log(f"Impossible d'écrire dans le fichier CSV SAV '{CSVSerialManager.SAV_CSV_FILE}': {e}",
                level="ERROR")
            return False
        except Exception as e:
            log(f"Erreur inattendue lors de l'écriture dans '{CSVSerialManager.SAV_CSV_FILE}': {e}",
                level="ERROR")
            return False

        # 2. Mettre à jour sav_status = True dans le CSV principal
        success_main = CSVSerialManager._update_main_csv_sav_status(
            numero_serie, "True")

        if success_main:
            log(f"SAV entrée complète pour {numero_serie}: CSV SAV + statut principal mis à jour",
                level="INFO")
            return True
        else:
            log(f"SAV entrée partielle pour {numero_serie}: CSV SAV OK mais échec mise à jour statut principal",
                level="WARNING")
            return False

    @staticmethod
    def update_sav_departure(serial_number_to_update, timestamp_depart):
        """Met à jour le TimestampDepart pour un NumeroSerie donné dans le CSV SAV."""
        if not os.path.exists(CSVSerialManager.SAV_CSV_FILE):
            log(
                f"Fichier CSV SAV '{CSVSerialManager.SAV_CSV_FILE}' non trouvé. Impossible de mettre à jour TimestampDepart pour {serial_number_to_update}.",
                level="ERROR",
            )
            return False

        rows_to_write = []
        updated_in_memory = False

        try:
            # 1. Mettre à jour le CSV SAV
            with open(CSVSerialManager.SAV_CSV_FILE,
                      mode='r',
                      newline='',
                      encoding='utf-8') as f_read:
                reader = csv.reader(f_read)
                header = next(reader, None)
                if not header:
                    log(f"Fichier CSV SAV '{CSVSerialManager.SAV_CSV_FILE}' est vide ou n'a pas d'entête.",
                        level="ERROR")
                    return False
                rows_to_write.append(header)

                # Rechercher la ligne avec le numéro de série (sans TimestampDepart)
                for row in reader:
                    if row and len(
                            row) >= 2 and row[1] == serial_number_to_update:
                        # Vérifier si TimestampDepart est vide (pas encore sorti de SAV)
                        if len(row) >= 3 and not row[2].strip():
                            # Mettre à jour le TimestampDepart
                            while len(row) < 3:
                                row.append("")
                            row[2] = timestamp_depart
                            updated_in_memory = True
                            log(
                                f"Ligne SAV pour {serial_number_to_update} sera mise à jour avec TimestampDepart: {timestamp_depart}",
                                level="INFO",
                            )
                    rows_to_write.append(row)

            if updated_in_memory:
                with open(CSVSerialManager.SAV_CSV_FILE,
                          mode='w',
                          newline='',
                          encoding='utf-8') as f_write:
                    writer = csv.writer(f_write)
                    writer.writerows(rows_to_write)
                log(
                    f"Fichier CSV SAV '{CSVSerialManager.SAV_CSV_FILE}' mis à jour avec TimestampDepart pour {serial_number_to_update}.",
                    level="INFO",
                )

                # 2. Mettre à jour sav_status = False dans le CSV principal
                success_main = CSVSerialManager._update_main_csv_sav_status(
                    serial_number_to_update, "False")

                if success_main:
                    log(f"SAV sortie complète pour {serial_number_to_update}: CSV SAV + statut principal mis à jour",
                        level="INFO")
                    return True
                else:
                    log(f"SAV sortie partielle pour {serial_number_to_update}: CSV SAV OK mais échec mise à jour statut principal",
                        level="WARNING")
                    return False
            else:
                log(
                    f"Aucun NumeroSerie en SAV (sans TimestampDepart) correspondant à '{serial_number_to_update}' trouvé dans '{CSVSerialManager.SAV_CSV_FILE}'.",
                    level="WARNING",
                )
                return False
        except Exception as e:
            log(f"Erreur lors de la mise à jour de TimestampDepart SAV pour {serial_number_to_update}: {e}",
                level="ERROR")
            return False

    @staticmethod
    def generate_next_numeric_part():
        """Génère la prochaine partie numérique en incrémentant la plus haute trouvée dans le CSV."""
        last_serial = CSVSerialManager.get_last_serial_from_csv()
        numeric_part_int = 0

        # Regex pour extraire uniquement les 4 derniers chiffres
        pattern = re.compile(r"(\d{4})$")

        if last_serial:
            match = pattern.search(last_serial)
            if match:
                try:
                    numeric_part_int = int(match.group(1)) + 1
                except (ValueError, IndexError):
                    log(f"Impossible de parser la partie numérique de '{last_serial}'. Réinitialisation.",
                        level="ERROR")
                    numeric_part_int = 0

        next_numeric_part_str = str(numeric_part_int).zfill(
            CSVSerialManager.SERIAL_NUMERIC_LENGTH)
        log(f"Prochaine partie numérique générée: {next_numeric_part_str}",
            level="INFO")
        return next_numeric_part_str

    @staticmethod
    def add_initial_serial_to_csv(timestamp, numeric_part, material_letter,
                                  code_aleatoire_qr):
        """Ajoute une nouvelle ligne au CSV pour la création initiale."""
        CSVSerialManager.initialize_serial_csv()

        # Construit le numéro de série initial avec des placeholders pour la capacité (Ah)
        # Exemple: RW-48vXXX0210
        initial_serial = f"RW-48vXXX{numeric_part}"

        try:
            with open(CSVSerialManager.SERIAL_CSV_FILE,
                      mode='a',
                      newline='',
                      encoding='utf-8') as f:
                writer = csv.writer(f)
                # Ajoute la lettre dans la nouvelle colonne "type"
                writer.writerow([
                    timestamp, initial_serial, code_aleatoire_qr, "", "",
                    material_letter.upper(), PrinterConfig.SOFTWARE_VERSION,
                    "False"
                ])
            log(f"Ajout initial au CSV: {initial_serial}, Type: {material_letter.upper()}",
                level="INFO")
            return True
        except IOError as e:
            log(f"Impossible d'écrire dans le fichier CSV '{CSVSerialManager.SERIAL_CSV_FILE}': {e}",
                level="ERROR")
            return False

    @staticmethod
    def update_csv_with_test_done_timestamp(serial_number_to_update,
                                            timestamp_done):
        """Met à jour le TimestampTestDone pour un NumeroSerie donné dans le CSV."""
        if not os.path.exists(CSVSerialManager.SERIAL_CSV_FILE):
            log(
                f"Fichier CSV '{CSVSerialManager.SERIAL_CSV_FILE}' non trouvé. Impossible de mettre à jour TimestampTestDone pour {serial_number_to_update}.",
                level="ERROR",
            )
            return False
        rows = []
        updated = False
        try:
            with open(CSVSerialManager.SERIAL_CSV_FILE,
                      mode='r',
                      newline='',
                      encoding='utf-8') as f_read:
                reader = csv.reader(f_read)
                header = next(reader)
                rows.append(header)
                for row in reader:
                    if row and len(
                            row) > 1 and row[1] == serial_number_to_update:
                        if len(row) > 3:
                            row[3] = timestamp_done
                        else:
                            row.extend([""] * (4 - len(row)))
                            row[3] = timestamp_done
                        if len(row) > 6:
                            row[6] = PrinterConfig.SOFTWARE_VERSION
                        else:
                            row.extend([""] * (7 - len(row)))
                            row[6] = PrinterConfig.SOFTWARE_VERSION
                        updated = True
                        log(
                            f"Ligne pour {serial_number_to_update} marquée avec TimestampTestDone: {timestamp_done} et version: {PrinterConfig.SOFTWARE_VERSION}",
                            level="INFO",
                        )
                    rows.append(row)
            if updated:
                with open(CSVSerialManager.SERIAL_CSV_FILE,
                          mode='w',
                          newline='',
                          encoding='utf-8') as f_write:
                    writer = csv.writer(f_write)
                    writer.writerows(rows)
                log(
                    f"Fichier CSV '{CSVSerialManager.SERIAL_CSV_FILE}' mis à jour avec TimestampTestDone et version pour {serial_number_to_update}.",
                    level="INFO",
                )
                return True
            else:
                log(
                    f"Aucun NumeroSerie correspondant à '{serial_number_to_update}' trouvé dans '{CSVSerialManager.SERIAL_CSV_FILE}' pour mettre à jour TimestampTestDone.",
                    level="WARNING",
                )
                return False
        except Exception as e:
            log(
                f"Erreur lors de la mise à jour de TimestampTestDone pour {serial_number_to_update} dans CSV: {e}",
                level="ERROR",
            )
            return False

    @staticmethod
    def update_csv_with_shipping_timestamp(serial_number_to_update,
                                           timestamp_shipping_iso):
        """Met à jour le TimestampExpedition pour un NumeroSerie donné dans le CSV."""
        if not os.path.exists(CSVSerialManager.SERIAL_CSV_FILE):
            log(
                f"Fichier CSV '{CSVSerialManager.SERIAL_CSV_FILE}' non trouvé. Impossible de mettre à jour TimestampExpedition pour {serial_number_to_update}.",
                level="ERROR",
            )
            return False

        rows_to_write = []
        updated_in_memory = False
        header_indices = {}

        try:
            with open(CSVSerialManager.SERIAL_CSV_FILE,
                      mode='r',
                      newline='',
                      encoding='utf-8') as f_read:
                reader = csv.reader(f_read)
                header = next(reader, None)
                if not header:
                    log(f"Fichier CSV '{CSVSerialManager.SERIAL_CSV_FILE}' est vide ou n'a pas d'entête.",
                        level="ERROR")
                    return False
                rows_to_write.append(header)

                for i, col_name in enumerate(header):
                    header_indices[col_name] = i

                if "NumeroSerie" not in header_indices or "TimestampExpedition" not in header_indices:
                    log(
                        f"Les colonnes 'NumeroSerie' ou 'TimestampExpedition' sont manquantes dans l'entête de {CSVSerialManager.SERIAL_CSV_FILE}.",
                        level="ERROR",
                    )
                    return False

                idx_serial = header_indices["NumeroSerie"]
                idx_shipping_ts = header_indices["TimestampExpedition"]

                for row in reader:
                    if row and len(row) > idx_serial and row[
                            idx_serial] == serial_number_to_update:
                        while len(row) <= idx_shipping_ts:
                            row.append("")
                        row[idx_shipping_ts] = timestamp_shipping_iso
                        updated_in_memory = True
                        log(
                            f"Ligne pour {serial_number_to_update} sera mise à jour avec TimestampExpedition: {timestamp_shipping_iso}",
                            level="INFO",
                        )
                    rows_to_write.append(row)

            if updated_in_memory:
                with open(CSVSerialManager.SERIAL_CSV_FILE,
                          mode='w',
                          newline='',
                          encoding='utf-8') as f_write:
                    writer = csv.writer(f_write)
                    writer.writerows(rows_to_write)
                log(
                    f"Fichier CSV '{CSVSerialManager.SERIAL_CSV_FILE}' mis à jour avec TimestampExpedition pour {serial_number_to_update}.",
                    level="INFO",
                )
                return True
            else:
                log(
                    f"Aucun NumeroSerie correspondant à '{serial_number_to_update}' trouvé dans '{CSVSerialManager.SERIAL_CSV_FILE}' pour mettre à jour TimestampExpedition.",
                    level="WARNING",
                )
                return False
        except Exception as e:
            log(f"Erreur lors de la mise à jour de TimestampExpedition pour {serial_number_to_update} dans CSV: {e}",
                level="ERROR")
            return False

    @staticmethod
    def _update_main_csv_sav_status(numero_serie, sav_status_value):
        """
        Met à jour le statut SAV dans le CSV principal.
        
        Args:
            numero_serie (str): Numéro de série à mettre à jour
            sav_status_value (str): "True" ou "False"
            
        Returns:
            bool: True si succès, False sinon
        """
        if not os.path.exists(CSVSerialManager.SERIAL_CSV_FILE):
            log(f"Fichier CSV principal '{CSVSerialManager.SERIAL_CSV_FILE}' non trouvé pour mise à jour SAV de {numero_serie}.",
                level="ERROR")
            return False

        rows_to_write = []
        updated_in_memory = False
        header_indices = {}

        try:
            with open(CSVSerialManager.SERIAL_CSV_FILE,
                      mode='r',
                      newline='',
                      encoding='utf-8') as f_read:
                reader = csv.reader(f_read)
                header = next(reader, None)
                if not header:
                    log(f"Fichier CSV principal '{CSVSerialManager.SERIAL_CSV_FILE}' est vide ou n'a pas d'entête.",
                        level="ERROR")
                    return False
                rows_to_write.append(header)

                # Créer un mapping des indices de colonnes
                for i, col_name in enumerate(header):
                    header_indices[col_name] = i

                # Vérifier si la colonne sav_status existe, sinon l'ajouter
                if "sav_status" not in header_indices:
                    header.append("sav_status")
                    header_indices["sav_status"] = len(header) - 1
                    rows_to_write[
                        0] = header  # Mettre à jour le header dans rows_to_write
                    log(f"Colonne 'sav_status' ajoutée au CSV principal",
                        level="INFO")

                if "NumeroSerie" not in header_indices:
                    log(f"Colonne 'NumeroSerie' manquante dans le CSV principal",
                        level="ERROR")
                    return False

                idx_serial = header_indices["NumeroSerie"]
                idx_sav_status = header_indices["sav_status"]

                for row in reader:
                    if row and len(row) > idx_serial and row[
                            idx_serial] == numero_serie:
                        # Étendre la ligne si nécessaire
                        while len(row) <= idx_sav_status:
                            row.append("")

                        # Mettre à jour le statut SAV
                        row[idx_sav_status] = sav_status_value
                        updated_in_memory = True
                        log(f"Statut SAV mis à jour pour {numero_serie}: {sav_status_value}",
                            level="INFO")

                    rows_to_write.append(row)

            if updated_in_memory or "sav_status" not in header_indices:  # Écrire aussi si on a ajouté la colonne
                with open(CSVSerialManager.SERIAL_CSV_FILE,
                          mode='w',
                          newline='',
                          encoding='utf-8') as f_write:
                    writer = csv.writer(f_write)
                    writer.writerows(rows_to_write)
                log(f"CSV principal mis à jour avec statut SAV pour {numero_serie}",
                    level="INFO")
                return True
            else:
                log(f"Numéro de série {numero_serie} non trouvé dans le CSV principal pour mise à jour SAV",
                    level="WARNING")
                return False

        except Exception as e:
            log(f"Erreur lors de la mise à jour du statut SAV pour {numero_serie}: {e}",
                level="ERROR")
            return False

    @staticmethod
    def get_sav_stats():
        """
        Récupère les statistiques SAV.
        
        Returns:
            dict: Statistiques SAV (batteries_en_sav, total_entrees_sav, etc.)
        """
        stats = {
            'batteries_en_sav': 0,
            'total_entrees_sav': 0,
            'sorties_sav_aujourd_hui': 0
        }

        try:
            if not os.path.exists(CSVSerialManager.SAV_CSV_FILE):
                return stats

            from datetime import datetime
            today_str = datetime.now().strftime("%Y-%m-%d")

            with open(CSVSerialManager.SAV_CSV_FILE,
                      mode='r',
                      newline='',
                      encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row and row.get('NumeroSerie'):
                        stats['total_entrees_sav'] += 1

                        # Vérifier si encore en SAV (TimestampDepart vide)
                        timestamp_depart = row.get('TimestampDepart',
                                                   '').strip()
                        if not timestamp_depart:
                            stats['batteries_en_sav'] += 1
                        else:
                            # Vérifier si sortie aujourd'hui
                            if timestamp_depart.startswith(today_str):
                                stats['sorties_sav_aujourd_hui'] += 1

        except Exception as e:
            log(f"Erreur calcul statistiques SAV: {e}", level="ERROR")

        return stats

    @staticmethod
    def get_details_for_reprint_from_csv(serial_number_to_find):
        """
        Cherche un NumeroSerie dans le CSV et retourne NumeroSerie, CodeAleatoireQR, et TimestampImpression.
        Retourne (None, None, None) si non trouvé.
        """
        try:
            if not os.path.exists(CSVSerialManager.SERIAL_CSV_FILE):
                log(
                    f"Fichier CSV '{CSVSerialManager.SERIAL_CSV_FILE}' non trouvé pour la réimpression de {serial_number_to_find}.",
                    level="WARNING",
                )
                return None, None, None
            found_serial = None
            found_random_code = None
            found_timestamp_impression = None
            with open(CSVSerialManager.SERIAL_CSV_FILE,
                      mode='r',
                      newline='',
                      encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("NumeroSerie") == serial_number_to_find:
                        found_serial = row["NumeroSerie"]
                        found_random_code = row.get("CodeAleatoireQR")
                        found_timestamp_impression = row.get(
                            "TimestampImpression")
            if found_serial and found_random_code and found_timestamp_impression:
                log(
                    f"Détails trouvés pour réimpression de {serial_number_to_find}: QR Code {found_random_code}, TimestampImpression {found_timestamp_impression}",
                    level="INFO",
                )
                return found_serial, found_random_code, found_timestamp_impression
            else:
                log(
                    f"Aucun enregistrement complet (S/N, QR, Timestamp) trouvé pour '{serial_number_to_find}' dans '{CSVSerialManager.SERIAL_CSV_FILE}' pour réimpression.",
                    level="WARNING",
                )
                return None, None, None
        except Exception as e:
            log(f"Erreur lors de la recherche de {serial_number_to_find} dans CSV pour réimpression: {e}",
                level="ERROR")
            return None, None, None

    @staticmethod
    def update_serial_for_downgrade(original_serial, new_serial):
        """
        Met à jour le numéro de série dans le CSV pour un downgrade.
        
        Args:
            original_serial (str): Le numéro de série d'origine à trouver.
            new_serial (str): Le nouveau numéro de série à enregistrer.
            
        Returns:
            bool: True si la mise à jour a réussi, False sinon.
        """
        if not os.path.exists(CSVSerialManager.SERIAL_CSV_FILE):
            log(f"Fichier CSV '{CSVSerialManager.SERIAL_CSV_FILE}' non trouvé pour le downgrade.",
                level="ERROR")
            return False

        rows_to_write = []
        updated_in_memory = False

        try:
            with open(CSVSerialManager.SERIAL_CSV_FILE,
                      mode='r',
                      newline='',
                      encoding='utf-8') as f_read:
                reader = csv.reader(f_read)
                header = next(reader, None)
                if not header:
                    return False
                rows_to_write.append(header)

                # Trouver la colonne "NumeroSerie"
                try:
                    serial_col_index = header.index("NumeroSerie")
                except ValueError:
                    log("Colonne 'NumeroSerie' non trouvée dans le CSV.",
                        level="ERROR")
                    return False

                # Lire et modifier la ligne correspondante
                for row in reader:
                    if row and len(row) > serial_col_index and row[
                            serial_col_index] == original_serial:
                        row[serial_col_index] = new_serial
                        updated_in_memory = True
                        log(f"Mise à jour du serial en mémoire: {original_serial} -> {new_serial}",
                            level="INFO")
                    rows_to_write.append(row)

            # Réécrire le fichier si une modification a eu lieu
            if updated_in_memory:
                with open(CSVSerialManager.SERIAL_CSV_FILE,
                          mode='w',
                          newline='',
                          encoding='utf-8') as f_write:
                    writer = csv.writer(f_write)
                    writer.writerows(rows_to_write)
                log(f"Fichier CSV mis à jour avec le nouveau serial: {new_serial}",
                    level="INFO")
                return True
            else:
                log(f"Aucun serial correspondant à '{original_serial}' trouvé pour le downgrade.",
                    level="WARNING")
                return False

        except Exception as e:
            log(f"Erreur lors de la mise à jour du serial pour le downgrade: {e}",
                level="ERROR")
            return False

    @staticmethod
    def search_battery_for_reprint(input_serial):
        """
        Recherche intelligente pour le reprint.
        Accepte : RW-48v... OU A0032
        Retourne : Dictionnaire avec toutes les infos ou None
        """
        import re
        if not os.path.exists(CSVSerialManager.SERIAL_CSV_FILE):
            return None

        # Analyse de l'entrée
        input_serial = input_serial.strip()
        target_digits = ""
        target_type = ""
        is_short_format = False

        # Est-ce un format court (A0032) ?
        match_short = re.match(r"^([A-E])(\d{4})$", input_serial.upper())
        if match_short:
            target_type = match_short.group(1)
            target_digits = match_short.group(2)
            is_short_format = True
        else:
            # On suppose un format long, on extrait les 4 derniers chiffres
            match_long = re.search(r"(\d{4})$", input_serial)
            if match_long:
                target_digits = match_long.group(1)
            else:
                return None  # Format inconnu

        try:
            with open(CSVSerialManager.SERIAL_CSV_FILE,
                      mode='r',
                      newline='',
                      encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    csv_serial = row.get("NumeroSerie", "")
                    csv_type = row.get("type", "")

                    # Extraction des 4 derniers chiffres du CSV
                    csv_match = re.search(r"(\d{4})$", csv_serial)
                    if not csv_match:
                        continue
                    csv_digits = csv_match.group(1)

                    # LOGIQUE DE MATCH
                    match_found = False

                    if is_short_format:
                        # Si on cherche A0032, il faut que Type=A et Digits=0032
                        if csv_digits == target_digits and csv_type == target_type:
                            match_found = True
                    else:
                        # Si on cherche RW...341, on cherche le serial exact
                        if csv_serial == input_serial:
                            match_found = True

                    if match_found:
                        # On a trouvé la ligne ! On prépare tout pour l'impression

                        # 1. Vérification Test Done
                        ts_test = row.get("TimestampTestDone", "").strip()
                        is_test_done = len(
                            ts_test) > 5  # S'il y a une date, c'est fait

                        # 2. Construction du Short Serial pour l'étiquette V1 (TOUJOURS)
                        # Ex: Type 'B' + Digits '0341' -> B0341
                        short_serial_v1 = f"{csv_type}{csv_digits}"

                        return {
                            "full_serial":
                            csv_serial,  # Pour Main/Shipping
                            "short_serial":
                            short_serial_v1,  # Pour V1
                            "random_code":
                            row.get("CodeAleatoireQR", ""),
                            "timestamp_impression":
                            row.get("TimestampImpression", ""),
                            "kwh":
                            0,  # Sera rempli par le handler si besoin via config
                            "ah":
                            0,  # Sera rempli par le handler si besoin via config
                            "type":
                            csv_type,
                            "is_test_done":
                            is_test_done
                        }

            return None  # Pas trouvé

        except Exception as e:
            log(f"Erreur recherche reprint: {e}", level="ERROR")
            return None
