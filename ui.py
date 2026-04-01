#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scanning, impression, expédition, messages utilisateur.
"""

import tkinter as tk
import customtkinter as ctk
import paho.mqtt.client as mqtt
import threading
import socket
import time
import os
from src.ui.system_utils import log, MQTT_BROKER, MQTT_PORT
from src.ui.scan_manager import ScanManager
from src.ui.info_panel import InfoPanel
from src.db import SQLiteManager

# Import des modules email pour s'assurer qu'ils sont disponibles
try:
    from src.ui.email import EmailTemplates, email_config
    EMAIL_AVAILABLE = True
except ImportError as e:
    log(f"SimpleUI: Modules email non disponibles: {e}", level="WARNING")
    EMAIL_AVAILABLE = False

ctk.set_appearance_mode("dark")


class SimpleApp(ctk.CTk):
    """
    Interface utilisateur.
    """

    def __init__(self):
        super().__init__()

        # === INITIALISATION DES ATTRIBUTS ===
        self.mqtt_client = None

        # === CONFIGURATION FENÊTRE ===
        self.title("Revaw - Interface de production")
        self.geometry("1200x800")
        self.attributes("-fullscreen", True)
        self.bind("<Escape>", lambda e: self.attributes("-fullscreen", False))
        self.bind("<F11>", lambda e: self.attributes("-fullscreen", True))
        self.bind("<Return>", self.handle_prompt)

        # === CONFIGURATION GRILLE ===
        self.rowconfigure(0, weight=1)  # Zone principale (divisée en 2)
        self.rowconfigure(1, weight=0)  # Zone scan
        self.rowconfigure(2, weight=0)  # Zone système
        self.columnconfigure(0, weight=1)

        # === GESTIONNAIRES (CRÉÉS AVANT _setup_ui) ===
        self.info_panel = InfoPanel(self)
        self.scan_manager = ScanManager(self)

        self._setup_ui()
        self._setup_mqtt()

        # Vérifier la disponibilité des emails
        if not EMAIL_AVAILABLE:
            self.add_message(
                "⚠️ Modules email non disponibles - expéditions sans email",
                "warning")

        # Focus sur l'entrée
        self.after(100, lambda: self.entry_prompt.focus_set())

        # Démarrer les mises à jour d'informations après un court délai
        self.after(1000, self._start_info_updates)

    def _start_info_updates(self):
        """Démarre les mises à jour d'informations de manière sécurisée."""
        try:
            self.info_panel.start_updates()
        except Exception as e:
            log(f"SimpleUI: Erreur démarrage mises à jour infos: {e}",
                level="ERROR")

    def _setup_ui(self):
        """Configure l'interface utilisateur."""

        # === ZONE PRINCIPALE (divisée en 2 : messages 3/4 + infos 1/4) ===
        self.frame_main = ctk.CTkFrame(self, corner_radius=10)
        self.frame_main.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.frame_main.rowconfigure(0, weight=1)
        self.frame_main.columnconfigure(0, weight=3)  # Zone messages (3/4)
        self.frame_main.columnconfigure(1, weight=1)  # Zone infos (1/4)

        # === ZONE MESSAGES (3/4 gauche) ===
        self.frame_messages = ctk.CTkFrame(self.frame_main, corner_radius=10)
        self.frame_messages.grid(row=0,
                                 column=0,
                                 padx=(0, 5),
                                 pady=0,
                                 sticky="nsew")
        self.frame_messages.rowconfigure(0, weight=1)
        self.frame_messages.columnconfigure(0, weight=1)

        # Zone de défilement pour les messages
        self.messages_textbox = ctk.CTkTextbox(self.frame_messages,
                                               font=("Consolas", 14),
                                               wrap="word",
                                               state="disabled")
        self.messages_textbox.grid(row=0,
                                   column=0,
                                   padx=10,
                                   pady=10,
                                   sticky="nsew")

        # === ZONE INFORMATIONS (1/4 droite) ===
        self.frame_info_panel = ctk.CTkFrame(self.frame_main,
                                             corner_radius=10,
                                             border_width=1,
                                             border_color="#404040")
        self.frame_info_panel.grid(row=0,
                                   column=1,
                                   padx=(5, 0),
                                   pady=0,
                                   sticky="nsew")
        self.frame_info_panel.rowconfigure(1, weight=1)
        self.frame_info_panel.columnconfigure(0, weight=1)

        # Créer les widgets d'informations via InfoPanel
        self.info_panel.create_info_widgets(self.frame_info_panel)

        # === ZONE SCAN (identique mais référence modifiée) ===
        self.frame_scan = ctk.CTkFrame(self, corner_radius=10)
        self.frame_scan.grid(row=1,
                             column=0,
                             padx=10,
                             pady=(0, 10),
                             sticky="ew")
        self.frame_scan.columnconfigure(0, weight=3)  # Zone scan
        self.frame_scan.columnconfigure(1, weight=1)  # Zone statuts

        # Zone scan gauche
        self.frame_scan_left = ctk.CTkFrame(self.frame_scan,
                                            fg_color="transparent")
        self.frame_scan_left.grid(row=0, column=0, padx=(0, 5), sticky="nsew")
        self.frame_scan_left.columnconfigure(0, weight=1)

        # Labels de réponse
        self.label_response1 = ctk.CTkLabel(self.frame_scan_left,
                                            text="Prêt.",
                                            font=("Helvetica", 18, "bold"))
        self.label_response1.grid(row=0,
                                  column=0,
                                  padx=10,
                                  pady=(10, 5),
                                  sticky="w")

        self.label_response2 = ctk.CTkLabel(
            self.frame_scan_left,
            text="Veuillez scanner ou saisir une commande...",
            font=("Helvetica", 16))
        self.label_response2.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        # Champ de saisie
        self.entry_prompt = ctk.CTkEntry(
            self.frame_scan_left,
            placeholder_text="Scanner ici ou taper une commande",
            font=("Helvetica", 16),
            height=40)
        self.entry_prompt.grid(row=2,
                               column=0,
                               padx=10,
                               pady=(5, 10),
                               sticky="ew")

        # === ZONE STATUTS DROITE (identique) ===
        self.frame_status = ctk.CTkFrame(self.frame_scan,
                                         corner_radius=5,
                                         border_width=1,
                                         border_color="#404040")
        self.frame_status.grid(row=0,
                               column=1,
                               padx=(5, 0),
                               pady=5,
                               sticky="nsew")

        # Titre statuts
        self.status_title = ctk.CTkLabel(self.frame_status,
                                         text="📊 STATUTS",
                                         font=("Helvetica", 14, "bold"),
                                         text_color="#B0B0B0")
        self.status_title.pack(pady=(5, 5))

        # Statut MQTT
        self.mqtt_status_label = ctk.CTkLabel(self.frame_status,
                                              text="🔄 MQTT: Connexion...",
                                              font=("Helvetica", 11),
                                              text_color="#FFA500",
                                              wraplength=150,
                                              justify="left")
        self.mqtt_status_label.pack(pady=2, padx=8, fill="x")

        # Statut imprimante
        self.printer_status_label = ctk.CTkLabel(
            self.frame_status,
            text="🖨️ Imprimante: Attente...",
            font=("Helvetica", 11),
            text_color="#FFA500",
            wraplength=150,
            justify="left")
        self.printer_status_label.pack(pady=2, padx=8, fill="x")

        # === ZONE INFO SYSTÈME (petite) ===
        self.frame_info = ctk.CTkFrame(self, corner_radius=5)
        self.frame_info.grid(row=2,
                             column=0,
                             padx=10,
                             pady=(0, 10),
                             sticky="ew")

        self.info_label = ctk.CTkLabel(
            self.frame_info,
            text="Commandes: create <A-E> | finish <kWh> | expedition | sav",
            font=("Helvetica", 12),
            text_color="#808080")
        self.info_label.pack(pady=5)

    def _setup_mqtt(self):
        """Configure MQTT."""
        self.mqtt_client = None
        # Démarrer le thread MQTT
        mqtt_thread = threading.Thread(target=self._mqtt_thread, daemon=True)
        mqtt_thread.start()

    def _mqtt_thread(self):
        """Thread MQTT."""
        while True:
            try:
                self.update_status("mqtt", "🔄 MQTT: Connexion...", "#FFA500")

                client = mqtt.Client(
                    client_id=f"simple_ui_{os.getpid()}",
                    callback_api_version=mqtt.
                    CallbackAPIVersion.  # type: ignore
                    VERSION1)

                client.on_connect = self._on_connect
                client.on_message = self._on_message
                client.on_disconnect = self._on_disconnect

                client.connect(MQTT_BROKER, MQTT_PORT, 300)
                self.mqtt_client = client

                client.loop_forever()
                # Pas de break ! La boucle while continue en cas de déconnexion
                #break

            except (socket.timeout, TimeoutError, ConnectionRefusedError,
                    socket.gaierror, OSError) as e:
                log(f"SimpleUI: Erreur réseau MQTT: {e}", level="WARNING")
                self.update_status("mqtt", "❌ MQTT: Erreur réseau", "red")
            except Exception as e:
                log(f"SimpleUI: Erreur MQTT inattendue: {e}", level="ERROR")
                self.update_status("mqtt", "❌ MQTT: Erreur", "red")

            time.sleep(10)

    def _on_connect(self, client, userdata, flags, rc):
        """Callback connexion MQTT."""
        if rc == 0:
            log("SimpleUI: Connexion MQTT réussie", level="INFO")
            self.update_status("mqtt", "✅ MQTT: Connecté", "green")

            # S'abonner au statut imprimante et aux résultats d'opérations
            client.subscribe("printer/status", 0)
            client.subscribe("printer/operation/result", 0)

            self.add_message("✅ Système connecté", "info")

        else:
            log(f"SimpleUI: Connexion MQTT échouée: {rc}", level="ERROR")
            self.update_status("mqtt", f"❌ MQTT: Erreur {rc}", "red")

    def _on_message(self, client, userdata, msg):
        """Callback message MQTT."""
        try:
            payload = msg.payload.decode("utf-8")

            if msg.topic == "printer/status":
                if payload.strip().lower() == "on":
                    self.update_status("printer", "✅ Imprimante: OK", "green")
                else:
                    self.update_status("printer", "❌ Imprimante: Hors ligne",
                                       "red")

            elif msg.topic == "printer/operation/result":
                import json as _json
                data = _json.loads(payload)
                operation = data.get("operation", "")
                success = data.get("success", False)
                message = data.get("message", "")
                if operation == "create":
                    if success:
                        self.add_message(f"✅ {message}", "success")
                        self.scan_manager._reset_scan()
                    else:
                        self.add_message(f"❌ Création échouée: {message}", "error")
                        self.scan_manager._reset_scan()

        except Exception as e:
            log(f"SimpleUI: Erreur traitement message MQTT: {e}",
                level="ERROR")

    def _on_disconnect(self, client, userdata, rc):
        """Callback déconnexion MQTT."""
        log(f"SimpleUI: Déconnexion MQTT: {rc}", level="WARNING")
        self.update_status("mqtt", "❌ MQTT: Déconnecté", "red")
        self.mqtt_client = None

    def handle_prompt(self, event=None):
        """Gère la saisie utilisateur."""
        text = self.entry_prompt.get().strip()
        if not text:
            return

        # Ajouter à l'historique des messages
        self.add_message(f"➤ {text}", "user")

        # Vider le champ
        self.entry_prompt.delete(0, tk.END)

        # Traiter via le scan manager
        self.scan_manager.process_scan(text)

    def add_message(self, message, msg_type="info"):
        """
        Ajoute un message dans la zone principale.
        
        Args:
            message (str): Le message à afficher
            msg_type (str): Type du message (info, success, error, warning, user)
        """
        # Couleurs selon le type
        colors = {
            "info": "#FFFFFF",
            "success": "#6EC207",
            "error": "#FF6B6B",
            "warning": "#FFA500",
            "user": "#87CEEB"
        }

        color = colors.get(msg_type, "#FFFFFF")
        timestamp = time.strftime("%H:%M:%S")

        # Activer l'édition temporairement
        self.messages_textbox.configure(state="normal")

        # Ajouter le message avec couleur
        self.messages_textbox.insert("end", f"[{timestamp}] {message}\n")

        # Colorer la dernière ligne
        line_start = f"end-2l linestart"
        line_end = f"end-2l lineend"
        tag_name = f"color_{msg_type}_{timestamp}"

        self.messages_textbox.tag_add(tag_name, line_start, line_end)
        self.messages_textbox.tag_config(tag_name, foreground=color)

        # Désactiver l'édition
        self.messages_textbox.configure(state="disabled")

        # Scroller vers le bas
        self.messages_textbox.see("end")

        # Déclencher une mise à jour manuelle du panneau d'infos après certaines actions
        if msg_type in ["success"] and any(
                keyword in message.lower()
                for keyword in ["créée", "expédition"]):
            self.after(2000, self._safe_manual_refresh)

    def _safe_manual_refresh(self):
        """Effectue une mise à jour manuelle sécurisée du panneau d'infos."""
        try:
            self.info_panel.manual_refresh()
        except Exception as e:
            log(f"SimpleUI: Erreur refresh manuel: {e}", level="ERROR")

    def update_status(self, status_type, message, color):
        """
        Met à jour un label de statut.
        
        Args:
            status_type (str): Type de statut ("mqtt" ou "printer")
            message (str): Message à afficher
            color (str): Couleur du texte
        """

        def update():
            if status_type == "mqtt" and hasattr(self, 'mqtt_status_label'):
                self.mqtt_status_label.configure(text=message,
                                                 text_color=color)
            elif status_type == "printer" and hasattr(self,
                                                      'printer_status_label'):
                self.printer_status_label.configure(text=message,
                                                    text_color=color)

        # Thread-safe update
        self.after(0, update)

    def update_response_labels(self, msg1=None, msg2=None):
        """
        Met à jour les labels de réponse.
        
        Args:
            msg1 (str): Message pour le premier label
            msg2 (str): Message pour le second label
        """

        def update():
            if msg1 is not None:
                self.label_response1.configure(text=msg1)
            if msg2 is not None:
                self.label_response2.configure(text=msg2)

        self.after(0, update)

    def destroy(self):
        """Nettoyage lors de la fermeture de l'application."""
        try:
            self.info_panel.stop_updates()
        except Exception as e:
            log(f"SimpleUI: Erreur lors du nettoyage: {e}", level="ERROR")
        finally:
            super().destroy()


def main():
    """Point d'entrée principal."""
    try:
        log("SimpleUI: Démarrage de l'application simplifiée", level="INFO")
        SQLiteManager.init_db()
        app = SimpleApp()
        app.mainloop()
        log("SimpleUI: Application terminée", level="INFO")

    except Exception as e:
        log(f"SimpleUI: Erreur critique: {e}", level="ERROR")


if __name__ == "__main__":
    main()
