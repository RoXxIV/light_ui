#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Service d'impression minimal avec file d'attente persistante :
- CREATE : Créer ligne CSV + ajouter à la file d'impression
- REPRINT : Ajouter à la file d'impression
- EXPEDITION : Mettre à jour timestamp expédition dans CSV
"""

import socket
import json
import re
import threading
import time
import collections
import paho.mqtt.client as mqtt
from datetime import datetime
from src.ui.system_utils import log
from src.labels import LabelTemplates, PrinterConfig, CSVSerialManager


class MinimalPrinter:
    """
    Service d'impression minimal avec file d'attente persistante.
    """

    def __init__(self):
        """Initialise le service d'impression."""
        self.mqtt_client = None
        self.printer_status = "unknown"

        # File d'attente et verrou pour le threading
        self.print_queue = collections.deque()
        self.queue_lock = threading.Lock()

        # Initialiser le CSV des séries
        CSVSerialManager.initialize_serial_csv()

        # NOUVEAU: Initialiser le CSV SAV
        CSVSerialManager.initialize_sav_csv()

        log("MinimalPrinter: Service initialisé avec file d'attente",
            level="INFO")

    def start(self):
        """Démarre le service d'impression."""
        log("MinimalPrinter: Démarrage du service minimal avec file d'attente",
            level="INFO")

        # Démarrer le worker thread pour traiter la file
        self._start_worker_thread()

        # Configuration du client MQTT
        self.mqtt_client = mqtt.Client(
            client_id="minimal_printer_service",
            callback_api_version=mqtt.CallbackAPIVersion.  # type: ignore
            VERSION1)

        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        self.mqtt_client.on_disconnect = self._on_disconnect

        # Boucle de connexion avec reconnexion automatique
        while True:
            try:
                log(f"MinimalPrinter: Connexion MQTT {PrinterConfig.MQTT_BROKER_HOST}:{PrinterConfig.MQTT_BROKER_PORT}",
                    level="INFO")
                self.mqtt_client.connect(PrinterConfig.MQTT_BROKER_HOST,
                                         PrinterConfig.MQTT_BROKER_PORT, 300)

                # Démarrer la boucle (bloquante)
                self.mqtt_client.loop_forever()

            except Exception as e:
                log(f"MinimalPrinter: Erreur connexion MQTT: {e}",
                    level="ERROR")
                time.sleep(5)

    def _start_worker_thread(self):
        """Démarre le thread worker pour traiter la file d'impression."""
        worker = threading.Thread(target=self._printer_worker_thread,
                                  name="PrinterWorker",
                                  daemon=True)
        worker.start()
        log("MinimalPrinter: Thread worker démarré", level="INFO")

    def _printer_worker_thread(self):
        """Thread worker qui traite la file d'impression en continu."""
        log("MinimalPrinter: Worker thread actif", level="INFO")

        while True:
            item_to_print = None

            # Récupérer un élément de la file de manière thread-safe
            with self.queue_lock:
                if self.print_queue:
                    item_to_print = self.print_queue[0]

            if item_to_print:
                # Vérifier le statut de l'imprimante
                status_info = self._check_printer_status()

                if status_info['ready']:
                    # Imprimante prête, tenter l'impression
                    success = self._process_print_item(item_to_print)

                    if success:
                        # Retirer de la file en cas de succès
                        with self.queue_lock:
                            if self.print_queue and self.print_queue[
                                    0] == item_to_print:
                                self.print_queue.popleft()
                                log(f"MinimalPrinter: Item imprimé et retiré de la file. Restants: {len(self.print_queue)}",
                                    level="INFO")
                        time.sleep(PrinterConfig.DELAY_AFTER_SUCCESS_S)
                    else:
                        # Échec impression, garder en file et retry
                        log(f"MinimalPrinter: Échec impression, retry dans {PrinterConfig.RETRY_DELAY_ON_ERROR_S}s",
                            level="WARNING")
                        time.sleep(PrinterConfig.RETRY_DELAY_ON_ERROR_S)
                else:
                    # Imprimante pas prête, attendre et retry
                    log(f"MinimalPrinter: Imprimante non prête ({status_info['message']}), retry dans {PrinterConfig.RETRY_DELAY_ON_ERROR_S}s",
                        level="DEBUG")
                    time.sleep(PrinterConfig.RETRY_DELAY_ON_ERROR_S)
            else:
                # File vide, attendre
                time.sleep(PrinterConfig.POLL_DELAY_WHEN_IDLE_S)

    def _process_print_item(self, item):
        """
        Traite un élément de la file d'impression.
        
        Args:
            item: Tuple (action_type, serial_number, random_code, fabrication_date)
            
        Returns:
            bool: True si succès, False sinon
        """
        if not item or len(item) < 4:
            log(f"MinimalPrinter: Item malformé: {item}", level="ERROR")
            return True  # Retirer de la file

        action_type, serial_number, random_code, fabrication_date = item

        if action_type == "PRINT_ALL_THREE":
            return self._print_all_three_labels(serial_number, random_code,
                                                fabrication_date)
        else:
            log(f"MinimalPrinter: Type d'action inconnu: {action_type}",
                level="ERROR")
            return True  # Retirer de la file

    def _check_printer_status(self):
        """
        Vérifie le statut de l'imprimante pour l'UI avec une logique de tentatives.
        
        Returns:
            dict: {
                'status': 'OK'|'MEDIA_OUT'|'HEAD_OPEN'|'ERROR',
                'message': 'Description lisible',
                'ready': True|False
            }
        """
        # --- Boucle de tentatives pour la connexion initiale ---
        for attempt in range(3):
            sock = None
            try:
                # La création du socket est maintenant DANS la boucle
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(PrinterConfig.SOCKET_TIMEOUT_S)
                sock.connect(
                    (PrinterConfig.PRINTER_IP, PrinterConfig.PRINTER_PORT))

                # Si la connexion réussit, on continue pour envoyer la commande de statut
                # --- La suite s'exécute uniquement si la connexion a réussi ---
                command = b'~HQES\r\n'
                sock.sendall(command)

                # Recevoir réponse
                response_bytes = b''
                try:
                    while True:
                        chunk = sock.recv(1024)
                        if not chunk:
                            break
                        response_bytes += chunk
                        if b'\x03' in chunk:  # ETX
                            break
                except socket.timeout:
                    if not response_bytes:
                        return {
                            'status': PrinterConfig.STATUS_ERROR_COMM,
                            'message': 'Timeout communication',
                            'ready': False
                        }

                if response_bytes:
                    response_str = response_bytes.decode('ascii',
                                                         errors='ignore')
                    parsed_data = self._parse_hqes_response(response_str)

                    if parsed_data:
                        error_flag, error_g2_hex, error_g1_hex, _, _, _ = parsed_data

                        if error_flag == '0':
                            return {
                                'status': PrinterConfig.STATUS_OK,
                                'message': 'Imprimante prête',
                                'ready': True
                            }
                        else:
                            try:
                                error_g1_int = int(error_g1_hex, 16)

                                if error_g1_int & PrinterConfig.ERROR_MASK_MEDIA_OUT:
                                    return {
                                        'status':
                                        PrinterConfig.STATUS_MEDIA_OUT,
                                        'message': 'Plus de papier/étiquettes',
                                        'ready': False
                                    }
                                elif error_g1_int & PrinterConfig.ERROR_MASK_HEAD_OPEN:
                                    return {
                                        'status':
                                        PrinterConfig.STATUS_HEAD_OPEN,
                                        'message':
                                        'Tête d\'impression ouverte',
                                        'ready': False
                                    }
                                else:
                                    return {
                                        'status':
                                        PrinterConfig.STATUS_ERROR_UNKNOWN,
                                        'message':
                                        f'Erreur inconnue (G1: {error_g1_hex})',
                                        'ready': False
                                    }
                            except ValueError:
                                return {
                                    'status':
                                    PrinterConfig.STATUS_ERROR_UNKNOWN,
                                    'message': 'Erreur parsing statut',
                                    'ready': False
                                }
                    else:
                        return {
                            'status': PrinterConfig.STATUS_ERROR_UNKNOWN,
                            'message': 'Réponse imprimante non comprise',
                            'ready': False
                        }
                else:
                    return {
                        'status': PrinterConfig.STATUS_ERROR_COMM,
                        'message': 'Aucune réponse de l\'imprimante',
                        'ready': False
                    }

            except socket.error as e:
                if "Network is unreachable" in str(e) and attempt < 2:
                    log(f"MinimalPrinter: Réseau non prêt (tentative {attempt + 1}/3). Nouvel essai dans 5s.",
                        level="WARNING")
                    time.sleep(5)
                    continue  # Passe à la tentative suivante
                else:
                    return {
                        'status': PrinterConfig.STATUS_ERROR_COMM,
                        'message': f'Erreur réseau: {str(e)[:50]}',
                        'ready': False
                    }
            except Exception as e:
                return {
                    'status': PrinterConfig.STATUS_ERROR_UNKNOWN,
                    'message': f'Erreur inattendue: {str(e)[:50]}',
                    'ready': False
                }
            finally:
                if sock:
                    sock.close()

        # Si la boucle se termine sans succès
        return {
            'status': PrinterConfig.STATUS_ERROR_COMM,
            'message': 'Réseau inaccessible après plusieurs tentatives',
            'ready': False
        }

    def _parse_hqes_response(self, response_str):
        """Parse la réponse ~HQES."""
        error_flag, error_g2, error_g1 = '0', '00000000', '00000000'
        warn_flag, warn_g2, warn_g1 = '0', '00000000', '00000000'
        found_errors = False

        pattern = re.compile(
            r"^\s*([A-Z]+):\s+(\d)\s+([0-9A-Fa-f]+)\s+([0-9A-Fa-f]+)")

        lines = response_str.splitlines()
        for line in lines:
            match = pattern.match(line)
            if match:
                section, flag, g2_hex, g1_hex = match.groups()
                if section == "ERRORS":
                    error_flag, error_g2, error_g1 = flag, g2_hex, g1_hex
                    found_errors = True
                elif section == "WARNINGS":
                    warn_flag, warn_g2, warn_g1 = flag, g2_hex, g1_hex

        if found_errors:
            return error_flag, error_g2.zfill(8), error_g1.zfill(
                8), warn_flag, warn_g2.zfill(8), warn_g1.zfill(8)
        else:
            return None

    def _print_all_three_labels(self, serial_number, random_code,
                                fabrication_date):
        """
        Imprime les 3 étiquettes pour un serial donné.
        
        Returns:
            bool: True si toutes les impressions réussies
        """
        success_v1 = self._print_v1_label(serial_number, random_code,
                                          fabrication_date)
        success_main = self._print_main_label(serial_number, random_code)
        success_shipping = self._print_shipping_label(serial_number)

        if success_v1 and success_main and success_shipping:
            log(f"MinimalPrinter: 3 étiquettes imprimées avec succès pour {serial_number}",
                level="INFO")
            return True
        else:
            log(f"MinimalPrinter: Impression partielle pour {serial_number} (V1:{success_v1}, Main:{success_main}, Ship:{success_shipping})",
                level="WARNING")
            return False

    def _on_connect(self, client, userdata, flags, rc):
        """Callback de connexion MQTT."""
        if rc == 0:
            log("MinimalPrinter: Connexion MQTT réussie", level="INFO")

            # S'abonner seulement aux 3 topics essentiels
            topics = [
                PrinterConfig.MQTT_TOPIC_CREATE_LABEL,  # CREATE
                PrinterConfig.MQTT_TOPIC_REQUEST_FULL_REPRINT,  # REPRINT
                PrinterConfig.
                MQTT_TOPIC_UPDATE_SHIPPING_TIMESTAMP,  # EXPEDITION
                PrinterConfig.MQTT_TOPIC_SAV_ENTRY,  # SAV ENTRY
                PrinterConfig.MQTT_TOPIC_SAV_DEPARTURE,  # SAV DEPARTURE
                PrinterConfig.MQTT_TOPIC_CREATE_QR,  # QR
            ]

            for topic in topics:
                client.subscribe(topic, 1)
                log(f"MinimalPrinter: Abonné à {topic}", level="DEBUG")

            # Publier le statut initial
            self._publish_printer_status()

        else:
            log(f"MinimalPrinter: Échec connexion MQTT, code: {rc}",
                level="ERROR")

    def _on_message(self, client, userdata, msg):
        """Callback de réception de message MQTT."""
        try:
            topic = msg.topic
            payload_str = msg.payload.decode("utf-8")

            log(f"MinimalPrinter: Message reçu sur {topic}: {payload_str}",
                level="INFO")

            # Router vers les handlers
            if topic == PrinterConfig.MQTT_TOPIC_CREATE_LABEL:
                self._handle_create(payload_str)

            elif topic == PrinterConfig.MQTT_TOPIC_REQUEST_FULL_REPRINT:
                self._handle_reprint(payload_str)

            elif topic == PrinterConfig.MQTT_TOPIC_UPDATE_SHIPPING_TIMESTAMP:
                self._handle_expedition(payload_str)

            elif topic == PrinterConfig.MQTT_TOPIC_SAV_ENTRY:
                self._handle_sav_entry(payload_str)

            elif topic == PrinterConfig.MQTT_TOPIC_SAV_DEPARTURE:
                self._handle_sav_departure(payload_str)

            elif topic == PrinterConfig.MQTT_TOPIC_CREATE_QR:
                self._handle_create_qr(payload_str)

            else:
                log(f"MinimalPrinter: Topic non géré: {topic}",
                    level="WARNING")

        except Exception as e:
            log(f"MinimalPrinter: Erreur traitement message: {e}",
                level="ERROR")

    def _on_disconnect(self, client, userdata, rc):
        """Callback de déconnexion MQTT."""
        log(f"MinimalPrinter: Déconnexion MQTT, code: {rc}", level="WARNING")

    def _handle_create(self, payload_str):
        """
        CREATE : Créer ligne CSV + ajouter à la file d'impression.
        Format: {"checker_name": "nom"}
        """
        try:
            data = json.loads(payload_str)
            checker_name = data.get("checker_name", "").strip()

            if not checker_name:
                log("MinimalPrinter: CREATE - Nom de checkeur manquant",
                    level="ERROR")
                self._publish_operation_result("create", False,
                                               "Nom de checkeur manquant")
                return

            # Générer nouveau serial
            serial_number = CSVSerialManager.generate_next_serial_number()
            random_code = CSVSerialManager.generate_random_code()
            timestamp_iso = datetime.now().isoformat()
            fabrication_date = datetime.now().strftime("%d/%m/%Y")

            # TOUJOURS créer la ligne CSV d'abord
            if not CSVSerialManager.add_serial_to_csv(
                    timestamp_iso, serial_number, random_code, checker_name):
                log(f"MinimalPrinter: CREATE - Échec enregistrement CSV pour {serial_number}",
                    level="ERROR")
                self._publish_operation_result("create", False,
                                               "Erreur sauvegarde CSV")
                return

            log(f"MinimalPrinter: CREATE - CSV mis à jour pour {serial_number} (checkeur: {checker_name})",
                level="INFO")

            # Ajouter à la file d'impression (sera traité quand l'imprimante sera prête)
            with self.queue_lock:
                self.print_queue.append(("PRINT_ALL_THREE", serial_number,
                                         random_code, fabrication_date))
                queue_size = len(self.print_queue)

            log(f"MinimalPrinter: CREATE - {serial_number} ajouté à la file d'impression ({queue_size} en attente)",
                level="INFO")
            self._publish_operation_result(
                "create", True,
                f"Série créée: {serial_number} (en file d'impression)")

        except json.JSONDecodeError:
            log("MinimalPrinter: CREATE - Payload JSON invalide",
                level="ERROR")
            self._publish_operation_result("create", False,
                                           "Format JSON invalide")
        except Exception as e:
            log(f"MinimalPrinter: CREATE - Erreur: {e}", level="ERROR")
            self._publish_operation_result("create", False,
                                           f"Erreur: {str(e)[:50]}")

    def _handle_reprint(self, payload_str):
        """
        REPRINT : Ajouter à la file d'impression les 3 étiquettes d'un serial existant.
        Format: "RW-48v271XXXX" (juste le serial number)
        """
        try:
            serial_number = payload_str.strip()

            if not serial_number:
                log("MinimalPrinter: REPRINT - Numéro de série manquant",
                    level="ERROR")
                self._publish_operation_result("reprint", False,
                                               "Numéro de série manquant")
                return

            # Récupérer les détails depuis le CSV
            found_serial, random_code, timestamp_impression = CSVSerialManager.get_details_for_reprint_from_csv(
                serial_number)

            if not all([found_serial, random_code, timestamp_impression]):
                log(f"MinimalPrinter: REPRINT - Serial {serial_number} non trouvé dans CSV",
                    level="ERROR")
                self._publish_operation_result(
                    "reprint", False, f"Serial {serial_number} non trouvé")
                return

            # Extraire la date de fabrication
            try:
                if timestamp_impression:
                    dt_impression = datetime.fromisoformat(
                        timestamp_impression)
                    fabrication_date = dt_impression.strftime("%d/%m/%Y")
                else:
                    fabrication_date = datetime.now().strftime("%d/%m/%Y")
                    log(f"MinimalPrinter: REPRINT - Timestamp vide pour {serial_number}, utilisation date actuelle",
                        level="WARNING")
            except (ValueError, TypeError) as e:
                fabrication_date = datetime.now().strftime("%d/%m/%Y")
                log(f"MinimalPrinter: REPRINT - Erreur parsing date pour {serial_number} ({e}), utilisation date actuelle",
                    level="WARNING")

            # Ajouter à la file d'impression
            with self.queue_lock:
                self.print_queue.append(("PRINT_ALL_THREE", serial_number,
                                         random_code, fabrication_date))
                queue_size = len(self.print_queue)

            log(f"MinimalPrinter: REPRINT - {serial_number} ajouté à la file d'impression ({queue_size} en attente)",
                level="INFO")
            self._publish_operation_result(
                "reprint", True, f"Réimpression programmée: {serial_number}")

        except Exception as e:
            log(f"MinimalPrinter: REPRINT - Erreur: {e}", level="ERROR")
            self._publish_operation_result("reprint", False,
                                           f"Erreur: {str(e)[:50]}")

    def _handle_expedition(self, payload_str):
        """
        EXPEDITION : Mettre à jour timestamp expédition dans CSV.
        Format: {"serial_number": "RW-48v271XXXX", "timestamp_expedition": "2025-01-01T12:00:00"}
        """
        try:
            data = json.loads(payload_str)
            serial_number = data.get("serial_number", "").strip()
            timestamp_expedition = data.get("timestamp_expedition", "").strip()

            if not all([serial_number, timestamp_expedition]):
                log("MinimalPrinter: EXPEDITION - Données manquantes",
                    level="ERROR")
                self._publish_operation_result("expedition", False,
                                               "Données manquantes")
                return

            # Mettre à jour le CSV
            success = CSVSerialManager.update_csv_with_shipping_timestamp(
                serial_number, timestamp_expedition)

            if success:
                log(f"MinimalPrinter: EXPEDITION réussie pour {serial_number}",
                    level="INFO")
                self._publish_operation_result(
                    "expedition", True,
                    f"Expédition mise à jour: {serial_number}")
            else:
                log(f"MinimalPrinter: EXPEDITION - Échec mise à jour {serial_number}",
                    level="ERROR")
                self._publish_operation_result(
                    "expedition", False, f"Échec mise à jour: {serial_number}")

        except json.JSONDecodeError:
            log("MinimalPrinter: EXPEDITION - Payload JSON invalide",
                level="ERROR")
            self._publish_operation_result("expedition", False,
                                           "Format JSON invalide")
        except Exception as e:
            log(f"MinimalPrinter: EXPEDITION - Erreur: {e}", level="ERROR")
            self._publish_operation_result("expedition", False,
                                           f"Erreur: {str(e)[:50]}")

    def _print_v1_label(self, serial_number, random_code, fabrication_date):
        """Imprime une étiquette V1."""
        zpl_command = LabelTemplates.get_v1_label_zpl(serial_number,
                                                      random_code,
                                                      fabrication_date)
        return self._send_zpl_to_printer(zpl_command, f"V1 {serial_number}")

    def _print_main_label(self, serial_number, random_code):
        """Imprime une étiquette principale."""
        zpl_command = LabelTemplates.get_main_label_zpl(
            serial_number, random_code)
        return self._send_zpl_to_printer(zpl_command, f"Main {serial_number}")

    def _print_shipping_label(self, serial_number):
        """Imprime une étiquette d'expédition."""
        zpl_command = LabelTemplates.get_shipping_label_zpl(serial_number)
        return self._send_zpl_to_printer(zpl_command,
                                         f"Shipping {serial_number}")

    def _send_zpl_to_printer(self, zpl_command, description=""):
        """Envoie une commande ZPL à l'imprimante."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(PrinterConfig.SOCKET_TIMEOUT_S)
            sock.connect(
                (PrinterConfig.PRINTER_IP, PrinterConfig.PRINTER_PORT))
            sock.sendall(zpl_command.encode('utf-8'))
            sock.close()

            log(f"MinimalPrinter: Impression réussie: {description}",
                level="DEBUG")
            return True

        except socket.timeout:
            log(f"MinimalPrinter: Timeout impression: {description}",
                level="ERROR")
            return False
        except socket.error as e:
            log(f"MinimalPrinter: Erreur socket impression {description}: {e}",
                level="ERROR")
            return False
        except Exception as e:
            log(f"MinimalPrinter: Erreur impression {description}: {e}",
                level="ERROR")
            return False

    def _publish_printer_status(self):
        """Publie le statut de l'imprimante pour l'UI."""
        try:
            status_info = self._check_printer_status()

            # Publier statut simple pour compatibilité
            simple_status = "on" if status_info['ready'] else "off"
            if self.mqtt_client and self.mqtt_client.is_connected():
                self.mqtt_client.publish("printer/status",
                                         simple_status,
                                         qos=1,
                                         retain=True)

                # Publier statut détaillé pour l'UI
                detailed_status = {
                    'status': status_info['status'],
                    'message': status_info['message'],
                    'ready': status_info['ready'],
                    'timestamp': datetime.now().isoformat()
                }
                self.mqtt_client.publish("printer/status/detailed",
                                         json.dumps(detailed_status),
                                         qos=1,
                                         retain=True)

                log(f"MinimalPrinter: Statut publié - {status_info['message']}",
                    level="INFO")

        except Exception as e:
            log(f"MinimalPrinter: Erreur publication statut: {e}",
                level="ERROR")

    def _handle_sav_entry(self, payload_str):
        """
        SAV ENTRY : Enregistrer l'arrivée d'une batterie en SAV.
        Format: {"serial_number": "RW-48v271XXXX", "timestamp_sav_arrivee": "2025-01-01T12:00:00", "technicien": "Scanner_User"}
        """
        try:
            data = json.loads(payload_str)
            serial_number = data.get("serial_number", "").strip()
            timestamp_arrivee = data.get("timestamp_sav_arrivee", "").strip()
            technicien = data.get("technicien",
                                  "").strip()  # Optionnel pour futur usage

            if not all([serial_number, timestamp_arrivee]):
                log("MinimalPrinter: SAV_ENTRY - Données manquantes",
                    level="ERROR")
                self._publish_operation_result("sav_entry", False,
                                               "Données manquantes")
                return

            # Vérifier que le serial existe dans le CSV principal
            from src.labels import CSVSerialManager
            found_serial, _, _ = CSVSerialManager.get_details_for_reprint_from_csv(
                serial_number)

            if not found_serial:
                log(f"MinimalPrinter: SAV_ENTRY - Serial {serial_number} non trouvé dans le système",
                    level="ERROR")
                self._publish_operation_result(
                    "sav_entry", False, f"Serial {serial_number} inexistant")
                return

            # Vérifier si déjà en SAV
            if CSVSerialManager.is_battery_in_sav(serial_number):
                log(f"MinimalPrinter: SAV_ENTRY - {serial_number} déjà en SAV",
                    level="WARNING")
                self._publish_operation_result("sav_entry", False,
                                               f"{serial_number} déjà en SAV")
                return

            # Enregistrer l'entrée SAV
            success = CSVSerialManager.add_sav_entry(timestamp_arrivee,
                                                     serial_number)

            if success:
                log(f"MinimalPrinter: SAV_ENTRY réussie pour {serial_number} par {technicien}",
                    level="INFO")
                self._publish_operation_result(
                    "sav_entry", True, f"SAV enregistré: {serial_number}")
            else:
                log(f"MinimalPrinter: SAV_ENTRY - Échec enregistrement {serial_number}",
                    level="ERROR")
                self._publish_operation_result("sav_entry", False,
                                               f"Échec SAV: {serial_number}")

        except json.JSONDecodeError:
            log("MinimalPrinter: SAV_ENTRY - Payload JSON invalide",
                level="ERROR")
            self._publish_operation_result("sav_entry", False,
                                           "Format JSON invalide")
        except Exception as e:
            log(f"MinimalPrinter: SAV_ENTRY - Erreur: {e}", level="ERROR")
            self._publish_operation_result("sav_entry", False,
                                           f"Erreur: {str(e)[:50]}")

    def _handle_sav_departure(self, payload_str):
        """
        SAV DEPARTURE : Enregistrer la sortie d'une batterie du SAV (lors de l'expédition).
        Format: {"serial_number": "RW-48v271XXXX", "timestamp_depart": "2025-01-01T12:00:00"}
        """
        try:
            data = json.loads(payload_str)
            serial_number = data.get("serial_number", "").strip()
            timestamp_depart = data.get("timestamp_depart", "").strip()

            if not all([serial_number, timestamp_depart]):
                log("MinimalPrinter: SAV_DEPARTURE - Données manquantes",
                    level="ERROR")
                self._publish_operation_result("sav_departure", False,
                                               "Données manquantes")
                return

            # Vérifier que la batterie est effectivement en SAV
            from src.labels import CSVSerialManager
            if not CSVSerialManager.is_battery_in_sav(serial_number):
                log(f"MinimalPrinter: SAV_DEPARTURE - {serial_number} n'est pas en SAV",
                    level="WARNING")
                self._publish_operation_result("sav_departure", False,
                                               f"{serial_number} pas en SAV")
                return

            # Enregistrer la sortie SAV
            success = CSVSerialManager.update_sav_departure(
                serial_number, timestamp_depart)

            if success:
                log(f"MinimalPrinter: SAV_DEPARTURE réussie pour {serial_number}",
                    level="INFO")
                self._publish_operation_result("sav_departure", True,
                                               f"Sortie SAV: {serial_number}")
            else:
                log(f"MinimalPrinter: SAV_DEPARTURE - Échec sortie {serial_number}",
                    level="ERROR")
                self._publish_operation_result(
                    "sav_departure", False,
                    f"Échec sortie SAV: {serial_number}")

        except json.JSONDecodeError:
            log("MinimalPrinter: SAV_DEPARTURE - Payload JSON invalide",
                level="ERROR")
            self._publish_operation_result("sav_departure", False,
                                           "Format JSON invalide")
        except Exception as e:
            log(f"MinimalPrinter: SAV_DEPARTURE - Erreur: {e}", level="ERROR")
            self._publish_operation_result("sav_departure", False,
                                           f"Erreur: {str(e)[:50]}")

    def _publish_operation_result(self, operation, success, message):
        """Publie le résultat d'une opération pour l'UI."""
        try:
            if self.mqtt_client and self.mqtt_client.is_connected():
                result = {
                    'operation': operation,
                    'success': success,
                    'message': message,
                    'timestamp': datetime.now().isoformat()
                }
                self.mqtt_client.publish("printer/operation/result",
                                         json.dumps(result),
                                         qos=1)

        except Exception as e:
            log(f"MinimalPrinter: Erreur publication résultat: {e}",
                level="ERROR")

    def _handle_create_qr(self, payload_str):
        """Gère la création de QR personnalisé."""
        try:
            data = json.loads(payload_str)
            qr_text = data.get("qr_text", "").strip()

            if not qr_text:
                log("MinimalPrinter: CREATE_QR - Texte QR manquant",
                    level="ERROR")
                return

            # Envoyer le ZPL à l'imprimante
            success = self._send_qr_zpl_to_printer(qr_text)

            if success:
                log(f"MinimalPrinter: QR imprimé avec succès: {qr_text}",
                    level="INFO")
            else:
                log(f"MinimalPrinter: Échec impression QR: {qr_text}",
                    level="ERROR")

        except json.JSONDecodeError:
            log("MinimalPrinter: CREATE_QR - Payload JSON invalide",
                level="ERROR")
        except Exception as e:
            log(f"MinimalPrinter: CREATE_QR - Erreur: {e}", level="ERROR")

    def _send_qr_zpl_to_printer(self, qr_text):
        """Envoie ZPL pour QR personnalisé."""
        zpl_command = f"""
    ^XA
    ~TA000
    ~JSN
    ^LT0
    ^MNW
    ^MTT
    ^PON
    ^PMN
    ^LH0,0
    ^JMA
    ^PR4,4
    ~SD15
    ^JUS
    ^LRN
    ^CI27
    ^PA0,1,1,0
    ^XZ
    ^XA
    ^MMT
    ^PW815
    ^LL200
    ^LS0
    ^FT50,50^A0N,30,30^FH\\^CI28^FDQR CODE:^FS^CI27
    ^FT50,90^A0N,40,40^FH\\^CI28^FD{qr_text}^FS^CI27
    ^FO500,20
    ^BQN,2,8
    ^FH\\^FDLA,{qr_text}^FS
    ^PQ1,0,1,Y
    ^XZ
    """
        return self._send_zpl_to_printer(zpl_command, f"QR {qr_text}")


def main():
    """Point d'entrée principal."""
    try:
        log("MinimalPrinter: Démarrage du service d'impression minimal",
            level="INFO")
        log("MinimalPrinter: Fonctions disponibles - CREATE, REPRINT, EXPEDITION",
            level="INFO")

        printer = MinimalPrinter()
        printer.start()

    except KeyboardInterrupt:
        log("MinimalPrinter: Arrêt demandé par l'utilisateur", level="INFO")
    except Exception as e:
        log(f"MinimalPrinter: Erreur critique: {e}", level="ERROR")


if __name__ == "__main__":
    main()
