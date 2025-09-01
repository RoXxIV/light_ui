# -*- coding: utf-8 -*-
"""
Gestionnaire pour les fichiers CSV et la génération de numéros de série.
"""
import csv
import os
import random
import string
from src.ui.system_utils import log
from .printer_config import PrinterConfig


class CSVSerialManager:
    """
    Classe pour gérer les opérations CSV et la génération de numéros de série.
    """
    # Configuration
    SERIAL_CSV_FILE = "printed_serials.csv"
    SERIAL_PREFIX = "RW-48v271"
    SERIAL_NUMERIC_LENGTH = 4
    SAV_CSV_FILE = "sav_batteries.csv"

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
                        "TimestampExpedition", "checker_name", "version",
                        "sav_status"
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
        """Lit le CSV et retourne le dernier NumeroSerie enregistré.
           Retourne None si le fichier est vide, n'existe pas, ou en cas d'erreur."""
        try:
            if not os.path.exists(CSVSerialManager.SERIAL_CSV_FILE):
                log(f"Le fichier CSV '{CSVSerialManager.SERIAL_CSV_FILE}' n'existe pas. Aucun dernier sérial.",
                    level="INFO")
                return None
            with open(CSVSerialManager.SERIAL_CSV_FILE,
                      mode='r',
                      newline='',
                      encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if not header:
                    log(f"Fichier CSV '{CSVSerialManager.SERIAL_CSV_FILE}' est vide (ou ne contient que l'entête).",
                        level="INFO")
                    return None

                last_row = None
                for row in reader:
                    if row:
                        last_row = row

                if last_row and len(last_row) > 1:
                    log(f"Dernière ligne lue du CSV: {last_row}",
                        level="DEBUG")
                    return last_row[1]
                else:
                    log(f"Aucune donnée trouvée dans '{CSVSerialManager.SERIAL_CSV_FILE}' après l'entête.",
                        level="INFO")
                    return None
        except FileNotFoundError:
            log(f"Le fichier CSV '{CSVSerialManager.SERIAL_CSV_FILE}' n'a pas été trouvé lors de la lecture du dernier sérial.",
                level="INFO")
            return None
        except IOError as e:
            log(f"Erreur d'IO lors de la lecture de '{CSVSerialManager.SERIAL_CSV_FILE}': {e}",
                level="ERROR")
            return None
        except Exception as e:
            log(f"Erreur inattendue lors de la lecture du dernier sérial de '{CSVSerialManager.SERIAL_CSV_FILE}': {e}",
                level="ERROR")
            return None

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
    def generate_next_serial_number():
        """Génère le prochain NumeroSerie en incrémentant le dernier du CSV."""
        last_serial = CSVSerialManager.get_last_serial_from_csv()

        if last_serial is None or not last_serial.startswith(
                CSVSerialManager.SERIAL_PREFIX):
            numeric_part_int = 0
        else:
            try:
                numeric_str = last_serial[len(CSVSerialManager.SERIAL_PREFIX):]
                numeric_part_int = int(numeric_str) + 1
            except ValueError:
                log(f"Impossible de parser la partie numérique du dernier sérial '{last_serial}'. Réinitialisation à 0.",
                    level="ERROR")
                numeric_part_int = 0

        next_numeric_part_str = str(numeric_part_int).zfill(
            CSVSerialManager.SERIAL_NUMERIC_LENGTH)
        next_serial = f"{CSVSerialManager.SERIAL_PREFIX}{next_numeric_part_str}"
        log(f"Prochain NumeroSerie généré: {next_serial}", level="INFO")
        return next_serial

    @staticmethod
    def add_serial_to_csv(timestamp,
                          numero_serie,
                          code_aleatoire_qr,
                          checker_name=""):
        """Ajoute une nouvelle ligne au fichier CSV des sérials."""
        # Initialisation du CSV si besoin
        log("DEBUG: Début de add_serial_to_csv()", level="INFO")
        CSVSerialManager.initialize_serial_csv()
        try:
            with open(CSVSerialManager.SERIAL_CSV_FILE,
                      mode='a',
                      newline='',
                      encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp, numero_serie, code_aleatoire_qr, "", "",
                    checker_name, PrinterConfig.SOFTWARE_VERSION, "False"
                ])
            log(f"Ajouté au CSV: {timestamp}, {numero_serie}, {code_aleatoire_qr}, {checker_name}, {PrinterConfig.SOFTWARE_VERSION}",
                level="INFO")
            return True
        except IOError as e:
            log(f"Impossible d'écrire dans le fichier CSV '{CSVSerialManager.SERIAL_CSV_FILE}': {e}",
                level="ERROR")
            return False
        except Exception as e:
            log(f"Erreur inattendue lors de l'écriture dans '{CSVSerialManager.SERIAL_CSV_FILE}': {e}",
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
