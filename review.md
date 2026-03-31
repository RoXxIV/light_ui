# Code Review - Light UI (Revaw)

## Questions avant review finale

J'ai lu l'ensemble du code en profondeur. Avant de finaliser ma review, j'ai besoin de tes reponses sur les points suivants :

---

### 1. Credentials en clair dans `email_config.json`

Le fichier `src/ui/email/email_config.json` contient le mot de passe Gmail en clair (`uogdrmutfwugfhgk`). Ce fichier est-il commite dans le repo Git ? Est-ce un mot de passe d'application Google (App Password) ? Prevois-tu de le deplacer dans des variables d'environnement ou un `.env` ?

- risque acceptable pour le moment, le programme tourne sur un device inaccessible.

---

### 2. Incohernece modele 8.6 kWh

Dans `printer_config.py`, le modele `"8.6"` a `"ah": "175"` et `energy: 8.4` (pas 8.6).
Mais dans `scan_manager.py` (`_is_finish_combination_valid`), les types D/E sont autorises avec `'8.4'` (pas `'8.6'`).
L'utilisateur tape `finish 8.6` mais la validation cherche `'8.4'` dans les combinaisons valides.

**Est-ce que la validation du finish pour les types D/E fonctionne actuellement ?** Ca semble etre un bug ou la validation `_is_finish_combination_valid` ne matchera jamais car la cle est `"8.6"` mais `valid_combinations` contient `'8.4'`.

- a corrigé c'est bien 8.4

---

### 3. Incoherence "175" vs "179" dans le reprint

Dans `printer.py` (`_handle_full_reprint`), la detection du modele cherche `"179"` dans le serial, alors que `PrinterConfig` definit `"ah": "175"`. Le serial genere contient `175` (ex: `RW-48v1750001`), donc `"179" in full_serial` ne matchera jamais.

- a corrigé c'est bien 175

**Est-ce un bug connu ou un changement de spec non propage ?**

---

### 4. `csv_serial_manager.py` - code mort ?

Le fichier `csv_serial_manager.py` semble etre l'ancien systeme remplace par `sqlite_manager.py`. Est-il encore utilise quelque part ou peut-il etre supprime ? Le script de migration `migrate_csv_to_sqlite.py` a-t-il deja ete execute ?

ignore le pour l'instant, sqlite n'a jamais été tester en prod , je travail dessus

---

### 5. Sync queue MongoDB - worker absent

La table `sync_queue` et les appels `SQLiteManager.enqueue(...)` sont presents partout, mais je ne vois aucun worker/service qui consomme cette queue pour synchroniser avec MongoDB.

- pas encore dev , c'est la suite logique apres la review

**Le worker MongoDB est-il dans un autre repo/service, ou est-ce un travail en cours non encore implemente ?**

---

### 6. Architecture MQTT : UI et Printer sur la meme machine ?

L'UI (`ui.py`) et le service d'impression (`printer.py`) communiquent via MQTT en localhost. Le broker MQTT est-il Mosquitto local ? Les deux processus tournent-ils sur la meme machine (ex: un Raspberry Pi ou un PC d'atelier) ?

oui les deux tourne sur un pi mais je vais passer sur pc avec cette version

---

### 7. Etiquettes ZPL : poids/dimensions en dur

Dans `label_templates.py`, les valeurs `115 kg`, `608*460*248mm` et `610*460*250mm` sont codees en dur, identiques pour tous les modeles (A a E). Les batteries D/E (9.6 kWh) ont-elles vraiment les memes dimensions et le meme poids que les A (28.8 kWh) ?

- je vais verifier

---

### 8. `_handle_await_expedition_confirm` est vide

La methode `_handle_await_expedition_confirm` dans `scan_manager.py` (ligne 371) est un `pass`. L'etat `STATE_AWAIT_EXPEDITION_CONFIRM` est atteignable mais son handler ne fait rien. Est-ce voulu ? (la finalisation se fait via `_handle_expedition_finalize` appele directement)

il faut scan expédition puis scanner les serial des batterie puis re scan expedition pour valider donc ou c'est voulu

---

### 9. Robustesse de la file d'impression

La `print_queue` (deque) est en memoire. Si le service `printer.py` crash ou est redemarre, la file est perdue. Est-ce acceptable dans ton contexte de production, ou prevois-tu une persistance (SQLite, fichier) ?

acceptable pour l'instant

---

### 10. Notifications de resultat non consommees

Le service `printer.py` publie des resultats sur `printer/operation/result` (via `_publish_operation_result`), mais l'UI (`ui.py`) ne s'abonne pas a ce topic. Les resultats d'operations (succes/echec create, expedition, SAV) ne remontent donc pas a l'interface.

**Est-ce prevu de s'y abonner cote UI pour afficher des confirmations/erreurs en temps reel ?**

non pas pour l'instant

---

### 11. Envoi email dans le thread UI

La methode `_send_expedition_email` lance bien un thread daemon, c'est correct. Mais si l'UI est fermee pendant l'envoi, le thread daemon est tue immediatement. L'email peut ne pas partir. Est-ce un cas de figure qui t'inquiete ?

c'est ok

---

### 12. Score dans la table batteries

La colonne `score` (REAL) existe dans la table `batteries` mais n'est jamais ecrite ni lue par le code actuel. Est-ce un champ reserve pour une fonctionnalite future ?

oui fonctionnalité future

---

### 13. Variable `model_changed` jamais `True`

Dans `printer.py` (`_handle_validate_battery`, ligne 794), `model_changed = False` est defini mais jamais mis a `True`. Le log conditionnel sur cette variable est donc du code mort. Est-ce un reste d'une feature retiree ?

on verra ca en detail plus tard

---

---
---

# Review finale

## Vue d'ensemble

L'application Revaw est une interface de production pour la gestion du cycle de vie de batteries LiFePO4 : creation, test/finalisation, expedition et SAV. L'architecture repose sur deux processus (UI + service d'impression) communiquant via MQTT, avec SQLite comme source de verite locale.

Le code est globalement bien structure, lisible, et la separation des responsabilites (ScanManager, InfoPanel, SQLiteManager, PrinterConfig) est propre. La machine a etats du ScanManager est claire et maintenable.

---

## Bugs a corriger

### BUG 1 - `_is_finish_combination_valid` : cle `"8.6"` vs `"8.4"` (CRITIQUE)

**Fichier** : `src/ui/scan_manager.py`, ligne 224

Le dictionnaire `valid_combinations` pour les types D/E contient `'8.4'`, mais la cle utilisateur (et celle de `BATTERY_MODELS`) est `"8.6"`. Le `model_key` passe a cette methode vaut `"8.6"`, donc `"8.6" not in ['8.4']` → la validation echoue systematiquement pour D/E.

**Correction** : remplacer `'8.4'` par `'8.6'` dans `valid_combinations` :
```python
valid_combinations = {
    'A': ['13', '12'],
    'B': ['13', '12'],
    'C': ['13', '12'],
    'D': ['8.6'],   # etait '8.4'
    'E': ['8.6']    # etait '8.4'
}
```

### BUG 2 - Reprint : `"179"` au lieu de `"175"` (CRITIQUE)

**Fichier** : `printer.py`, ligne 893

```python
elif "179" in full_serial:  # BUG: devrait etre "175"
    kwh = 8.6
    ah = 179   # BUG: devrait etre 175
```

Le serial genere est `RW-48v175XXXX`, donc cette branche n'est jamais atteinte. Les reprints de batteries 8.6 kWh n'imprimeront que l'etiquette V1, sans Main ni Shipping.

**Correction** :
```python
elif "175" in full_serial:
    kwh = 8.4
    ah = 175
```

> Note : `kwh` devrait etre `8.4` pour etre coherent avec `PrinterConfig.BATTERY_MODELS["8.6"]["energy"]` qui vaut `8.4`. A clarifier si l'energy reelle est 8.4 ou 8.6 — voir point de nommage ci-dessous.

### BUG 3 - Confusion naming `energy: 8.4` sous la cle `"8.6"`

**Fichier** : `src/labels/printer_config.py`, ligne 23-26

```python
"8.6": {
    "energy": 8.4,  # la cle dit 8.6, la valeur dit 8.4
    "ah": "175"
}
```

Ce n'est pas un bug fonctionnel en soi (le code utilise la cle `"8.6"` pour le routing et `energy` pour l'affichage), mais c'est une source de confusion qui a deja cause les bugs 1 et 2.

**Recommandation** : choisir une seule valeur. Si la capacite reelle est 8.4 kWh, renommer la cle en `"8.4"` partout (UI, modals, commandes). Si c'est un arrondissement commercial a 8.6, alors mettre `energy: 8.6`.

---

## Problemes de qualite

### QUA 1 - Double declaration de constantes dans `system_utils.py`

**Fichier** : `src/ui/system_utils.py`

Les variables `PROJECT_ROOT`, `LOGS_DIR`, `LOG_FILE`, `LOG_LEVELS`, `CURRENT_LOG_LEVEL` sont declarees deux fois (lignes 14-18, puis lignes 33-37). Le deuxieme bloc ecrase le premier. Pas de bug fonctionnel, mais c'est du code mort qui cree de la confusion.

**Correction** : supprimer le bloc duplique (lignes 28-37).

### QUA 2 - Import `logging` duplique dans `system_utils.py`

Lignes 5-6 puis lignes 28-29 : `import logging` et `import logging.handlers` sont importes deux fois.

### QUA 3 - Handler `_handle_await_expedition_confirm` vide

**Fichier** : `src/ui/scan_manager.py`, ligne 371

La methode est un `pass` mais est referencee dans le dispatch `handlers`. Compris que c'est voulu (la finalisation se fait via `_handle_expedition_finalize` directement), mais cela signifie que si un utilisateur scan autre chose que `"expedition"` dans l'etat `STATE_AWAIT_EXPEDITION_CONFIRM`, le texte est silencieusement ignore sans feedback.

**Suggestion** : ajouter un message d'erreur plutot que `pass` :
```python
def _handle_await_expedition_confirm(self, text):
    self._update_ui("Scannez 'expedition' pour confirmer", "")
```

### QUA 4 - Variable morte `model_changed`

**Fichier** : `printer.py`, ligne 794

`model_changed = False` n'est jamais mis a `True`. Le `if model_changed:` est du code mort. A nettoyer quand tu y passeras.

### QUA 5 - Commentaires CSV obsoletes

Plusieurs commentaires dans `printer.py` font encore reference au CSV :
- Ligne 412 : `"EXPEDITION : Mettre a jour timestamp expedition dans CSV"`
- Ligne 686 : `"CREATE INITIAL : Cree une ligne CSV"`
- Ligne 935 : `"C'est le service d'impression qui fera la recherche intelligente dans le CSV"`

**Correction** : remplacer "CSV" par "SQLite" dans ces commentaires.

---

## Ameliorations suggerees (non bloquantes)

### SUG 1 - Centraliser la detection de modele par serial

Dans `printer.py` (`_handle_full_reprint`), la detection kWh/Ah se fait via des `if "271" in serial` en dur. Ce mapping existe deja dans `PrinterConfig.BATTERY_MODELS`. Utiliser une boucle sur `BATTERY_MODELS` eviterait les desynchronisations (c'est exactement ce qui a cause le bug 2).

```python
# Au lieu de if/elif en dur :
for model_key, model_info in PrinterConfig.BATTERY_MODELS.items():
    if model_info["ah"] in full_serial:
        kwh = model_info["energy"]
        ah = int(model_info["ah"])
        break
```

### SUG 2 - Poids et dimensions par modele dans les etiquettes

Les valeurs `115 kg`, `608*460*248mm` sont codees en dur dans `label_templates.py` et identiques pour tous les modeles. Si les batteries D/E ont des specs differentes, ces valeurs devraient etre dans `PrinterConfig` par modele.

### SUG 3 - S'abonner a `printer/operation/result` dans l'UI

Les resultats (succes/erreur) des operations create, validate, expedition, SAV sont publies par `printer.py` mais jamais consommes. S'y abonner dans l'UI permettrait d'afficher des confirmations fiables (actuellement, l'UI affiche "envoyee" des le publish MQTT, sans savoir si l'operation a reellement reussi cote printer).

### SUG 4 - `battery_exists` fait deux requetes

`battery_exists()` appelle `get_battery()` qui fait un `SELECT *` complet, juste pour verifier l'existence. Une requete `SELECT 1 ... LIMIT 1` serait plus legere, surtout dans la boucle d'expedition ou c'est appele pour chaque serial.

### SUG 5 - Timeout SMTP

Dans `_send_expedition_email`, la connexion SMTP n'a pas de timeout explicite. Si le serveur SMTP est injoignable, le thread peut rester bloque indefiniment. Ajouter un `timeout` au `SMTP_SSL` :
```python
server = smtplib.SMTP_SSL(email_config.smtp_server, email_config.smtp_port, timeout=15)
```

---

## Resume

| Categorie | Nombre | Priorite |
|-----------|--------|----------|
| Bugs critiques | 2 (finish D/E + reprint 175) | A corriger maintenant |
| Confusion naming | 1 (8.4 vs 8.6) | A clarifier |
| Qualite / code mort | 5 | Nettoyage quand possible |
| Suggestions | 5 | A planifier |

Les deux bugs critiques (BUG 1 et BUG 2) bloquent des workflows de production pour les batteries de type D/E. Je recommande de les corriger en priorite avant de passer au worker MongoDB.
