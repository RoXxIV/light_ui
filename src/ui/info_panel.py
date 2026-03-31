# -*- coding: utf-8 -*-
"""
Gestionnaire pour la zone d'informations de l'interface utilisateur.
"""

import threading
import time
from src.db import SQLiteManager
from src.ui.system_utils import log


class InfoPanel:
    """
    Gestionnaire pour la zone d'informations affichant les données en temps réel.
    """

    def __init__(self, parent_app):
        """
        Initialise le panneau d'informations.
        
        Args:
            parent_app: Instance de l'application principale (SimpleApp)
        """
        self.app = parent_app
        self.info_labels = {}
        self.update_thread = None
        self.is_running = False

        log("InfoPanel: Gestionnaire initialisé", level="INFO")

    def create_info_widgets(self, parent_frame):
        """
        Crée les widgets d'information dans le frame parent.
        
        Args:
            parent_frame: Frame CTk où ajouter les widgets
        """
        import customtkinter as ctk

        # Configuration du frame parent
        parent_frame.columnconfigure(0, weight=1)

        # Titre de la zone d'informations
        title_label = ctk.CTkLabel(parent_frame,
                                   text="📋 INFORMATIONS SYSTÈME",
                                   font=("Helvetica", 16, "bold"),
                                   text_color="#B0B0B0")
        title_label.grid(row=0, column=0, pady=(10, 15), padx=10, sticky="w")

        # Frame container pour les informations
        info_container = ctk.CTkFrame(parent_frame, fg_color="transparent")
        info_container.grid(row=1,
                            column=0,
                            padx=10,
                            pady=(0, 10),
                            sticky="nsew")
        info_container.columnconfigure(0, weight=1, uniform="btn")
        info_container.columnconfigure(1, weight=1, uniform="btn")

        # Dernier serial imprimé
        self.info_labels['last_serial'] = ctk.CTkLabel(
            info_container,
            text="Dernier serial imprimé : Chargement...",
            font=("Helvetica", 14),
            text_color="#FFFFFF",
            anchor="w")
        self.info_labels['last_serial'].grid(row=0,
                                             column=0,
                                             padx=5,
                                             pady=3,
                                             sticky="w")

        # Batteries expédiées aujourd'hui
        self.info_labels['shipped_today'] = ctk.CTkLabel(
            info_container,
            text="Expédiées aujourd'hui : Chargement...",
            font=("Helvetica", 14),
            text_color="#FFFFFF",
            anchor="w")
        self.info_labels['shipped_today'].grid(row=2,
                                               column=0,
                                               padx=5,
                                               pady=3,
                                               sticky="w")

        # Batteries expédiées ce mois-ci
        self.info_labels['shipped_this_month'] = ctk.CTkLabel(
            info_container,
            text="Expédiées ce mois-ci : Chargement...",
            font=("Helvetica", 14),
            text_color="#FFFFFF",
            anchor="w")
        self.info_labels['shipped_this_month'].grid(row=3,
                                                    column=0,
                                                    padx=5,
                                                    pady=3,
                                                    sticky="w")

        # Batteries produites aujourd'hui
        self.info_labels['produced_today'] = ctk.CTkLabel(
            info_container,
            text="Produites aujourd'hui : Chargement...",
            font=("Helvetica", 14),
            text_color="#FFFFFF",
            anchor="w")
        self.info_labels['produced_today'].grid(row=4,
                                                column=0,
                                                padx=5,
                                                pady=3,
                                                sticky="w")

        # Dernière mise à jour
        self.info_labels['last_update'] = ctk.CTkLabel(
            info_container,
            text="Dernière MAJ : --:--:--",
            font=("Helvetica", 11),
            text_color="#808080",
            anchor="w")
        self.info_labels['last_update'].grid(row=5,
                                             column=0,
                                             padx=5,
                                             pady=(10, 3),
                                             sticky="w")

        # Ligne 1 : Créer | Finish
        self.btn_create = ctk.CTkButton(
            info_container,
            text="➕ Créer",
            command=self._on_create_click,
            font=("Helvetica", 12, "bold"),
            height=32,
            fg_color="#1C98F1",
            hover_color="#0D72BB",
        )
        self.btn_create.grid(row=6,
                             column=0,
                             padx=(5, 2),
                             pady=(20, 4),
                             sticky="ew")

        self.btn_finish = ctk.CTkButton(
            info_container,
            text="🔋 Finish",
            command=self._on_finish_click,
            font=("Helvetica", 12, "bold"),
            height=32,
            fg_color="#1C98F1",
            hover_color="#0D72BB",
        )
        self.btn_finish.grid(row=6,
                             column=1,
                             padx=(2, 5),
                             pady=(20, 4),
                             sticky="ew")

        # Confirmer finish — pleine largeur, caché par défaut
        self.btn_finish_confirm = ctk.CTkButton(
            info_container,
            text="✅ Confirmer le finish",
            command=self._on_finish_confirm_click,
            font=("Helvetica", 12, "bold"),
            height=32,
            fg_color="#00C050",
            hover_color="#037934",
        )
        self.btn_finish_confirm.grid(row=7,
                                     column=0,
                                     columnspan=2,
                                     padx=5,
                                     pady=(4, 4),
                                     sticky="ew")
        self.btn_finish_confirm.grid_remove()

        # Ligne 2 : Expédition | SAV
        self.btn_expedition = ctk.CTkButton(
            info_container,
            text="📦 Expédition",
            command=self._on_expedition_click,
            font=("Helvetica", 12, "bold"),
            height=32,
            fg_color="#1C98F1",
            hover_color="#0D72BB",
        )
        self.btn_expedition.grid(row=8,
                                 column=0,
                                 padx=(5, 2),
                                 pady=(4, 4),
                                 sticky="ew")

        self.btn_sav = ctk.CTkButton(
            info_container,
            text="🔧 SAV",
            command=self._on_sav_click,
            font=("Helvetica", 12, "bold"),
            height=32,
            fg_color="#1C98F1",
            hover_color="#0D72BB",
        )
        self.btn_sav.grid(row=8,
                          column=1,
                          padx=(2, 5),
                          pady=(4, 4),
                          sticky="ew")

        # Annuler — centré, plus petit, caché par défaut
        self.btn_cancel = ctk.CTkButton(
            info_container,
            text="Annuler",
            command=self._on_cancel_click,
            font=("Helvetica", 11),
            height=26,
            fg_color="#B71C1C",
            hover_color="#7F0000",
        )
        self.btn_cancel.grid(row=9,
                             column=0,
                             columnspan=2,
                             padx=50,
                             pady=(6, 4))
        self.btn_cancel.grid_remove()

    def start_updates(self):
        """Démarre les mises à jour automatiques des informations."""
        if self.is_running:
            return

        self.is_running = True
        self.update_thread = threading.Thread(target=self._update_loop,
                                              daemon=True)
        self.update_thread.start()

        log("InfoPanel: Mises à jour automatiques démarrées", level="INFO")

    def stop_updates(self):
        """Arrête les mises à jour automatiques."""
        self.is_running = False
        log("InfoPanel: Mises à jour automatiques arrêtées", level="INFO")

    def _update_loop(self):
        """Boucle de mise à jour des informations (thread séparé)."""
        while self.is_running:
            try:
                # Récupérer les données
                data = self._collect_data()

                # Mettre à jour l'interface (thread-safe)
                self.app.after(0, lambda: self._update_display(data))

                # Attendre avant la prochaine mise à jour (30 secondes)
                time.sleep(30)

            except Exception as e:
                log(f"InfoPanel: Erreur dans la boucle de mise à jour: {e}",
                    level="ERROR")
                time.sleep(10)  # Attendre plus longtemps en cas d'erreur

    def _collect_data(self):
        """
        Collecte toutes les données nécessaires depuis SQLite.

        Returns:
            dict: Dictionnaire contenant toutes les informations
        """
        try:
            return {
                'last_serial': SQLiteManager.get_last_serial() or 'Aucun',
                'produced_today': SQLiteManager.count_produced_today(),
                'shipped_today': SQLiteManager.count_shipped_today(),
                'shipped_this_month': SQLiteManager.count_shipped_this_month(),
                'update_time': time.strftime("%H:%M:%S"),
            }
        except Exception as e:
            log(f"InfoPanel: Erreur collecte données: {e}", level="ERROR")
            return {
                'last_serial': 'Erreur',
                'shipped_today': 'Erreur',
                'shipped_this_month': 'Erreur',
                'produced_today': 'Erreur',
                'update_time': time.strftime("%H:%M:%S"),
            }

    def _update_display(self, data):
        """
        Met à jour l'affichage avec les nouvelles données.
        
        Args:
            data (dict): Données à afficher
        """
        try:
            # Mettre à jour chaque label
            if 'last_serial' in self.info_labels:
                self.info_labels['last_serial'].configure(
                    text=f"Dernier serial imprimé : {data['last_serial']}")

            if 'shipped_today' in self.info_labels:
                self.info_labels['shipped_today'].configure(
                    text=f"Expédiées aujourd'hui : {data['shipped_today']}")

            if 'shipped_this_month' in self.info_labels:
                self.info_labels['shipped_this_month'].configure(
                    text=f"Expédiées ce mois-ci : {data['shipped_this_month']}"
                )

            if 'produced_today' in self.info_labels:
                self.info_labels['produced_today'].configure(
                    text=f"Produites aujourd'hui : {data['produced_today']}")

            if 'last_update' in self.info_labels:
                self.info_labels['last_update'].configure(
                    text=f"Dernière MAJ : {data['update_time']}")

        except Exception as e:
            log(f"InfoPanel: Erreur mise à jour affichage: {e}", level="ERROR")

    def _on_finish_click(self):
        """Ouvre le modal de sélection du modèle kWh pour le finish."""
        import customtkinter as ctk
        from src.labels.printer_config import PrinterConfig

        MODELS = {
            "13": "13 kWh  —  271 Ah  (types A, B, C)",
            "12": "12 kWh  —  250 Ah  (types A, B, C)",
            "8.6": " 8.6 kWh  —  175 Ah  (types D, E)",
        }

        modal = ctk.CTkToplevel(self.app)
        modal.title("Finish — Choisir le modèle")
        modal.geometry("360x280")
        modal.resizable(False, False)
        modal.grab_set()
        modal.focus_set()

        ctk.CTkLabel(modal,
                     text="Capacité finale de la batterie",
                     font=("Helvetica", 15, "bold")).pack(pady=(18, 4))
        ctk.CTkLabel(modal,
                     text="Scannez ensuite le QR intérieur",
                     font=("Helvetica", 11),
                     text_color="#808080").pack(pady=(0, 14))

        def send(model_key):
            modal.destroy()
            self.app.scan_manager.process_scan(f"finish {model_key}")
            self.btn_cancel.grid()

        for key, label in MODELS.items():
            ctk.CTkButton(
                modal,
                text=label,
                command=lambda k=key: send(k),
                font=("Helvetica", 13),
                height=40,
                anchor="w",
                fg_color="#1C98F1",
                hover_color="#0D72BB",
            ).pack(fill="x", padx=20, pady=4)

        ctk.CTkButton(
            modal,
            text="Annuler",
            command=modal.destroy,
            font=("Helvetica", 11),
            height=28,
            fg_color="#B71C1C",
            hover_color="#7F0000",
        ).pack(fill="x", padx=20, pady=(8, 16))

    def _on_finish_confirm_click(self):
        """Confirme le finish — équivalent au re-scan 'finish <kWh>'."""
        model_key = self.app.scan_manager.validated_model
        if model_key:
            self.app.scan_manager.process_scan(f"finish {model_key}")

    def show_finish_confirm_button(self):
        """Affiche le bouton de confirmation finish (appelé par scan_manager)."""
        if hasattr(self, 'btn_finish_confirm'):
            self.btn_finish_confirm.grid()

    def _on_create_click(self):
        """Ouvre le modal de sélection du type de batterie."""
        import customtkinter as ctk

        MATERIALS = {
            'A': "28.8 kWh  —  Alu",
            'B': "14.4 kWh  —  Alu",
            'C': "14.4 kWh  —  Acier",
            'D': "9.6 kWh   —  Alu",
            'E': "9.6 kWh   —  Acier",
        }

        modal = ctk.CTkToplevel(self.app)
        modal.title("Nouvelle batterie")
        modal.geometry("340x380")
        modal.resizable(False, False)
        modal.grab_set()  # rend la fenêtre modale
        modal.focus_set()

        ctk.CTkLabel(modal,
                     text="Choisir le type de source",
                     font=("Helvetica", 15, "bold")).pack(pady=(18, 4))
        ctk.CTkLabel(modal,
                     text="Cliquez sur la lettre correspondante",
                     font=("Helvetica", 11),
                     text_color="#808080").pack(pady=(0, 14))

        def send(letter):
            modal.destroy()
            self.app.scan_manager.process_scan(f"create {letter}")

        for letter, description in MATERIALS.items():
            ctk.CTkButton(
                modal,
                text=f"{letter}  —  {description}",
                command=lambda l=letter: send(l),
                font=("Helvetica", 13),
                height=40,
                anchor="w",
                fg_color="#1C98F1",
                hover_color="#0D72BB",
            ).pack(fill="x", padx=20, pady=4)

        ctk.CTkButton(
            modal,
            text="Annuler",
            command=modal.destroy,
            font=("Helvetica", 11),
            height=30,
            fg_color="#B71C1C",
            hover_color="#7F0000",
        ).pack(fill="x", padx=20, pady=(10, 16))

    def _on_expedition_click(self):
        """Envoie la commande 'expedition' — identique au QR ou au clavier."""
        self.app.scan_manager.process_scan("expedition")
        if self.app.scan_manager.expedition_mode_active:
            self.btn_expedition.configure(
                text="✅ Valider l'expédition",
                fg_color="#00C050",
                hover_color="#037934",
            )
            self.btn_cancel.grid()
        else:
            self.btn_expedition.configure(
                text="📦 Expédition",
                fg_color="#1C98F1",
                hover_color="#0D72BB",
            )
            self.btn_cancel.grid_remove()

    def _on_sav_click(self):
        """Envoie la commande 'sav' — identique au QR ou au clavier."""
        self.app.scan_manager.process_scan("sav")
        self.btn_cancel.grid()

    def _on_cancel_click(self):
        """Envoie la commande 'cancel' — identique au QR ou au clavier."""
        self.app.scan_manager.process_scan("cancel")

    def reset_action_buttons(self):
        """Remet les boutons à leur état initial (appelé par scan_manager après reset)."""
        if hasattr(self, 'btn_expedition'):
            self.btn_expedition.configure(
                text="📦 Expédition",
                fg_color="#1C98F1",
                hover_color="#0D72BB",
            )
        if hasattr(self, 'btn_finish_confirm'):
            self.btn_finish_confirm.grid_remove()
        if hasattr(self, 'btn_cancel'):
            self.btn_cancel.grid_remove()

    def manual_refresh(self):
        """Force une mise à jour manuelle immédiate."""
        try:
            data = self._collect_data()
            self._update_display(data)
            log("InfoPanel: Mise à jour manuelle effectuée", level="INFO")
        except Exception as e:
            log(f"InfoPanel: Erreur mise à jour manuelle: {e}", level="ERROR")
