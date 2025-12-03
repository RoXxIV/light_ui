# -*- coding: utf-8 -*-
"""
Templates et configuration pour les emails du système de test de batteries.

Ce module centralise tous les templates d'email utilisés par l'application,
permettant une maintenance et une personnalisation plus faciles.
"""
from datetime import datetime
from typing import List, Dict
from src.labels.printer_config import PrinterConfig


class EmailTemplates:
    """
    Classe statique contenant tous les templates d'email utilisés par l'application.
    
    Cette classe fournit des méthodes pour générer le contenu des emails
    avec les données appropriées, en séparant clairement la logique de 
    présentation de la logique métier.
    """

    # CONFIGURATION DES SIGNATURES
    SENDER_NAME = "Evan Hermier"
    COMPANY_NAME = "L'équipe Revaw"

    # TEMPLATES EMAIL EXPÉDITION
    @staticmethod
    def generate_expedition_email_content(
            serial_numbers: List[str],
            timestamp_expedition: str,
            sav_serials: List[str] | None = None) -> tuple[str, str]:
        """
        Génère le contenu complet d'un email d'expédition (texte et HTML).
        """
        if sav_serials is None: sav_serials = []
        try:
            dt_expedition = datetime.fromisoformat(timestamp_expedition)
            date_formatee = dt_expedition.strftime("%d/%m/%Y à %H:%M:%S")
        except ValueError:
            date_formatee = timestamp_expedition

        # --- NOUVELLE LOGIQUE DE REGROUPEMENT ---
        # Regrouper les numéros de série par modèle et SAV
        serials_by_model: Dict[str, List[str]] = {}

        for serial in serial_numbers:
            is_sav = serial in sav_serials  # Vérifie si c'est un SAV

            found_model = False
            for model_key, model_info in PrinterConfig.BATTERY_MODELS.items():
                if model_info['ah'] in serial:
                    kwh = model_info['energy']

                    # Détermine le nom de la catégorie (SAV ou Standard)
                    if is_sav:
                        model_name = f"Retours SAV {kwh}kWh"
                    else:
                        model_name = f"Batteries {kwh}kWh"

                    if model_name not in serials_by_model:
                        serials_by_model[model_name] = []
                    serials_by_model[model_name].append(serial)
                    found_model = True
                    break

            if not found_model:
                # Gestion des cas inconnus, séparés aussi
                cat_name = "Autres (SAV)" if is_sav else "Autres"
                if cat_name not in serials_by_model:
                    serials_by_model[cat_name] = []
                serials_by_model[cat_name].append(serial)

        # Génération des contenus (les méthodes _generate... utilisent le dictionnaire qu'on vient de créer)
        contenu_texte = EmailTemplates._generate_expedition_text_content(
            serials_by_model, date_formatee)
        contenu_html = EmailTemplates._generate_expedition_html_content(
            serials_by_model, date_formatee)

        return contenu_texte, contenu_html

    @staticmethod
    def generate_expedition_subject(timestamp_expedition: str,
                                    total_batteries: int | None = None) -> str:
        """
        Génère l'objet de l'email d'expédition.
        
        Args:
            timestamp_expedition (str): Timestamp d'expédition au format ISO
            total_batteries (int, optional): Nombre total de batteries expédiées
            
        Returns:
            str: L'objet de l'email formaté
        """
        try:
            dt_expedition = datetime.fromisoformat(timestamp_expedition)
            date_formatee = dt_expedition.strftime("%d/%m/%Y à %H:%M:%S")
        except ValueError:
            date_formatee = timestamp_expedition

        if total_batteries:
            return f"Expédition de {total_batteries} batterie{'s' if total_batteries > 1 else ''} - {date_formatee}"
        else:
            return f"Récapitulatif d'expedition du {date_formatee}"

    @staticmethod
    def _generate_expedition_text_content(serials_by_model: Dict[str,
                                                                 List[str]],
                                          date_formatee: str) -> str:
        """
        Génère le contenu texte de l'email d'expédition.
        """
        total_batteries = sum(
            len(serials) for serials in serials_by_model.values())

        corps_principal = f"Bonjour,\n\nVoici la liste des batteries marquées comme expédiées le {date_formatee}:\n\n"

        # Boucle sur chaque modèle trouvé
        for model_name, serials in serials_by_model.items():
            total_model = len(serials)
            corps_principal += f"--- {model_name} ({total_model}) ---\n"
            for i, serial in enumerate(serials, 1):
                corps_principal += f"{i:2d}. {serial}\n"
            corps_principal += "\n"

        # Ligne de total
        recap_total = f"📦 TOTAL EXPÉDIÉ: {total_batteries} batterie{'s' if total_batteries > 1 else ''}"
        corps_principal += recap_total + "\n"

        # Formule de politesse
        formule_politesse = f"\nCordialement,\n{EmailTemplates.SENDER_NAME}\n"

        # Zone de signature manuelle
        zone_signature = """
    Nom : _________________________

    Signature :


    _________________________________________
    """

        # Signature de l'entreprise
        signature_entreprise = f"""
    -- 
    {EmailTemplates.COMPANY_NAME}
    """

        return corps_principal + formule_politesse + zone_signature + signature_entreprise

    @staticmethod
    def _generate_expedition_html_content(serials_by_model: Dict[str,
                                                                 List[str]],
                                          date_formatee: str) -> str:
        """
        Génère le contenu HTML de l'email d'expédition.
        """
        total_batteries = sum(
            len(serials) for serials in serials_by_model.values())
        description = f"des <strong>{total_batteries} batteries</strong> marquées comme expédiées" if total_batteries > 1 else "de la batterie marquée comme expédiée"

        html_body = f"""
            <html>
            <body>
                <p>Bonjour,</p>
                <p>Voici la liste {description} le <strong>{date_formatee}</strong>:</p>
            """

        # Boucle sur chaque modèle trouvé
        for model_name, serials in serials_by_model.items():
            total_model = len(serials)
            html_body += f'<h3>{model_name} ({total_model})</h3><ul>'
            for serial in serials:
                html_body += f"<li><strong>{serial}</strong></li>"
            html_body += "</ul>"

        # Récapitulatif
        recap_detail_parts = [
            f"{len(serials)} en {model_name.split(' ')[1]}"
            for model_name, serials in serials_by_model.items()
        ]
        recap_detail_str = f"(Détail: {', '.join(recap_detail_parts)})" if len(
            recap_detail_parts) > 1 else ""

        html_body += f"""
            <div style="margin-top: 20px; padding: 15px; background-color: #f0f8ff; border-left: 4px solid #4CAF50;">
                <p style="margin: 0; font-weight: bold; font-size: 16px;">
                    📦 TOTAL EXPÉDIÉ: {total_batteries} batterie{'s' if total_batteries > 1 else ''}
                </p>
                <p style="margin: 5px 0 0 0; font-size: 14px; color: #555;">
                    {recap_detail_str}
                </p>
            </div>
            
            <p>Cordialement,</p>
            <p>{EmailTemplates.SENDER_NAME}</p>
        """

        # Zone de signature manuelle
        html_signature_zone = """
            <div style="margin-top: 40px; font-family: Arial, sans-serif; font-size: 14px;">
                <p><strong>Nom :</strong></p>
                <p style="margin-top: 20px;"><strong>Signature :</strong></p>
                <div style="border: 1px solid #000; height: 80px; width: 280px; margin-bottom: 5px;"></div>
            </div>
            """

        # Signature de l'entreprise
        html_signature_entreprise = f"""
            <hr>
            <p style="color: #666666; font-family: Arial, sans-serif; font-size: 12px;">
            <strong>{EmailTemplates.COMPANY_NAME}</strong><br>
            </p>
            """

        # Fermeture HTML
        html_fermeture = """
            </body>
            </html>
            """

        return (html_body + html_signature_zone + html_signature_entreprise +
                html_fermeture)
