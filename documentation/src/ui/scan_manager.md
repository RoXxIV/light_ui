# src/ui/scan_manager.py — Machine à états des scans

## Rôle

Cœur logique de l'application. Traite toutes les entrées utilisateur (scan de code-barres ou saisie clavier) via une machine à états. Publie les ordres sur MQTT selon le workflow en cours.

---

## Classe `ScanManager`

### États (states)

```
STATE_IDLE
STATE_AWAIT_FINISH_SERIAL
STATE_AWAIT_FINISH_CONFIRM
STATE_AWAIT_EXPEDITION_SERIAL
STATE_AWAIT_EXPEDITION_CONFIRM
STATE_AWAIT_SAV_SERIAL
STATE_AWAIT_SAV_CONFIRM
STATE_AWAIT_QR_TEXT
STATE_AWAIT_QR_CONTENT
STATE_AWAIT_QR_CONFIRM
STATE_AWAIT_REPRINT_SERIAL
STATE_AWAIT_REPRINT_CONFIRM
```

L'état initial est toujours `STATE_IDLE`.

---

## Point d'entrée

### `process_scan(input_text)`

Méthode principale appelée à chaque saisie. Selon l'état courant, dispatche vers le handler approprié.

**Flux général :**
```
process_scan(input)
  └── _handle_global_commands()   ← commandes valables depuis IDLE
        ou
  └── handler de l'état courant   ← ex: _handle_await_finish_serial()
```

---

## Workflows

### CREATE

```
IDLE → commande CREATE (type matière) → MQTT labels/create_label → IDLE
```

### FINISH

```
IDLE
  → commande FINISH (capacité sélectionnée) → STATE_AWAIT_FINISH_SERIAL
  → scan QR temporaire                       → STATE_AWAIT_FINISH_CONFIRM
  → scan QR de confirmation                  → MQTT labels/validate_battery → IDLE
```

### EXPEDITION

```
IDLE
  → commande EXPEDITION                      → STATE_AWAIT_EXPEDITION_SERIAL
  → scans multiples de numéros de série      → accumulation dans liste
  → commande FINALIZE                        → MQTT labels/update_shipping_timestamp → IDLE
  → commande CANCEL                          → IDLE (liste vidée)
```

### SAV

```
IDLE
  → commande SAV                             → STATE_AWAIT_SAV_SERIAL
  → scan numéro de série                     → STATE_AWAIT_SAV_CONFIRM
  → confirmation                             → MQTT labels/sav_entry ou sav_departure → IDLE
```

### QR personnalisé

```
IDLE
  → commande NEW_QR                          → STATE_AWAIT_QR_TEXT
  → saisie texte affiché                     → STATE_AWAIT_QR_CONTENT
  → saisie contenu QR                        → STATE_AWAIT_QR_CONFIRM
  → confirmation                             → MQTT labels/create_qr → IDLE
```

### REPRINT

```
IDLE
  → commande REPRINT                         → STATE_AWAIT_REPRINT_SERIAL
  → scan numéro de série                     → STATE_AWAIT_REPRINT_CONFIRM
  → confirmation                             → MQTT labels/request_full_reprint → IDLE
```

---

## Méthodes clés

| Méthode | Description |
|---|---|
| `_handle_global_commands(input)` | Reconnait les commandes globales depuis IDLE |
| `_is_finish_combination_valid(material, capacity)` | Vérifie la compatibilité matière/capacité |
| `_extract_serial(input)` | Valide le format `RW-48vXXX0001` via regex |
| `_check_and_handle_sav_return(serial)` | Détecte automatiquement un retour SAV |
| `_change_state(new_state)` | Transition d'état avec log |
| `_update_ui(main_msg, sub_msg)` | Met à jour les labels de retour dans `ui.py` |
| `_start_timeout()` | Démarre un timer de 30s — reset auto vers IDLE si inactif |
| `_reset_scan()` | Retour à IDLE + reset UI |

---

## Validation des numéros de série

Format regex attendu :

```
RW-48v(271|250|175)\d{4}
```

Exemples valides :
- `RW-48v2710042` — 13 kWh, numéro 0042
- `RW-48v2500100` — 12 kWh, numéro 0100
- `RW-48v1750001` — 8.4 kWh, numéro 0001

---

## Timeout

Si aucune saisie n'est reçue pendant **30 secondes** en dehors de `STATE_IDLE`, le système reset automatiquement vers IDLE.

---

## Dépendances

| Module | Usage |
|---|---|
| `re` | Validation regex des numéros de série |
| `json` | Sérialisation des payloads MQTT |
| `threading` | Timer de timeout |
| `paho.mqtt.client` | Publication des ordres |
| `src.labels.printer_config` | Topics MQTT, modèles de batteries |
| `src.ui.system_utils` | Logging |
