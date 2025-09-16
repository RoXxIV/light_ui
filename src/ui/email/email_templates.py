# -*- coding: utf-8 -*-
"""
Templates et configuration pour les emails du système de test de batteries.

Ce module centralise tous les templates d'email utilisés par l'application,
permettant une maintenance et une personnalisation plus faciles.
"""
from datetime import datetime
from typing import List


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
            timestamp_expedition: str) -> tuple[str, str]:
        """
        Génère le contenu complet d'un email d'expédition (texte et HTML).
        
        Args:
            serial_numbers (List[str]): Liste des numéros de série expédiés
            timestamp_expedition (str): Timestamp d'expédition au format ISO
            
        Returns:
            tuple[str, str]: (contenu_texte, contenu_html)
        """
        # Formatage de la date
        try:
            dt_expedition = datetime.fromisoformat(timestamp_expedition)
            date_formatee = dt_expedition.strftime("%d/%m/%Y à %H:%M:%S")
        except ValueError:
            date_formatee = timestamp_expedition

        # NOUVEAU: Séparation des batteries par capacité
        serials_13kwh = [s for s in serial_numbers if '271' in s]
        serials_12kwh = [s for s in serial_numbers if '250' in s]

        # Génération du contenu texte
        contenu_texte = EmailTemplates._generate_expedition_text_content(
            serials_13kwh, serials_12kwh, date_formatee)

        # Génération du contenu HTML
        contenu_html = EmailTemplates._generate_expedition_html_content(
            serials_13kwh, serials_12kwh, date_formatee)

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
    def _generate_expedition_text_content(serials_13kwh: List[str],
                                          serials_12kwh: List[str],
                                          date_formatee: str) -> str:
        """
        Génère le contenu texte de l'email d'expédition.
        """
        total_batteries = len(serials_13kwh) + len(serials_12kwh)
        total_13kwh = len(serials_13kwh)
        total_12kwh = len(serials_12kwh)

        # Corps principal (phrase d'intro inchangée)
        corps_principal = f"Bonjour,\n\nVoici la liste des batteries marquées comme expédiées le {date_formatee}:\n\n"

        # Liste des batteries 13kWh
        if serials_13kwh:
            corps_principal += f"--- Batteries 13kWh ({total_13kwh}) ---\n"
            for i, serial in enumerate(serials_13kwh, 1):
                corps_principal += f"{i:2d}. {serial}\n"
            corps_principal += "\n"

        # Liste des batteries 12kWh
        if serials_12kwh:
            corps_principal += f"--- Batteries 12kWh ({total_12kwh}) ---\n"
            for i, serial in enumerate(serials_12kwh, 1):
                corps_principal += f"{i:2d}. {serial}\n"
            corps_principal += "\n"

        # Ligne de total avec détail conditionnel
        recap_total = f"📦 TOTAL EXPÉDIÉ: {total_batteries} batterie{'s' if total_batteries > 1 else ''}"
        if total_13kwh > 0 and total_12kwh > 0:
            recap_total += f" (dont {total_13kwh} en 13kWh et {total_12kwh} en 12kWh)"
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
    def _generate_expedition_html_content(serials_13kwh: List[str],
                                          serials_12kwh: List[str],
                                          date_formatee: str) -> str:
        """
        Génère le contenu HTML de l'email d'expédition.
        """
        total_batteries = len(serials_13kwh) + len(serials_12kwh)
        total_13kwh = len(serials_13kwh)
        total_12kwh = len(serials_12kwh)

        # Description (phrase d'intro inchangée)
        if total_batteries > 1:
            description = f"des <strong>{total_batteries} batteries</strong> marquées comme expédiées"
        else:
            description = "de la batterie marquée comme expédiée"

        # En-tête et introduction
        html_body = f"""
            <html>
            <body>
                <p>Bonjour,</p>
                <p>Voici la liste {description} le <strong>{date_formatee}</strong>:</p>
            """

        # Section pour les batteries 13kWh
        if serials_13kwh:
            html_body += f'<h3>Batteries 13kWh ({total_13kwh})</h3><ul>'
            for serial in serials_13kwh:
                html_body += f"<li><strong>{serial}</strong></li>"
            html_body += "</ul>"

        # Section pour les batteries 12kWh
        if serials_12kwh:
            html_body += f'<h3>Batteries 12kWh ({total_12kwh})</h3><ul>'
            for serial in serials_12kwh:
                html_body += f"<li><strong>{serial}</strong></li>"
            html_body += "</ul>"

        # Récapitulatif
        recap_detail = ""
        if total_13kwh > 0 and total_12kwh > 0:
            recap_detail = f"""
            <p style="margin: 5px 0 0 0; font-size: 14px; color: #555;">
                (Détail: {total_13kwh} en 13kWh et {total_12kwh} en 12kWh)
            </p>
            """

        html_body += f"""
            <div style="margin-top: 20px; padding: 15px; background-color: #f0f8ff; border-left: 4px solid #4CAF50;">
                <p style="margin: 0; font-weight: bold; font-size: 16px;">
                    📦 TOTAL EXPÉDIÉ: {total_batteries} batterie{'s' if total_batteries > 1 else ''}
                </p>
                {recap_detail}
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
