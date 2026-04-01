# src/labels/csv_serial_manager.py — Gestion CSV des numéros de série (legacy)

## Rôle

Gestionnaire legacy des numéros de série et du suivi SAV via fichiers CSV. Ce module est en cours de remplacement par `SQLiteManager` dans le cadre de la migration vers SQLite (branche `sqlite`).

---

## Classe `CSVSerialManager`

Classe statique — toutes les méthodes sont des `@staticmethod`.

---

## Fichiers CSV gérés

| Fichier | Description |
|---|---|
| `printed_serials.csv` | Historique des numéros de série imprimés |
| `sav_batteries.csv` | Entrées / sorties SAV |

---

## Méthodes

### Initialisation

| Méthode | Description |
|---|---|
| `initialize_serial_csv()` | Crée `printed_serials.csv` avec les en-têtes si inexistant |
| `initialize_sav_csv()` | Crée `sav_batteries.csv` avec les en-têtes si inexistant |

---

### Gestion des numéros de série

| Méthode | Description |
|---|---|
| `get_last_serial_from_csv()` | Lit le dernier numéro de série depuis le CSV |
| `generate_random_code()` | Génère un code alphanumérique de 6 caractères |
| `validate_and_update_serial(temp_serial, capacity)` | Convertit un numéro temporaire en numéro définitif |

#### Format des numéros de série

- **Temporaire** : lettre + 4 chiffres (ex: `A0042`) — généré lors du CREATE
- **Définitif** : `RW-48v{Ah}{numéro}` (ex: `RW-48v2710042`) — généré lors du FINISH

---

### SAV (Service Après-Vente)

| Méthode | Description |
|---|---|
| `is_battery_in_sav(serial)` | Vérifie si une batterie est en garantie active |
| `add_sav_entry(serial)` | Enregistre une entrée SAV avec horodatage d'arrivée |
| `update_sav_departure(serial)` | Enregistre la date de sortie SAV |

---

## Statut de migration

> **Ce module est legacy.** Il est conservé pour compatibilité avec les données existantes et le script de migration `scripts/migrate_csv_to_sqlite.py`.
>
> En production active, `SQLiteManager` (`src/db/sqlite_manager.py`) est utilisé à la place.

---

## Dépendances

| Module | Usage |
|---|---|
| `csv` | Lecture/écriture des fichiers CSV |
| `re` | Validation du format des numéros de série |
| `datetime` | Horodatages |
| `src.ui.system_utils` | Logging |
| `src.labels.printer_config` | `PrinterConfig.BATTERY_MODELS` |
