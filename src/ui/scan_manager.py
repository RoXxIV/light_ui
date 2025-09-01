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


class ScanManager:
    """
    Gestionnaire de scan simplifié pour impression et expédition uniquement.
    """

    # === ÉTATS ===
    STATE_IDLE = 0
    STATE_AWAIT_REPRINT_SERIAL = 1
    STATE_AWAIT_REPRINT_CONFIRM = 2
    STATE_AWAIT_EXPEDITION_SERIAL = 3
    STATE_AWAIT_EXPEDITION_CONFIRM = 4
    STATE_AWAIT_SAV_SERIAL = 5
    STATE_AWAIT_SAV_CONFIRM = 6

    # === CONSTANTES ===
    SERIAL_PATTERN = r"RW-48v271[A-Za-z0-9]{4}"
    TIMEOUT_S = 30

    def __init__(self, app):
        """
        Initialise le gestionnaire de scan simplifié.
        
        Args:
            app: Instance de l'application SimpleApp
        """
        self.app = app
        self.current_state = self.STATE_IDLE

        # Données temporaires
        self.serial_to_reprint = None
        self.serials_for_expedition = []
        self.expedition_mode_active = False
        self.serial_for_sav = None

        # Timer de timeout
        self.timeout_timer_id = None

        log("ScanManager: Initialisé", level="INFO")

    def process_scan(self, scanned_text):
        """
        Point d'entrée principal pour traiter un scan.
        
        Args:
            scanned_text (str): Texte scanné/saisi
        """
        text = scanned_text.strip().lower()

        log(f"ScanManager: Traitement '{text}' dans état {self.current_state}",
            level="INFO")

        # === COMMANDES GLOBALES ===
        if self.current_state == self.STATE_IDLE:
            if self._handle_global_commands(text, scanned_text):
                return

        # === COMMANDE CANCEL (en mode expédition) ===
        if text == "cancel" and self.expedition_mode_active:
            self._handle_expedition_cancel()
            return

        # === DISPATCH SELON L'ÉTAT ===
        handlers = {
            self.STATE_IDLE: self._handle_idle_state,
            self.STATE_AWAIT_REPRINT_SERIAL: self._handle_await_reprint_serial,
            self.STATE_AWAIT_REPRINT_CONFIRM:
            self._handle_await_reprint_confirm,
            self.STATE_AWAIT_EXPEDITION_SERIAL:
            self._handle_await_expedition_serial,
            self.STATE_AWAIT_EXPEDITION_CONFIRM:
            self._handle_await_expedition_confirm,
            self.STATE_AWAIT_SAV_SERIAL: self._handle_await_sav_serial,
            self.STATE_AWAIT_SAV_CONFIRM: self._handle_await_sav_confirm,
        }

        handler = handlers.get(self.current_state)
        if handler:
            handler(scanned_text)
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
        # === CREATE ===
        if text_lower.startswith("create "):
            return self._handle_create_command(original_text)

        # === REPRINT ===
        elif text_lower == "reprint":
            return self._handle_reprint_command()

        # === EXPEDITION ===
        elif text_lower == "expedition":
            return self._handle_expedition_command()

        # === SAV ===
        elif text_lower == "sav":
            return self._handle_sav_command()

        return False

    def _handle_create_command(self, text):
        """Gère la commande create <nom>."""
        if not is_printer_service_running():
            self._update_ui("❌ Service d'impression inactif",
                            "Impossible de créer une étiquette")
            self.app.add_message("❌ Service d'impression non détecté", "error")
            return True

        try:
            checker_name = text.split(" ", 1)[1].strip()
            if not checker_name:
                raise ValueError("Nom vide")
        except (IndexError, ValueError):
            self._update_ui("❌ Format incorrect", "Utilisez: create <nom>")
            self.app.add_message("❌ Format incorrect. Utilisez: create <nom>",
                                 "error")
            return True

        # Envoi MQTT
        if self.app.mqtt_client and self.app.mqtt_client.is_connected():
            payload = json.dumps({"checker_name": checker_name})
            self.app.mqtt_client.publish("printer/create_label",
                                         payload,
                                         qos=1)

            self._update_ui(f"✅ Étiquette demandée",
                            f"Validée par {checker_name.title()}")
            self.app.add_message(
                f"✅ Étiquette créée pour {checker_name.title()}", "success")
        else:
            self._update_ui("❌ Erreur MQTT", "Client déconnecté")
            self.app.add_message("❌ Impossible d'envoyer - MQTT déconnecté",
                                 "error")

        return True

    def _handle_reprint_command(self):
        """Gère la commande reprint."""
        if not is_printer_service_running():
            self._update_ui("❌ Service d'impression inactif",
                            "Réimpression impossible")
            self.app.add_message("❌ Service d'impression non détecté", "error")
            return True

        self._change_state(self.STATE_AWAIT_REPRINT_SERIAL)
        self._update_ui("🔄 Mode Réimpression",
                        "Scanner le numéro de série à réimprimer")
        self.app.add_message("🔄 Mode réimpression activé", "info")
        self._start_timeout()
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

    def _handle_await_reprint_serial(self, text):
        """Gère l'attente du serial pour réimpression."""
        serial = self._extract_serial(text)
        if not serial:
            self._update_ui("❌ Série invalide",
                            "Format attendu: RW-48v271XXXX")
            self.app.add_message(f"❌ Format de série invalide: {text}",
                                 "error")
            self._delayed_reset(2000)
            return

        self.serial_to_reprint = serial
        self._change_state(self.STATE_AWAIT_REPRINT_CONFIRM)

        self._update_ui(f"✅ Série: {serial}",
                        "Scanner 'reprint' pour confirmer")
        self.app.add_message(f"✅ Série sélectionnée: {serial}", "success")
        self._start_timeout()

    def _handle_await_reprint_confirm(self, text):
        """Gère la confirmation de réimpression."""
        if text.lower().strip() != "reprint":
            self._update_ui("❌ Confirmation incorrecte",
                            "Scanner 'reprint' pour confirmer")
            self.app.add_message(f"❌ Attendu 'reprint', reçu: {text}", "error")
            self._delayed_reset(2000)
            return

        # Envoyer la demande de réimpression
        if self.app.mqtt_client and self.app.mqtt_client.is_connected():
            self.app.mqtt_client.publish("printer/request_full_reprint",
                                         self.serial_to_reprint,
                                         qos=1)

            self._update_ui("🖨️ Réimpression lancée",
                            f"Série: {self.serial_to_reprint}")
            self.app.add_message(
                f"🖨️ Réimpression lancée pour {self.serial_to_reprint}",
                "success")
        else:
            self._update_ui("❌ Erreur MQTT", "Impossible d'envoyer la demande")
            self.app.add_message("❌ MQTT déconnecté - réimpression échouée",
                                 "error")

        self._reset_scan()

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
            from src.labels import CSVSerialManager

            if CSVSerialManager.is_battery_in_sav(serial):
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

        for serial in self.serials_for_expedition:
            try:
                from src.labels import CSVSerialManager

                # Vérifier AVANT si c'est une batterie SAV
                is_sav_battery = CSVSerialManager.is_battery_in_sav(serial)

                if is_sav_battery:
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
                                        timestamp_iso)
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
        self.serial_to_reprint = None
        self.serials_for_expedition = []
        self.expedition_mode_active = False
        self.serial_for_sav = None

        self._cancel_timeout()

        self._update_ui("Prêt.", "Veuillez scanner ou saisir une commande...")

    def _send_expedition_email(self, serial_numbers, timestamp_expedition):
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
                        serial_numbers, timestamp_expedition)
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
