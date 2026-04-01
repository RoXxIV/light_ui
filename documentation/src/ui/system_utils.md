# src/ui/system_utils.py — Utilitaires système et logging

## Rôle

Fournit la configuration du logger centralisé et des utilitaires système (détection de processus).

---

## Fonctions

### `setup_logging()`

Configure le logger de l'application avec :

| Paramètre | Valeur |
|---|---|
| Fichier de log | `logs/banc_test.log` |
| Rotation | 10 MB par fichier, 5 fichiers de backup |
| Format | `[timestamp] [LEVEL] message` |

Doit être appelé une seule fois au démarrage de l'application.

---

### `log(level, message)`

Fonction de logging multi-niveaux avec filtrage.

**Niveaux supportés (du plus verbeux au plus critique) :**

| Niveau | Description |
|---|---|
| `DEEP_DEBUG` | Traces très détaillées (désactivé en production) |
| `DEBUG` | Informations de débogage |
| `INFO` | Événements normaux |
| `WARNING` | Avertissements non bloquants |
| `ERROR` | Erreurs |

---

### `is_printer_service_running()`

Vérifie si le processus `printer.py` est en cours d'exécution.

- Utilise `psutil` pour parcourir les processus système
- Retourne `True` si un processus Python exécutant `printer.py` est trouvé
- Utilisé par `ui.py` au démarrage pour avertir si le service d'impression est absent

---

## Dépendances

| Module | Usage |
|---|---|
| `logging` | Configuration et écriture des logs |
| `logging.handlers.RotatingFileHandler` | Rotation automatique des fichiers |
| `psutil` | Inspection des processus système |
| `datetime` | Horodatages dans les logs |
