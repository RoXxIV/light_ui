#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestionnaire  pour impression, create, reprint et expedition.
"""

import re
import json
import time
import threading
from datetime import datetime
from src.ui.system_utils import log, is_printer_service_running
# Importe la configuration des modèles
from src.labels.printer_config import PrinterConfig


class ScanManager:
    """
    Gestionnaire de scan simplifié pour impression et expédition uniquement.
    """

    # === ÉTATS ===
    STATE_IDLE = 0
    # États pour le nouveau processus de création
    STATE_AWAIT_FINISH_SERIAL = 1
    STATE_AWAIT_FINISH_CONFIRM = 2
    STATE_AWAIT_EXPEDITION_SERIAL = 3
    STATE_AWAIT_EXPEDITION_CONFIRM = 4
    STATE_AWAIT_SAV_SERIAL = 5
    STATE_AWAIT_SAV_CONFIRM = 6
    STATE_AWAIT_QR_TEXT = 7
    STATE_AWAIT_QR_CONTENT = 8
    STATE_AWAIT_QR_CONFIRM = 9
    STATE_AWAIT_REPRINT_SERIAL = 10
    STATE_AWAIT_REPRINT_CONFIRM = 11

    # === CONSTANTES ===
    SERIAL_PATTERN = r"RW-48v(XXX|271|250|175)\d{4}"
    TIMEOUT_S = 30
    VALID_MATERIAL_LETTERS = ['A', 'B', 'C', 'D', 'E']

    def __init__(self, app):
        """
        Initialise le gestionnaire de scan simplifié.
        
        Args:
            app: Instance de l'application SimpleApp
        """
        self.app = app
        self.current_state = self.STATE_IDLE

        # Données temporaires
        self.serials_for_expedition = []
        self.expedition_mode_active = False
        self.serial_for_sav = None
        self.qr_text_to_print = None
        self.qr_content_to_encode = None
        # Données temporaires pour la finalisation
        self.validated_model = None
        self.temp_serial_to_validate = None
        self.serial_to_reprint = None
        # Timer de timeout
        self.timeout_timer_id = None

        log("ScanManager: Initialisé", level="INFO")

    def process_scan(self, scanned_text):
        """
        Point d'entrée principal pour traiter un scan.
        
        Args:
            scanned_text (str): Texte scanné/saisi
        """
        text = scanned_text.strip()
        text_lower = text.lower()

        log(f"ScanManager: Traitement '{text}' dans état {self.current_state}",
            level="INFO")

        # === COMMANDES GLOBALES ===
        if self.current_state == self.STATE_IDLE:
            if self._handle_global_commands(text_lower, text):
                return

        # === COMMANDE CANCEL (expédition ou SAV) ===
        if text_lower == "cancel" and (
                self.expedition_mode_active or
                self.current_state in (self.STATE_AWAIT_SAV_SERIAL, self.STATE_AWAIT_SAV_CONFIRM)):
            if self.expedition_mode_active:
                self._handle_expedition_cancel()
            else:
                self.app.add_message("❌ SAV annulé", "warning")
                self._reset_scan()
            return

        # === DISPATCH SELON L'ÉTAT ===
        handlers = {
            self.STATE_IDLE: self._handle_idle_state,
            self.STATE_AWAIT_FINISH_SERIAL: self._handle_await_finish_serial,
            self.STATE_AWAIT_FINISH_CONFIRM: self._handle_await_finish_confirm,
            self.STATE_AWAIT_EXPEDITION_SERIAL:
            self._handle_await_expedition_serial,
            self.STATE_AWAIT_EXPEDITION_CONFIRM:
            self._handle_await_expedition_confirm,
            self.STATE_AWAIT_SAV_SERIAL: self._handle_await_sav_serial,
            self.STATE_AWAIT_SAV_CONFIRM: self._handle_await_sav_confirm,
            self.STATE_AWAIT_QR_TEXT: self._handle_await_qr_text,
            self.STATE_AWAIT_QR_CONTENT: self._handle_await_qr_content,
            self.STATE_AWAIT_QR_CONFIRM: self._handle_await_qr_confirm,
            self.STATE_AWAIT_REPRINT_SERIAL: self._handle_await_reprint_serial,
            self.STATE_AWAIT_REPRINT_CONFIRM:
            self._handle_await_reprint_confirm,
        }

        handler = handlers.get(self.current_state)
        if handler:
            handler(text)
        else:
            log(f"ScanManager: État inconnu {self.current_state}",
                level="ERROR")
            self._reset_scan()

    def _handle_global_commands(self, text_lower, original_text):
        """
        Gère les commandes globales disponibles depuis IDLE.
        
        Returns:
            bool: True si une commande a été traitée
        """
        # === NOUVEAU: CREATE DYNAMIQUE ===
        if text_lower.startswith("create "):
            return self._handle_create_command(original_text)

        # === FINISH / VALIDATE ===
        elif text_lower.startswith("finish "):
            return self._handle_finish_command(original_text)

        # === EXPEDITION ===
        elif text_lower == "expedition":
            return self._handle_expedition_command()

        # === SAV ===
        elif text_lower == "sav":
            return self._handle_sav_command()

        # === QR ===
        elif text_lower == "new qr":
            return self._handle_new_qr_command()

        # === REPRINT ===
        elif text_lower == "reprint":
            return self._handle_reprint_command()

        return False

    def _handle_finish_command(self, text):
        """Gère la commande initiale 'finish <kWh>'."""
        try:
            model_key = text.split(" ", 1)[1].strip()
            if model_key not in PrinterConfig.BATTERY_MODELS:
                raise ValueError(f"Modèle '{model_key}' inconnu.")

            self.validated_model = model_key
            self._change_state(self.STATE_AWAIT_FINISH_SERIAL)
            self._update_ui(
                f"Modèle final: {self.validated_model} kWh",
                "Scannez le QR code intérieur de la batterie (ex: B0210)")
            self.app.add_message(
                f"Prêt à finaliser en {self.validated_model} kWh.", "info")
            self._start_timeout()

        except (IndexError, ValueError) as e:
            valid_models = ", ".join(PrinterConfig.BATTERY_MODELS.keys())
            self._update_ui("❌ Commande invalide",
                            f"Utilisez: finish [{valid_models}]")
            self.app.add_message(f"Erreur: {e}", "error")
            self._reset_scan()
        return True

    def _handle_await_finish_serial(self, text):
        """Gère l'attente du scan du QR code intérieur."""
        # Le QR code est de la forme <LETTRE><NUMERIC_PART>
        temp_serial = text.strip().upper()

        # Validation simple du format
        if not (len(temp_serial) == 5 and temp_serial[0]
                in self.VALID_MATERIAL_LETTERS and temp_serial[1:].isdigit()):
            self._update_ui(
                "❌ QR code invalide",
                "Format attendu : une lettre suivie de 4 chiffres (ex: B0210)."
            )
            self.app.add_message(f"Format de QR code invalide : {temp_serial}",
                                 "error")
            return

        self.temp_serial_to_validate = temp_serial
        self._change_state(self.STATE_AWAIT_FINISH_CONFIRM)
        self._update_ui(
            f"Batterie '{temp_serial}' identifiée",
            f"Re-scannez 'finish {self.validated_model}' pour valider et imprimer."
        )
        if hasattr(self.app, 'info_panel'):
            self.app.info_panel.show_finish_confirm_button()
        self._start_timeout()

    def _is_finish_combination_valid(self, material_letter, model_key):
        """
        Vérifie si le modèle de finition est compatible avec le type de matériau.
        
        Args:
            material_letter (str): La lettre du matériau (A, B, C, D, E).
            model_key (str): La clé du modèle de finition (ex: "13", "12", "8.4").
            
        Returns:
            bool: True si la combinaison est valide, False sinon.
            str: Un message d'erreur explicite en cas d'échec.
        """
        # Règles de compatibilité
        valid_combinations = {
            'A': ['13', '12'],
            'B': ['13', '12'],
            'C': ['13', '12'],
            'D': ['8.4'],
            'E': ['8.4']
        }

        allowed_models = valid_combinations.get(material_letter)

        if not allowed_models:
            return False, f"Le type de matériau '{material_letter}' est inconnu."

        if model_key not in allowed_models:
            error_message = f"Type '{material_letter}' incompatible avec {model_key}kWh. Modèles autorisés: {', '.join(allowed_models)}kWh."
            return False, error_message

        return True, "Combinaison valide."

    def _handle_await_finish_confirm(self, text):
        """Gère la confirmation finale et envoie la demande de validation."""
        expected_command = f"finish {self.validated_model}"

        if text.lower().strip() != expected_command:
            self._update_ui("❌ Confirmation incorrecte",
                            f"Attendu: '{expected_command}'")
            self.app.add_message(f"Confirmation échouée. Reçu: '{text}'",
                                 "error")
            self._delayed_reset(2000)
            return

        if not self.temp_serial_to_validate:
            log("ScanManager: tentive de validation sans QR code temporaire.",
                level="ERROR")
            self._update_ui("❌ Erreur interne",
                            "Aucun QR code en mémoire. Veuillez recommencer.")
            self._reset_scan()
            return

        material_letter = self.temp_serial_to_validate[0]
        is_valid, error_message = self._is_finish_combination_valid(
            material_letter, self.validated_model)

        if not is_valid:
            self._update_ui("❌ Validation échouée", error_message)
            self.app.add_message(f"Erreur de validation: {error_message}",
                                 "error")
            self._reset_scan()
            return
        # --- FIN DES VÉRIFICATIONS ---

        # Envoi MQTT au service d'impression
        if self.app.mqtt_client and self.app.mqtt_client.is_connected():
            payload = json.dumps({
                "temp_serial": self.temp_serial_to_validate,
                "final_model_key": self.validated_model
            })
            # Nous utiliserons un nouveau topic pour cette action
            self.app.mqtt_client.publish("printer/validate_battery",
                                         payload,
                                         qos=1)

            self._update_ui(
                "✅ Validation en cours...",
                f"Finalisation de '{self.temp_serial_to_validate}' en {self.validated_model} kWh."
            )
            self.app.add_message("Demande de validation envoyée.", "success")
        else:
            self._update_ui("❌ Erreur MQTT", "Client déconnecté")
            self.app.add_message("❌ Impossible d'envoyer - MQTT déconnecté",
                                 "error")

        self._reset_scan()

    def _handle_create_command(self, text):
        """Gère la nouvelle commande create <lettre>."""
        if not is_printer_service_running():
            self._update_ui("❌ Service d'impression inactif",
                            "Impossible de créer une étiquette")
            self.app.add_message("❌ Service d'impression non détecté", "error")
            return True

        try:
            letter = text.split(" ", 1)[1].strip().upper()
            if letter not in self.VALID_MATERIAL_LETTERS:
                raise ValueError(f"Lettre matériau '{letter}' invalide.")

            # Dictionnaire de correspondance pour les messages
            material_descriptions = {
                'A': "28.8Kwh Alu",
                'B': "14.4 Kwh Alu",
                'C': "14.4 Kwh Acier",
                'D': "9.6 Kwh Alu",
                'E': "9.6 Kwh Acier"
            }
            description = material_descriptions.get(
                letter, f"Matériau {letter}"
            )  # Fallback si la lettre n'est pas dans le dico

            # Envoi MQTT
            if self.app.mqtt_client and self.app.mqtt_client.is_connected():
                payload = json.dumps({"material_letter": letter})
                self.app.mqtt_client.publish("printer/create_label",
                                             payload,
                                             qos=1)

                # Mise à jour des messages avec la nouvelle description
                self._update_ui("✅ Création en cours...",
                                f"Type: {description}")
                self.app.add_message(
                    f"Demande de création à partir d'une {description} envoyée.",
                    "success")
            else:
                self._update_ui("❌ Erreur MQTT", "Client déconnecté")
                self.app.add_message(
                    "❌ Impossible d'envoyer - MQTT déconnecté", "error")

        except (IndexError, ValueError) as e:
            valid_letters = ", ".join(self.VALID_MATERIAL_LETTERS)
            self._update_ui("❌ Commande invalide",
                            f"Utilisez: create [{valid_letters}]")
            self.app.add_message(f"Erreur: {e}", "error")

        # La création est une action unique, on retourne à l'état IDLE
        # self._reset_scan()
        return True

    def _handle_expedition_command(self):
        """Gère la commande expedition."""
        if not is_printer_service_running():
            self._update_ui("❌ Service d'impression inactif",
                            "Expédition impossible")
            self.app.add_message("❌ Service d'impression non détecté", "error")
            return True

        if not self.expedition_mode_active:
            # Démarrer le mode expédition
            self._change_state(self.STATE_AWAIT_EXPEDITION_SERIAL)
            self.expedition_mode_active = True
            self.serials_for_expedition = []

            self._update_ui(
                "📦 Mode Expédition",
                "Scanner les numéros de série (ou 'expedition' pour terminer)")
            self.app.add_message("📦 Mode expédition activé", "info")
        else:
            # Terminer le mode expédition
            self._change_state(self.STATE_AWAIT_EXPEDITION_CONFIRM)
            self._handle_expedition_finalize()

        return True

    def _handle_await_expedition_confirm(self, text):
        """Gère la confirmation finale d'expédition."""
        # Cette méthode est appelée après avoir scanné "expedition" une 2e fois
        # La finalisation se fait directement dans _handle_expedition_finalize()
        pass

    def _handle_end_command(self):
        """Gère la commande end (arrêt services externes)."""
        self._update_ui("⏹️ Commande END", "Signal d'arrêt envoyé")
        self.app.add_message("⏹️ Commande END exécutée", "warning")
        # Vous pouvez ajouter ici la logique pour arrêter des services externes
        return True

    def _handle_reset_services_command(self):
        """Gère la commande reset (redémarrage services)."""
        self._update_ui("🔄 Reset Services", "Commande de reset envoyée")
        self.app.add_message("🔄 Reset des services demandé", "warning")
        # Vous pouvez ajouter ici la logique pour redémarrer des services
        return True

    def _handle_idle_state(self, text):
        """Gère l'état IDLE (défaut)."""
        # Si ce n'est pas une commande reconnue, l'interpréter comme un serial
        serial = self._extract_serial(text)
        if serial:
            self._update_ui(f"📋 Série détectée: {serial}",
                            "Utilisez 'reprint' pour réimprimer")
            self.app.add_message(f"📋 Numéro de série détecté: {serial}",
                                 "info")
        else:
            self._update_ui("❓ Commande inconnue",
                            "Voir la liste des commandes en bas")
            self.app.add_message(f"❓ Commande non reconnue: {text}", "warning")

    def _handle_await_expedition_serial(self, text):
        """Gère l'attente des serials pour expédition."""
        # Vérifier si c'est la commande pour terminer
        if text.lower().strip() == "expedition":
            self._change_state(self.STATE_AWAIT_EXPEDITION_CONFIRM)
            self._handle_expedition_finalize()
            return

        serial = self._extract_serial(text)
        if not serial:
            self._update_ui(
                "❌ Série invalide",
                "Format: RW-48v271XXXX ou 'expedition' pour terminer")
            self.app.add_message(f"❌ Format invalide: {text}", "error")
            return

        # Refuser les batterie non terminé "XXX"
        if "XXX" in serial:
            self._update_ui("❌ Batterie non finie",
                            "Refusé: Batterie non terminée aH non définie")
            self.app.add_message(f"❌ Batterie non terminée: {serial}", "error")
            return  # Ne pas ajouter la batterie, retour immediat

        if serial not in self.serials_for_expedition:
            self.serials_for_expedition.append(serial)
            self.app.add_message(f"➕ Ajouté: {serial}", "success")
            #Vérifier si c'est un retour SAV
            self._check_and_handle_sav_return(serial)
        else:
            self.app.add_message(f"⚠️ Déjà dans la liste: {serial}", "warning")

        count = len(self.serials_for_expedition)
        self._update_ui(
            f"📦 {count} batterie(s) scannée(s)",
            "Scanner plus de séries ou 'expedition' pour terminer")

    def _check_and_handle_sav_return(self, serial):
        """
        Vérifie si une batterie est en SAV et la traite automatiquement.
        
        Args:
            serial (str): Numéro de série à vérifier
        """
        try:
            from src.db import SQLiteManager

            if SQLiteManager.is_battery_in_sav(serial):
                self.app.add_message(f"🔧 Retour SAV détecté: {serial}", "info")

                # Préparer pour la sortie SAV automatique lors de la finalisation
                log(f"ScanManager: Batterie {serial} marquée pour sortie SAV automatique",
                    level="INFO")

        except Exception as e:
            log(f"ScanManager: Erreur vérification SAV pour {serial}: {e}",
                level="ERROR")

    def _handle_expedition_finalize(self):
        """Finalise l'expédition."""
        if not self.serials_for_expedition:
            self._update_ui("❌ Aucune batterie", "Expédition annulée")
            self.app.add_message("❌ Aucune batterie scannée pour l'expédition",
                                 "error")
            self._reset_scan()
            return

        if not (self.app.mqtt_client and self.app.mqtt_client.is_connected()):
            self._update_ui("❌ MQTT déconnecté",
                            "Impossible de traiter l'expédition")
            self.app.add_message("❌ MQTT déconnecté - expédition échouée",
                                 "error")
            self._reset_scan()
            return

        # Traiter l'expédition
        timestamp_iso = datetime.now().isoformat()
        topic_expedition = "printer/update_shipping_timestamp"
        topic_sav_departure = "printer/sav_departure"

        success_count = 0
        sav_count = 0
        sav_serials = []  # Liste pour stocker les serials SAV

        for serial in self.serials_for_expedition:
            try:
                from src.db import SQLiteManager

                # Vérifier que la batterie existe avant de publier
                if not SQLiteManager.battery_exists(serial):
                    log(f"ScanManager: Batterie {serial} introuvable - expédition bloquée",
                        level="ERROR")
                    self.app.add_message(f"❌ Batterie inconnue: {serial}", "error")
                    continue

                # Vérifier AVANT si c'est une batterie SAV
                is_sav_battery = SQLiteManager.is_battery_in_sav(serial)

                if is_sav_battery:
                    sav_serials.append(serial)
                    # SEULEMENT sortie SAV, PAS d'expédition normale
                    payload_sav = {
                        "serial_number": serial,
                        "timestamp_depart": timestamp_iso
                    }
                    self.app.mqtt_client.publish(topic_sav_departure,
                                                 json.dumps(payload_sav),
                                                 qos=1)
                    sav_count += 1
                    self.app.add_message(f"  Sortie SAV: {serial}", "info")
                else:
                    # Expédition normale uniquement
                    payload_expedition = {
                        "serial_number": serial,
                        "timestamp_expedition": timestamp_iso
                    }
                    self.app.mqtt_client.publish(
                        topic_expedition,
                        json.dumps(payload_expedition),
                        qos=1)

                success_count += 1

            except Exception as e:
                log(f"ScanManager: Erreur expédition {serial}: {e}",
                    level="ERROR")

        if success_count == len(self.serials_for_expedition):
            msg = f"✅ {success_count} batteries expédiées"
            if sav_count > 0:
                msg += f" (dont {sav_count} retours SAV)"

            self._update_ui(msg, "Mise à jour CSV et email en cours...")
            self.app.add_message(
                f"✅ Expédition réussie: {success_count} batteries", "success")

            if sav_count > 0:
                self.app.add_message(
                    f"🔧 Sorties SAV automatiques: {sav_count}", "success")

            # Afficher la liste dans les messages
            for serial in self.serials_for_expedition:
                self.app.add_message(f"  📦 {serial}", "info")

            # Envoyer l'email d'expédition
            self._send_expedition_email(self.serials_for_expedition,
                                        timestamp_iso, sav_serials)
        else:
            self._update_ui(
                f"⚠️ Expédition partielle",
                f"{success_count}/{len(self.serials_for_expedition)} réussies")
            self.app.add_message(
                f"⚠️ Expédition partielle: {success_count}/{len(self.serials_for_expedition)}",
                "warning")

        self._reset_scan()

    def _handle_expedition_cancel(self):
        """Gère l'annulation de l'expédition."""
        count = len(self.serials_for_expedition)
        self._update_ui("❌ Expédition annulée", f"{count} batteries ignorées")
        self.app.add_message(f"❌ Expédition annulée ({count} batteries)",
                             "warning")
        self._reset_scan()

    def _handle_sav_command(self):
        """Gère la commande SAV."""
        if not is_printer_service_running():
            self._update_ui("❌ Service d'impression inactif", "SAV impossible")
            self.app.add_message("❌ Service d'impression non détecté", "error")
            return True

        self._change_state(self.STATE_AWAIT_SAV_SERIAL)
        self._update_ui("🔧 Mode SAV",
                        "Scanner le numéro de série à enregistrer en SAV")
        self.app.add_message("🔧 Mode SAV activé", "info")
        self._start_timeout()
        return True

    def _handle_await_sav_serial(self, text):
        """Gère l'attente du serial pour SAV."""
        serial = self._extract_serial(text)
        if not serial:
            self._update_ui("❌ Série invalide",
                            "Format attendu: RW-48v271XXXX")
            self.app.add_message(f"❌ Format de série invalide: {text}",
                                 "error")
            self._delayed_reset(2000)
            return

        # Refuser les batterie non terminé "XXX"
        if "XXX" in serial:
            self._update_ui("❌ Batterie non finie",
                            "Refusé: Batterie non terminée")
            self.app.add_message(f"❌ Batterie non terminée: {serial}", "error")
            self._delayed_reset(2000)
            return

        self.serial_for_sav = serial
        self._change_state(self.STATE_AWAIT_SAV_CONFIRM)

        self._update_ui(f"✅ Série SAV: {serial}",
                        "Scanner 'sav' pour confirmer l'entrée")
        self.app.add_message(f"✅ Série sélectionnée pour SAV: {serial}",
                             "success")
        self._start_timeout()

    def _handle_await_sav_confirm(self, text):
        """Gère la confirmation SAV."""
        if text.lower().strip() != "sav":
            self._update_ui("❌ Confirmation incorrecte",
                            "Scanner 'sav' pour confirmer")
            self.app.add_message(f"❌ Attendu 'sav', reçu: {text}", "error")
            self._delayed_reset(2000)
            return

        # Envoyer la demande SAV via MQTT
        if self.app.mqtt_client and self.app.mqtt_client.is_connected():
            payload = json.dumps({
                "serial_number":
                self.serial_for_sav,
                "timestamp_sav_arrivee":
                datetime.now().isoformat(),
                "technicien":
                "Scanner_User"  # Optionnel pour futur usage
            })
            self.app.mqtt_client.publish("printer/sav_entry", payload, qos=1)

            self._update_ui("🔧 SAV enregistré",
                            f"Série: {self.serial_for_sav}")
            self.app.add_message(
                f"🔧 SAV enregistré pour {self.serial_for_sav}", "success")
        else:
            self._update_ui("❌ Erreur MQTT", "Impossible d'enregistrer le SAV")
            self.app.add_message("❌ MQTT déconnecté - SAV échoué", "error")

        self._reset_scan()

    def _extract_serial(self, text):
        """
        Extrait un numéro de série valide du texte.
        
        Returns:
            str|None: Numéro de série ou None
        """
        match = re.search(self.SERIAL_PATTERN, text)
        return match.group(0) if match else None

    def _change_state(self, new_state):
        """Change l'état du scanner."""
        log(f"ScanManager: État {self.current_state} -> {new_state}",
            level="DEBUG")
        self.current_state = new_state
        self._cancel_timeout()

    def _start_timeout(self):
        """Démarre le timer de timeout."""
        self._cancel_timeout()
        self.timeout_timer_id = self.app.after(self.TIMEOUT_S * 1000,
                                               self._timeout_expired)

    def _cancel_timeout(self):
        """Annule le timer de timeout."""
        if self.timeout_timer_id:
            try:
                self.app.after_cancel(self.timeout_timer_id)
            except ValueError:
                pass
            self.timeout_timer_id = None

    def _timeout_expired(self):
        """Appelée quand le timeout expire."""
        log("ScanManager: Timeout expiré", level="INFO")
        self._update_ui("⏰ Timeout", "Opération annulée")
        self.app.add_message("⏰ Timeout - opération annulée", "warning")
        self._reset_scan()

    def _delayed_reset(self, delay_ms):
        """Reset avec délai."""
        self._cancel_timeout()
        self.app.after(delay_ms, self._reset_scan)

    def _reset_scan(self):
        """Remet le scanner à l'état initial."""
        log("ScanManager: Reset", level="DEBUG")

        self.current_state = self.STATE_IDLE
        self.serials_for_expedition = []
        self.expedition_mode_active = False
        self.serial_for_sav = None
        self.material_letter = None
        self.validated_model = None
        self.temp_serial_to_validate = None

        self._cancel_timeout()

        # Remettre les boutons à leur état initial
        if hasattr(self.app, 'info_panel'):
            self.app.info_panel.reset_action_buttons()

        self._update_ui("Prêt.", "Veuillez scanner ou saisir une commande...")

    def _send_expedition_email(self,
                               serial_numbers,
                               timestamp_expedition,
                               sav_serials=None):
        """
        Envoie l'email d'expédition de manière asynchrone.
        
        Args:
            serial_numbers (list): Liste des numéros de série expédiés
            timestamp_expedition (str): Timestamp ISO d'expédition
        """

        def send_email_async():
            try:
                # Import des modules email ici pour éviter les dépendances au démarrage
                from src.ui.email import EmailTemplates, email_config
                import smtplib
                from email.mime.text import MIMEText
                from email.mime.multipart import MIMEMultipart
                import socket

                # Vérifier la configuration email
                if not email_config.is_configured():
                    missing_items = email_config.get_missing_config_items()
                    log(f"ScanManager: Config email incomplète: {missing_items}",
                        level="ERROR")
                    self.app.after(
                        0, lambda: self.app.add_message(
                            "❌ Configuration email manquante", "error"))
                    return

                # Générer le contenu de l'email
                try:
                    subject = EmailTemplates.generate_expedition_subject(
                        timestamp_expedition)
                    text_content, html_content = EmailTemplates.generate_expedition_email_content(
                        serial_numbers, timestamp_expedition, sav_serials)
                except Exception as template_error:
                    log(f"ScanManager: Erreur template email: {template_error}",
                        level="ERROR")
                    self.app.after(
                        0, lambda: self.app.add_message(
                            "❌ Erreur génération email", "error"))
                    return

                # Créer le message MIME
                message = MIMEMultipart("alternative")
                message["Subject"] = subject
                message["From"] = email_config.gmail_user
                message["To"] = ", ".join(email_config.recipient_emails)

                # Ajouter le contenu
                part_text = MIMEText(text_content, "plain")
                part_html = MIMEText(html_content, "html")
                message.attach(part_text)
                message.attach(part_html)

                # Envoyer l'email
                server = smtplib.SMTP_SSL(email_config.smtp_server,
                                          email_config.smtp_port)
                server.ehlo()
                server.login(email_config.gmail_user,
                             email_config.gmail_password)
                server.sendmail(email_config.gmail_user,
                                email_config.recipient_emails,
                                message.as_string())
                server.close()

                # Succès
                log(f"ScanManager: Email expédition envoyé pour {len(serial_numbers)} batteries",
                    level="INFO")
                self.app.after(
                    0, lambda: self.app.add_message(
                        f"📧 Email d'expédition envoyé ({len(serial_numbers)} batteries)",
                        "success"))

            except smtplib.SMTPAuthenticationError:
                log("ScanManager: Erreur authentification email",
                    level="ERROR")
                self.app.after(
                    0, lambda: self.app.add_message(
                        "❌ Erreur authentification email", "error"))

            except (socket.gaierror, OSError) as e:
                log(f"ScanManager: Erreur réseau email: {e}", level="ERROR")
                self.app.after(
                    0, lambda: self.app.add_message(
                        "❌ Erreur réseau - email non envoyé", "error"))

            except Exception as e:
                log(f"ScanManager: Erreur email inattendue: {e}",
                    level="ERROR")
                self.app.after(
                    0, lambda: self.app.add_message("❌ Erreur envoi email",
                                                    "error"))

        # Lancer l'envoi dans un thread séparé pour ne pas bloquer l'UI
        import threading
        email_thread = threading.Thread(target=send_email_async, daemon=True)
        email_thread.start()

        # Indiquer que l'envoi est en cours
        self.app.add_message("📧 Envoi email en cours...", "info")

    def _update_ui(self, msg1, msg2):
        """Met à jour les labels de réponse."""
        self.app.update_response_labels(msg1, msg2)

    def _handle_new_qr_command(self):
        """Gère la commande new qr."""
        if not is_printer_service_running():
            self._update_ui("❌ Service d'impression inactif", "QR impossible")
            self.app.add_message("❌ Service d'impression non détecté", "error")
            return True

        self._change_state(self.STATE_AWAIT_QR_TEXT)
        self._update_ui("📄 Mode QR", "Saisir le texte pour le QR code")
        self.app.add_message("📄 Mode création QR activé", "info")
        self._start_timeout()
        return True

    def _handle_await_qr_text(self, text):
        """Gère l'attente du texte à afficher sur l'étiquette."""
        display_text = text.strip()
        if not display_text:
            self._update_ui("❌ Texte vide",
                            "Veuillez saisir un texte à afficher.")
            return

        self.qr_text_to_print = display_text
        self._change_state(
            self.STATE_AWAIT_QR_CONTENT)  # Transition vers le nouvel état
        self._update_ui(f"Texte affiché: '{display_text}'",
                        "Maintenant, saisissez le contenu pour le QR code.")
        self._start_timeout()

    def _handle_await_qr_content(self, text):
        """Gère l'attente du contenu pour le QR code."""
        qr_content = text.strip()
        if not qr_content:
            self._update_ui("❌ Contenu vide",
                            "Veuillez saisir un contenu pour le QR code.")
            return

        self.qr_content_to_encode = qr_content
        self._change_state(self.STATE_AWAIT_QR_CONFIRM)
        self._update_ui(f"Contenu QR: '{qr_content}'",
                        "Re-scannez 'new qr' pour confirmer et imprimer.")
        self._start_timeout()

    def _handle_await_qr_confirm(self, text):
        """Gère la confirmation finale et envoie les deux textes via MQTT."""
        if text.lower().strip() != "new qr":
            self._update_ui("❌ Confirmation incorrecte",
                            "Scanner 'new qr' pour confirmer")
            self._delayed_reset(2000)
            return

        if self.app.mqtt_client and self.app.mqtt_client.is_connected():
            payload = json.dumps({
                "display_text": self.qr_text_to_print,
                "qr_content": self.qr_content_to_encode
            })
            self.app.mqtt_client.publish("printer/create_qr", payload, qos=1)

            self._update_ui("📄 QR personnalisé envoyé",
                            f"Texte: {self.qr_text_to_print}")
            self.app.add_message("Demande de QR personnalisé envoyée.",
                                 "success")
        else:
            self._update_ui("❌ Erreur MQTT", "Impossible d'envoyer la demande")

        self._reset_scan()


# ==========================================
# LOGIQUE REPRINT
# ==========================================

    def _handle_reprint_command(self):
        """Active le mode réimpression."""
        if not is_printer_service_running():
            self._update_ui("❌ Service inactif", "Réimpression impossible")
            return True

        self._change_state(self.STATE_AWAIT_REPRINT_SERIAL)
        self._update_ui("🔄 Mode Réimpression",
                        "Scannez le serial (RW-48v... ou A0032)")
        self.app.add_message("🔄 Mode réimpression activé", "info")
        self._start_timeout()
        return True

    def _handle_await_reprint_serial(self, text):
        """Traite le serial scanné (Format Long ou Court)."""
        text = text.strip()
        serial = None

        # 1. Essayer d'extraire un serial long (RW-48v...)
        serial = self._extract_serial(text)

        # 2. Si pas trouvé, vérifier le format court (A0032)
        if not serial:
            # Regex : Une lettre (A-E) suivie de 4 chiffres
            match_short = re.match(r"^([A-Ee])(\d{4})$", text)
            if match_short:
                serial = text.upper()  # On normalise (ex: a0032 -> A0032)

        if not serial:
            self._update_ui("❌ Série invalide", "Attendu : RW-48v... ou A0000")
            self.app.add_message(f"❌ Format non reconnu : {text}", "error")
            return

        self.serial_to_reprint = serial
        self._change_state(self.STATE_AWAIT_REPRINT_CONFIRM)
        self._update_ui(f"✅ Série : {serial}",
                        "Scannez 'reprint' pour confirmer")
        self.app.add_message(f"✅ Série sélectionnée pour reprint : {serial}",
                             "success")
        self._start_timeout()

    def _handle_await_reprint_confirm(self, text):
        """Confirme et envoie la demande de reprint."""
        if text.lower().strip() != "reprint":
            self._update_ui("❌ Confirmation incorrecte", "Attendu : 'reprint'")
            self._delayed_reset(2000)
            return

        if self.app.mqtt_client and self.app.mqtt_client.is_connected():
            # On envoie le serial (court ou long) au service d'impression
            # C'est le service d'impression qui fera la recherche intelligente dans le CSV
            payload = json.dumps({"serial_to_reprint": self.serial_to_reprint})

            # Le topic est défini dans PrinterConfig.MQTT_TOPIC_REQUEST_FULL_REPRINT
            topic = "printer/request_full_reprint"

            self.app.mqtt_client.publish(topic, payload, qos=1)

            self._update_ui("🖨️ Réimpression lancée",
                            f"Pour : {self.serial_to_reprint}")
            self.app.add_message(
                f"🖨️ Demande de reprint envoyée pour {self.serial_to_reprint}",
                "success")
        else:
            self._update_ui("❌ Erreur MQTT", "Non connecté")
            self.app.add_message("❌ Échec envoi reprint (MQTT déconnecté)",
                                 "error")

        self._reset_scan()
