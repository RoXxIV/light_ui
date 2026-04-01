# src/ui/email/email_config.py — Configuration SMTP

## Rôle

Charge et valide la configuration SMTP depuis `email_config.json`. Fournit des valeurs par défaut sécurisées et expose une interface propre pour accéder aux paramètres.

---

## Fichier de configuration

`src/ui/email/email_config.json` — fichier JSON attendu :

```json
{
  "gmail_user": "expeditions@revaw.com",
  "gmail_password": "xxxx xxxx xxxx xxxx",
  "recipient_emails": ["contact@client.com"],
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 465
}
```

> Le mot de passe doit être un **App Password** Google (pas le mot de passe du compte).

---

## Classe `EmailConfig`

### Initialisation

| Méthode | Description |
|---|---|
| `__init__()` | Charge la configuration depuis le JSON |
| `_load_config()` | Parse le JSON avec gestion d'erreur — retourne un dict vide si absent ou invalide |
| `reload_config()` | Recharge depuis le fichier (utile si modifié à chaud) |

---

## Propriétés

| Propriété | Type | Défaut |
|---|---|---|
| `gmail_user` | str | `""` |
| `gmail_password` | str | `""` |
| `recipient_emails` | list[str] | `[]` |
| `smtp_server` | str | `"smtp.gmail.com"` |
| `smtp_port` | int | `465` |

---

## Validation

| Méthode | Description |
|---|---|
| `is_configured()` | Retourne `True` si tous les champs requis sont présents et non vides |
| `get_missing_config_items()` | Retourne la liste des clés manquantes |

---

## Dépendances

| Module | Usage |
|---|---|
| `json` | Lecture du fichier de configuration |
| `os` | Résolution du chemin du fichier JSON |
| `src.ui.system_utils` | Logging des erreurs de chargement |
