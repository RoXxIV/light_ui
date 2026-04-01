# src/labels/printer_config.py — Configuration imprimante et MQTT

## Rôle

Classe de configuration centralisée (statique) pour tous les paramètres de l'imprimante Zebra et des topics MQTT.

---

## Classe `PrinterConfig`

### Modèles de batteries

```python
BATTERY_MODELS = {
    13:  271,   # 13 kWh → 271 Ah
    12:  250,   # 12 kWh → 250 Ah
    8.4: 175,   # 8.4 kWh → 175 Ah
}
```

### Topics MQTT

| Constante | Topic | Description |
|---|---|---|
| `TOPIC_CREATE` | `labels/create_label` | Création d'une nouvelle batterie |
| `TOPIC_VALIDATE` | `labels/validate_battery` | Finalisation / validation |
| `TOPIC_EXPEDITION` | `labels/update_shipping_timestamp` | Expédition |
| `TOPIC_SAV_ENTRY` | `labels/sav_entry` | Entrée SAV |
| `TOPIC_SAV_DEPARTURE` | `labels/sav_departure` | Sortie SAV |
| `TOPIC_CREATE_QR` | `labels/create_qr` | QR personnalisé |
| `TOPIC_REPRINT` | `labels/request_full_reprint` | Réimpression complète |

### Connexion imprimante

| Paramètre | Valeur |
|---|---|
| `PRINTER_IP` | `192.168.1.123` |
| `PRINTER_PORT` | `9100` |
| `PRINTER_TIMEOUT` | *(défini dans la classe)* |

### Statuts imprimante

| Constante | Description |
|---|---|
| `STATUS_OK` | Prête |
| `STATUS_MEDIA_OUT` | Plus de papier/étiquettes |
| `STATUS_HEAD_OPEN` | Tête d'impression ouverte |
| `STATUS_PAUSED` | En pause |
| `STATUS_ERROR` | Erreur générique |

### Autres

| Paramètre | Description |
|---|---|
| `SOFTWARE_VERSION` | Version logicielle : `1.1.5.1` |
| `ERROR_MASKS` | Masques binaires pour parser la réponse `~HQES` |

---

## Dépendances

Aucune — classe de configuration pure.
