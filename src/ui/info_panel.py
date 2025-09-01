# -*- coding: utf-8 -*-
"""
Gestionnaire pour la zone d'informations de l'interface utilisateur.
"""

import threading
import time
from src.labels import CSVSerialManager
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
        info_container.columnconfigure(0, weight=1)

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
        Collecte toutes les données nécessaires depuis le CSV.
        
        Returns:
            dict: Dictionnaire contenant toutes les informations
        """
        try:
            data = {
                'last_serial': 'Aucun',
                'shipped_today': 0,
                'shipped_this_month': 0,
                'produced_today': 0,
                'update_time': time.strftime("%H:%M:%S")
            }

            # Dernier serial imprimé
            last_serial = CSVSerialManager.get_last_serial_from_csv()
            if last_serial:
                data['last_serial'] = last_serial

            # Statistiques depuis le CSV
            stats = self._calculate_csv_stats()
            data.update(stats)

            return data

        except Exception as e:
            log(f"InfoPanel: Erreur collecte données: {e}", level="ERROR")
            return {
                'last_serial': 'Erreur',
                'shipped_today': 'Erreur',
                'shipped_this_month': 'Erreur',
                'produced_today': 'Erreur',
                'update_time': time.strftime("%H:%M:%S")
            }

    def _calculate_csv_stats(self):
        """
        Calcule les statistiques depuis le fichier CSV.
        
        Returns:
            dict: Statistiques calculées
        """
        import csv
        import os
        from datetime import datetime

        stats = {
            'shipped_today': 0,
            'shipped_this_month': 0,
            'produced_today': 0
        }

        try:
            if not os.path.exists(CSVSerialManager.SERIAL_CSV_FILE):
                return stats

            today_str = datetime.now().strftime("%Y-%m-%d")
            current_month_str = datetime.now().strftime("%Y-%m")

            with open(CSVSerialManager.SERIAL_CSV_FILE,
                      mode='r',
                      newline='',
                      encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    if row and row.get('NumeroSerie'):

                        # Produites aujourd'hui (TimestampImpression)
                        timestamp_impression = row.get('TimestampImpression',
                                                       '')
                        if timestamp_impression.startswith(today_str):
                            stats['produced_today'] += 1

                        # Expédiées aujourd'hui (TimestampExpedition)
                        timestamp_expedition = row.get('TimestampExpedition',
                                                       '')
                        if timestamp_expedition.startswith(today_str):
                            stats['shipped_today'] += 1

                        # Expédiées ce mois-ci (TimestampExpedition)
                        if timestamp_expedition:
                            try:
                                # Extraire YYYY-MM du timestamp (ex: "2025-07-24T15:35:01" -> "2025-07")
                                expedition_month = timestamp_expedition[:
                                                                        7]  # Prend les 7 premiers caractères
                                if expedition_month == current_month_str:
                                    stats['shipped_this_month'] += 1
                            except (IndexError, ValueError):
                                pass  # Ignorer les timestamps malformés

        except Exception as e:
            log(f"InfoPanel: Erreur calcul statistiques CSV: {e}",
                level="ERROR")

        return stats

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

    def manual_refresh(self):
        """Force une mise à jour manuelle immédiate."""
        try:
            data = self._collect_data()
            self._update_display(data)
            log("InfoPanel: Mise à jour manuelle effectuée", level="INFO")
        except Exception as e:
            log(f"InfoPanel: Erreur mise à jour manuelle: {e}", level="ERROR")
