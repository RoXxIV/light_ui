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

        # Génération du contenu texte
        contenu_texte = EmailTemplates._generate_expedition_text_content(
            serial_numbers, date_formatee)

        # Génération du contenu HTML
        contenu_html = EmailTemplates._generate_expedition_html_content(
            serial_numbers, date_formatee)

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
    def _generate_expedition_text_content(serial_numbers: List[str],
                                          date_formatee: str) -> str:
        """
        Génère le contenu texte de l'email d'expédition.
        
        Args:
            serial_numbers (List[str]): Liste des numéros de série
            date_formatee (str): Date formatée pour l'affichage
            
        Returns:
            str: Le contenu texte complet de l'email
        """
        total_batteries = len(serial_numbers)

        # Corps principal avec total
        corps_principal = f"Bonjour,\n\nVoici la liste des batteries marquées comme expédiées le {date_formatee}:\n\n"

        # Liste des batteries (numérotée)
        for i, serial in enumerate(serial_numbers, 1):
            corps_principal += f"{i:2d}. {serial}\n"

        # Ligne de total
        corps_principal += f"\n📦 TOTAL EXPÉDIÉ: {total_batteries} batterie{'s' if total_batteries > 1 else ''}\n"

        # Formule de politesse
        formule_politesse = f"\nCordialement,\n{EmailTemplates.SENDER_NAME}\n"

        # Zone de signature manuelle (inchangée)
        zone_signature = """
    Nom : _________________________

    Signature :


    _________________________________________
    """

        # Signature de l'entreprise (inchangée)
        signature_entreprise = f"""
    -- 
    {EmailTemplates.COMPANY_NAME}
    """

        return corps_principal + formule_politesse + zone_signature + signature_entreprise

    @staticmethod
    def _generate_expedition_html_content(serial_numbers: List[str],
                                          date_formatee: str) -> str:
        """
        Génère le contenu HTML de l'email d'expédition.
        
        Args:
            serial_numbers (List[str]): Liste des numéros de série
            date_formatee (str): Date formatée pour l'affichage
            
        Returns:
            str: Le contenu HTML complet de l'email
        """
        total_batteries = len(serial_numbers)

        # En-tête et introduction avec total
        html_intro = f"""
            <html>
            <body>
                <p>Bonjour,</p>
                <p>Voici la liste des <strong>{total_batteries} batterie{'s' if total_batteries > 1 else ''}</strong> marquée{'s' if total_batteries > 1 else ''} comme expédiée{'s' if total_batteries > 1 else ''} le <strong>{date_formatee}</strong>:</p>
                <ul>
            """

        # Liste des batteries (numérotée automatiquement par <ul>)
        html_liste = ""
        for serial in serial_numbers:
            html_liste += f"<li><strong>{serial}</strong></li>"

        # Fermeture de la liste avec récapitulatif
        html_corps = f"""
                </ul>
                
                <div style="margin-top: 20px; padding: 15px; background-color: #f0f8ff; border-left: 4px solid #4CAF50;">
                    <p style="margin: 0; font-weight: bold; font-size: 16px;">
                        📦 TOTAL EXPÉDIÉ: {total_batteries} batterie{'s' if total_batteries > 1 else ''}
                    </p>
                </div>
                
                <p>Cordialement,</p>
                <p>{EmailTemplates.SENDER_NAME}</p>
            """

        # Zone de signature manuelle (inchangée)
        html_signature_zone = """
            <div style="margin-top: 40px; font-family: Arial, sans-serif; font-size: 14px;">
                <p><strong>Nom :</strong></p>
                <p style="margin-top: 20px;"><strong>Signature :</strong></p>
                <div style="border: 1px solid #000; height: 80px; width: 280px; margin-bottom: 5px;"></div>
            </div>
            """

        # Signature de l'entreprise (inchangée)
        html_signature_entreprise = f"""
            <hr>
            <p style="color: #666666; font-family: Arial, sans-serif; font-size: 12px;">
            <strong>{EmailTemplates.COMPANY_NAME}</strong><br>
            </p>
            """

        # Fermeture HTML (inchangée)
        html_fermeture = """
            </body>
            </html>
            """

        return (html_intro + html_liste + html_corps + html_signature_zone +
                html_signature_entreprise + html_fermeture)
