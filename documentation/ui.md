# ui.py — Application principale

## Rôle

Point d'entrée de l'application. Lance l'interface graphique CustomTkinter, orchestre le `ScanManager` et l'`InfoPanel`, et gère la connexion MQTT pour surveiller l'état du service d'impression.

---

## Classe `SimpleApp`

Hérite de `ctk.CTk`. Représente la fenêtre principale de l'application.

### Initialisation

| Méthode | Description |
|---|---|
| `__init__()` | Initialise la fenêtre (plein écran, thème sombre), crée les managers, démarre MQTT |
| `_setup_ui()` | Crée les widgets CTk : frames, textbox de log, champ de saisie, labels de statut |
| `_setup_mqtt()` | Lance le thread de connexion MQTT |

### MQTT

| Méthode | Description |
|---|---|
| `_mqtt_thread()` | Boucle de connexion MQTT avec reconnexion automatique |
| `_on_connect()` | Souscrit aux topics `printer/status` et `printer/result` |
| `_on_message()` | Met à jour le label de statut imprimante selon le message reçu |
| `_on_disconnect()` | Log de la déconnexion |

### Interface

| Méthode | Description |
|---|---|
| `handle_prompt()` | Traite la saisie utilisateur depuis le champ d'entrée, la transmet au `ScanManager` |
| `add_message(msg, color)` | Ajoute un message coloré dans le textbox de log |
| `update_status(type, value)` | Met à jour le label MQTT ou imprimante |
| `update_response_labels(main, sub)` | Met à jour les textes de retour du scan |
| `_start_info_updates()` | Démarre le rafraîchissement automatique de l'`InfoPanel` |
| `_safe_manual_refresh()` | Rafraîchissement manuel thread-safe |
| `destroy()` | Nettoyage propre à la fermeture (arrêt threads, MQTT) |

### Point d'entrée

```python
def main():
    app = SimpleApp()
    app.mainloop()
```

---

## Interface graphique

- Mode plein écran activé par défaut (toggle F11)
- Thème sombre CustomTkinter
- Zone de log avec messages colorés (INFO, WARNING, ERROR)
- Champ de saisie unique pour les commandes et les scans
- Labels de statut : connexion MQTT + état imprimante

---

## Dépendances

| Module | Usage |
|---|---|
| `customtkinter` | Framework GUI |
| `paho.mqtt.client` | Communication MQTT |
| `threading` | Threads MQTT et info panel |
| `src.ui.scan_manager` | Traitement des scans/commandes |
| `src.ui.info_panel` | Panel de statistiques |
| `src.db.sqlite_manager` | Accès base de données |
| `src.ui.system_utils` | Logging |

---

## Flux de démarrage

```
main()
  └── SimpleApp.__init__()
        ├── _setup_ui()          → widgets CTk
        ├── ScanManager(self)    → machine à états
        ├── InfoPanel(self)      → panel stats
        └── _setup_mqtt()        → thread MQTT
```
