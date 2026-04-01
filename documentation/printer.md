# printer.py — Service d'impression

## Rôle

Processus indépendant gérant l'impression des étiquettes Zebra. Reçoit les ordres via MQTT, maintient une file d'attente persistante, vérifie l'état de l'imprimante avant chaque impression, et persiste les données en SQLite.

---

## Classe `MinimalPrinter`

### Démarrage du service

| Méthode | Description |
|---|---|
| `start()` | Boucle principale : initialise MQTT + lance le thread worker |
| `_start_worker_thread()` | Démarre le thread de traitement de la file d'impression |
| `_printer_worker_thread()` | Boucle continue : dépile et traite les jobs d'impression |

---

## File d'attente

Les jobs sont stockés dans une `deque` thread-safe protégée par un `threading.Lock`.

Types de jobs :

| Type | Description |
|---|---|
| `V1_INITIAL` | Étiquette intérieure seule (lors du CREATE) |
| `ALL_THREE_FINAL` | 3 étiquettes complètes (lors du FINISH) |
| `FINAL_TWO` | Étiquette principale + expédition |

---

## Traitement des impressions

| Méthode | Description |
|---|---|
| `_process_print_item(item)` | Dispatche le job selon son type |
| `_print_all_three_labels(data)` | Imprime V1 + principale + expédition |
| `_print_v1_label(data)` | Étiquette intérieure batterie |
| `_print_main_label(data)` | Étiquette principale avec QR code |
| `_print_shipping_label(data)` | Étiquette de carton d'expédition |
| `_print_custom_qr(data)` | Étiquette QR personnalisée |
| `_send_zpl_to_printer(zpl)` | Envoi brut via socket TCP avec retry |

---

## Communication avec l'imprimante

Protocole : socket TCP sur `192.168.1.123:9100` (configurable via `PrinterConfig`).

| Méthode | Description |
|---|---|
| `_check_printer_status()` | Envoie la commande `~HQES` et lit la réponse |
| `_parse_hqes_response(response)` | Interprète les flags d'erreur/warning Zebra |

Statuts possibles : `OK`, `MEDIA_OUT`, `HEAD_OPEN`, `PAUSED`, `ERROR`

---

## Handlers MQTT

Souscrit à 7 topics au démarrage :

| Topic | Handler | Description |
|---|---|---|
| `labels/create_label` | `_handle_create()` | Nouveau CREATE |
| `labels/validate_battery` | `_handle_validate_battery()` | FINISH / validation |
| `labels/update_shipping_timestamp` | `_handle_expedition()` | Expédition |
| `labels/sav_entry` | `_handle_sav_entry()` | Entrée SAV |
| `labels/sav_departure` | `_handle_sav_departure()` | Sortie SAV |
| `labels/create_qr` | `_handle_create_qr()` | QR personnalisé |
| `labels/request_full_reprint` | `_handle_full_reprint()` | Réimpression complète |

---

## Publication MQTT

| Méthode | Description |
|---|---|
| `_publish_printer_status(status)` | Publie l'état imprimante sur `printer/status` |
| `_publish_operation_result(op, success, msg)` | Publie le résultat d'une opération sur `printer/result` |

---

## Dépendances

| Module | Usage |
|---|---|
| `socket` | Communication TCP avec l'imprimante |
| `paho.mqtt.client` | Réception des ordres |
| `threading` | Worker thread + lock file d'attente |
| `collections.deque` | File d'attente FIFO |
| `src.labels` | `LabelTemplates`, `PrinterConfig` |
| `src.db.sqlite_manager` | Persistence des opérations |
| `src.ui.system_utils` | Logging |

---

## Architecture du service

```
printer.py (processus séparé)
  └── MinimalPrinter
        ├── MQTT thread       ← reçoit les ordres
        ├── deque (queue)     ← file d'attente thread-safe
        └── Worker thread     ← traite la queue
              ├── check status imprimante (HQES)
              └── envoi ZPL via socket TCP
```
