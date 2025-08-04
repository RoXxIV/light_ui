#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Service d'impression simplifié sans thread ni file d'attente.
Traitement immédiat des commandes MQTT.
"""

import socket
import json
import re
import paho.mqtt.client as mqtt
from datetime import datetime
from src.ui.system_utils import log
from src.labels import LabelTemplates, PrinterConfig, CSVSerialManager


class SimplePrinter:
    """
    Service d'impression simplifié avec traitement immédiat.
    """
    
    def __init__(self):
        """Initialise le service d'impression."""
        self.mqtt_client = None
        self.printer_status = "unknown"
        
        # Initialiser le CSV des séries
        CSVSerialManager.initialize_serial_csv()
        
        log("SimplePrinter: Service initialisé", level="INFO")
        
    def start(self):
        """Démarre le service d'impression."""
        log("SimplePrinter: Démarrage du service", level="INFO")
        
        # Vérifier l'IP de l'imprimante
        if "192.168.1." in PrinterConfig.PRINTER_IP:
            log("SimplePrinter: ⚠️ IP imprimante par défaut détectée. Vérifiez la configuration.", level="WARNING")
            
        # Configuration du client MQTT
        self.mqtt_client = mqtt.Client(
            client_id="simple_printer_service",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1 # type: ignore
        )
        
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        self.mqtt_client.on_disconnect = self._on_disconnect
        
        # Boucle de connexion avec reconnexion automatique
        while True:
            try:
                log(f"SimplePrinter: Connexion MQTT {PrinterConfig.MQTT_BROKER_HOST}:{PrinterConfig.MQTT_BROKER_PORT}", level="INFO")
                self.mqtt_client.connect(PrinterConfig.MQTT_BROKER_HOST, PrinterConfig.MQTT_BROKER_PORT, 60)
                
                # Démarrer la boucle (bloquante)
                self.mqtt_client.loop_forever()
                
            except Exception as e:
                log(f"SimplePrinter: Erreur connexion MQTT: {e}", level="ERROR")
                import time
                time.sleep(5)  # Attendre avant de reconnecter
                
    def _on_connect(self, client, userdata, flags, rc):
        """Callback de connexion MQTT."""
        if rc == 0:
            log("SimplePrinter: Connexion MQTT réussie", level="INFO")
            
            # S'abonner aux topics nécessaires
            topics = [
                PrinterConfig.MQTT_TOPIC_CREATE_LABEL,
                PrinterConfig.MQTT_TOPIC_REQUEST_FULL_REPRINT,
                PrinterConfig.MQTT_TOPIC_UPDATE_SHIPPING_TIMESTAMP,
                PrinterConfig.MQTT_TOPIC_TEST_DONE,
                PrinterConfig.MQTT_TOPIC_CREATE_BATCH_LABELS
            ]
            
            for topic in topics:
                client.subscribe(topic, 1)
                log(f"SimplePrinter: Abonné à {topic}", level="DEBUG")
                
            # Publier le statut initial de l'imprimante
            self._update_printer_status()
            
        else:
            log(f"SimplePrinter: Échec connexion MQTT, code: {rc}", level="ERROR")
            
    def _on_message(self, client, userdata, msg):
        """Callback de réception de message MQTT."""
        try:
            topic = msg.topic
            payload_str = msg.payload.decode("utf-8")
            
            log(f"SimplePrinter: Message reçu sur {topic}: {payload_str}", level="INFO")
            
            # Router vers le bon handler
            handlers = {
                PrinterConfig.MQTT_TOPIC_CREATE_LABEL: self._handle_create_label,
                PrinterConfig.MQTT_TOPIC_REQUEST_FULL_REPRINT: self._handle_full_reprint,
                PrinterConfig.MQTT_TOPIC_UPDATE_SHIPPING_TIMESTAMP: self._handle_shipping_update,
                PrinterConfig.MQTT_TOPIC_TEST_DONE: self._handle_test_done,
                PrinterConfig.MQTT_TOPIC_CREATE_BATCH_LABELS: self._handle_batch_creation,
            }
            
            handler = handlers.get(topic)
            if handler:
                handler(payload_str)
            else:
                log(f"SimplePrinter: Topic non géré: {topic}", level="WARNING")
                
        except Exception as e:
            log(f"SimplePrinter: Erreur traitement message: {e}", level="ERROR")
            
    def _on_disconnect(self, client, userdata, rc):
        """Callback de déconnexion MQTT."""
        log(f"SimplePrinter: Déconnexion MQTT, code: {rc}", level="WARNING")
        
    def _handle_create_label(self, payload_str):
        """Gère la création d'une nouvelle étiquette."""
        try:
            data = json.loads(payload_str)
            checker_name = data.get("checker_name", "").strip()
            
            if not checker_name:
                log("SimplePrinter: Nom de checkeur manquant", level="ERROR")
                return
                
            # Générer le numéro de série
            serial_number = CSVSerialManager.generate_next_serial_number()
            random_code = CSVSerialManager.generate_random_code()
            timestamp_iso = datetime.now().isoformat()
            fabrication_date = datetime.now().strftime("%d/%m/%Y")
            
            # Enregistrer dans le CSV
            if not CSVSerialManager.add_serial_to_csv(timestamp_iso, serial_number, random_code, checker_name):
                log(f"SimplePrinter: Échec enregistrement CSV pour {serial_number}", level="ERROR")
                return
                
            # Imprimer l'étiquette V1
            success = self._print_v1_label(serial_number, random_code, fabrication_date)
            
            if success:
                log(f"SimplePrinter: Étiquette créée avec succès: {serial_number}", level="INFO")
            else:
                log(f"SimplePrinter: Échec impression étiquette: {serial_number}", level="ERROR")
                
        except json.JSONDecodeError:
            log(f"SimplePrinter: Payload JSON invalide pour create_label", level="ERROR")
        except Exception as e:
            log(f"SimplePrinter: Erreur create_label: {e}", level="ERROR")
            
    def _handle_full_reprint(self, payload_str):
        """Gère la réimpression complète d'une batterie."""
        try:
            serial_number = payload_str.strip()
            
            # Récupérer les détails depuis le CSV
            found_serial, random_code, timestamp_impression = CSVSerialManager.get_details_for_reprint_from_csv(serial_number)
            
            if not all([found_serial, random_code, timestamp_impression]):
                log(f"SimplePrinter: Données manquantes pour réimpression de {serial_number}", level="ERROR")
                return
                
            # Extraire la date de fabrication
            try:
                if timestamp_impression:
                    dt_impression = datetime.fromisoformat(timestamp_impression)
                    fabrication_date = dt_impression.strftime("%d/%m/%Y")
                else:
                    # timestamp_impression est None
                    fabrication_date = datetime.now().strftime("%d/%m/%Y")
                    log(f"SimplePrinter: Timestamp impression vide pour {serial_number}, utilisation date actuelle", level="WARNING")
            except (ValueError, TypeError) as e:
                fabrication_date = datetime.now().strftime("%d/%m/%Y")
                log(f"SimplePrinter: Erreur parsing date impression pour {serial_number}: {e}, utilisation date actuelle", level="WARNING")
                
            # Imprimer les 3 étiquettes
            success_v1 = self._print_v1_label(serial_number, random_code, fabrication_date)
            success_main = self._print_main_label(serial_number, random_code)
            success_shipping = self._print_shipping_label(serial_number)
            
            if success_v1 and success_main and success_shipping:
                log(f"SimplePrinter: Réimpression complète réussie: {serial_number}", level="INFO")
            else:
                log(f"SimplePrinter: Réimpression partielle pour {serial_number}", level="WARNING")
                
        except Exception as e:
            log(f"SimplePrinter: Erreur full_reprint: {e}", level="ERROR")
            
    def _handle_shipping_update(self, payload_str):
        """Gère la mise à jour du timestamp d'expédition."""
        try:
            data = json.loads(payload_str)
            serial_number = data.get("serial_number")
            timestamp_expedition = data.get("timestamp_expedition")
            
            if not all([serial_number, timestamp_expedition]):
                log("SimplePrinter: Données manquantes pour shipping_update", level="ERROR")
                return
                
            # Mettre à jour le CSV
            success = CSVSerialManager.update_csv_with_shipping_timestamp(serial_number, timestamp_expedition)
            
            if success:
                log(f"SimplePrinter: Timestamp expédition mis à jour: {serial_number}", level="INFO")
            else:
                log(f"SimplePrinter: Échec mise à jour expédition: {serial_number}", level="ERROR")
                
        except json.JSONDecodeError:
            log("SimplePrinter: Payload JSON invalide pour shipping_update", level="ERROR")
        except Exception as e:
            log(f"SimplePrinter: Erreur shipping_update: {e}", level="ERROR")
            
    def _handle_test_done(self, payload_str):
        """Gère la fin d'un test de batterie."""
        try:
            data = json.loads(payload_str)
            serial_number = data.get("serial_number")
            timestamp_test_done = data.get("timestamp_test_done")
            
            if not all([serial_number, timestamp_test_done]):
                log("SimplePrinter: Données manquantes pour test_done", level="ERROR")
                return
                
            # Mettre à jour le CSV avec timestamp test
            csv_success = CSVSerialManager.update_csv_with_test_done_timestamp(serial_number, timestamp_test_done)
            
            # Récupérer les détails pour impression
            found_serial, random_code, _ = CSVSerialManager.get_details_for_reprint_from_csv(serial_number)
            
            # Imprimer étiquette standard et expédition
            print_success = True
            if found_serial and random_code:
                print_success &= self._print_main_label(serial_number, random_code)
            print_success &= self._print_shipping_label(serial_number)
            
            if csv_success and print_success:
                log(f"SimplePrinter: Test terminé traité avec succès: {serial_number}", level="INFO")
            else:
                log(f"SimplePrinter: Traitement partiel test_done: {serial_number}", level="WARNING")
                
        except json.JSONDecodeError:
            log("SimplePrinter: Payload JSON invalide pour test_done", level="ERROR")
        except Exception as e:
            log(f"SimplePrinter: Erreur test_done: {e}", level="ERROR")
            
    def _handle_batch_creation(self, payload_str):
        """Gère la création de lots d'étiquettes."""
        try:
            num_labels = int(payload_str.strip())
            
            if num_labels <= 0 or num_labels > 100:  # Limite de sécurité
                log(f"SimplePrinter: Nombre d'étiquettes invalide: {num_labels}", level="ERROR")
                return
                
            log(f"SimplePrinter: Création de {num_labels} étiquettes en lot", level="INFO")
            
            success_count = 0
            for i in range(num_labels):
                # Générer les données
                serial_number = CSVSerialManager.generate_next_serial_number()
                random_code = CSVSerialManager.generate_random_code()
                timestamp_iso = datetime.now().isoformat()
                timestamp_test_done = datetime.now().isoformat()
                fabrication_date = datetime.now().strftime("%d/%m/%Y")
                
                # Enregistrer dans CSV
                if not CSVSerialManager.add_serial_to_csv(timestamp_iso, serial_number, random_code):
                    continue
                    
                # Mettre à jour test_done
                CSVSerialManager.update_csv_with_test_done_timestamp(serial_number, timestamp_test_done)
                
                # Imprimer les 3 étiquettes
                success = True
                success &= self._print_v1_label(serial_number, random_code, fabrication_date)
                success &= self._print_main_label(serial_number, random_code)
                success &= self._print_shipping_label(serial_number)
                
                if success:
                    success_count += 1
                    
            log(f"SimplePrinter: Lot terminé: {success_count}/{num_labels} étiquettes créées", level="INFO")
            
        except ValueError:
            log(f"SimplePrinter: Nombre invalide pour batch_creation: {payload_str}", level="ERROR")
        except Exception as e:
            log(f"SimplePrinter: Erreur batch_creation: {e}", level="ERROR")
            
    def _print_v1_label(self, serial_number, random_code, fabrication_date):
        """Imprime une étiquette V1."""
        zpl_command = LabelTemplates.get_v1_label_zpl(serial_number, random_code, fabrication_date)
        return self._send_zpl_to_printer(zpl_command, f"V1 {serial_number}")
        
    def _print_main_label(self, serial_number, random_code):
        """Imprime une étiquette principale."""
        zpl_command = LabelTemplates.get_main_label_zpl(serial_number, random_code)
        return self._send_zpl_to_printer(zpl_command, f"Main {serial_number}")
        
    def _print_shipping_label(self, serial_number):
        """Imprime une étiquette d'expédition."""
        zpl_command = LabelTemplates.get_shipping_label_zpl(serial_number)
        return self._send_zpl_to_printer(zpl_command, f"Shipping {serial_number}")
        
    def _send_zpl_to_printer(self, zpl_command, description=""):
        """
        Envoie une commande ZPL à l'imprimante.
        
        Args:
            zpl_command (str): Commande ZPL à envoyer
            description (str): Description pour les logs
            
        Returns:
            bool: True si succès, False sinon
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(PrinterConfig.SOCKET_TIMEOUT_S)
            sock.connect((PrinterConfig.PRINTER_IP, PrinterConfig.PRINTER_PORT))
            sock.sendall(zpl_command.encode('utf-8'))
            sock.close()
            
            log(f"SimplePrinter: Impression réussie: {description}", level="INFO")
            return True
            
        except socket.timeout:
            log(f"SimplePrinter: Timeout impression: {description}", level="ERROR")
            return False
        except socket.error as e:
            log(f"SimplePrinter: Erreur socket impression {description}: {e}", level="ERROR")
            return False
        except Exception as e:
            log(f"SimplePrinter: Erreur impression {description}: {e}", level="ERROR")
            return False
            
    def _update_printer_status(self):
        """Met à jour et publie le statut de l'imprimante."""
        try:
            # Test simple de connexion
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)  # Timeout court pour le test
            sock.connect((PrinterConfig.PRINTER_IP, PrinterConfig.PRINTER_PORT))
            sock.close()
            
            new_status = "on"
            
        except Exception:
            new_status = "off"
            
        # Publier seulement si le statut a changé
        if new_status != self.printer_status:
            self.printer_status = new_status
            
            if self.mqtt_client and self.mqtt_client.is_connected():
                self.mqtt_client.publish("printer/status", new_status, qos=1, retain=True)
                log(f"SimplePrinter: Statut publié: {new_status}", level="INFO")


def main():
    """Point d'entrée principal."""
    try:
        log("SimplePrinter: Démarrage du service d'impression simplifié", level="INFO")
        printer = SimplePrinter()
        printer.start()
        
    except KeyboardInterrupt:
        log("SimplePrinter: Arrêt demandé par l'utilisateur", level="INFO")
    except Exception as e:
        log(f"SimplePrinter: Erreur critique: {e}", level="ERROR")


if __name__ == "__main__":
    main()