# -*- coding: utf-8 -*-
"""
Module complet pour la gestion des étiquettes d'impression.

Ce module regroupe :
- Les templates ZPL pour les différents types d'étiquettes
- La configuration de l'imprimante et des services MQTT
"""

from .label_templates import LabelTemplates
from .printer_config import PrinterConfig

__all__ = ['LabelTemplates', 'PrinterConfig']
