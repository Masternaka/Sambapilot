# Contrôler une configuration candidate avec Samba

## Fonction disponible

Un aperçu peut être contrôlé avec le programme système `testparm` déjà installé sur Linux. Ce contrôle est facultatif et doit être demandé explicitement. Préparer un aperçu ne lance pas automatiquement Samba.

Le contrôle utilise le texte exact du candidat, y compris un éventuel BOM UTF-8. Il crée un dossier temporaire privé et une copie accessible uniquement au compte courant, puis supprime ces fichiers après l’exécution. Il n’enregistre jamais le candidat à la place du fichier source, ne modifie pas les comptes ou les droits et ne recharge aucun service.

## Dans le terminal

Depuis le dossier `sambapilot`, ajouter `--validate` à la préparation :

```sh
python3 -B -m sambapilot plan-partage --demo --action create --name Documents --path /srv/documents --user alex --validate
```

La même option est disponible sur un fichier choisi :

```sh
python3 -B -m sambapilot plan-partage --config /chemin/vers/smb.conf --action update --name Medias --path /srv/partages/medias --group famille --writable --validate --json
```

Sans `--validate`, le comportement précédent est conservé. Avec `--json`, le plan garde ses champs existants et reçoit un objet `validation`. Le champ `can_apply` reste faux, même si le candidat est accepté.

Codes de sortie :

- `0` : aperçu produit sans contrôle demandé, ou candidat accepté par le contrôle demandé.
- `2` : demande invalide ou impossible à préparer.
- `4` : contrôle demandé mais non accepté, indisponible, hors périmètre, en échec ou devenu caduc.

## Dans la fenêtre GTK

Après avoir généré un aperçu, cliquer sur **Contrôler avec Samba**. Le bouton est désactivé tant qu’aucun candidat n’est prêt. Le contrôle se déroule dans un fil séparé ; son résultat et les messages de Samba sont affichés séparément de la comparaison.

Modifier un champ, annuler, changer de source ou fermer la fenêtre invalide le résultat affichable. Un ancien contrôle qui se termine plus tard ne peut pas remplacer celui du candidat courant. Si le fichier source est devenu obsolète, le candidat est abandonné et doit être préparé à nouveau après rechargement.

## Périmètre volontairement limité

Le candidat doit rester dans le sous-ensemble actuellement pris en charge :

- Paramètres globaux : `workgroup`, `netbios name`, `server string`, `server role`, `security`, `server min protocol` et `server max protocol`.
- Si le rôle est déclaré, seule la valeur `standalone server` est acceptée ; si la sécurité est déclarée, seule la valeur `user` est acceptée.
- Paramètres de partage : `path`, `valid users`, `read only`, `browseable`, `guest ok` et `comment`.
- Identifiants simples et groupes UNIX avec le préfixe `+` dans la liste d’accès.

Les inclusions, les paramètres inconnus ou répétés, les substitutions, les sections spéciales et les configurations de domaine ou de registre sont refusés avant de lancer un programme. Les modules et les scripts configurables ne font pas partie de ce périmètre. Un refus de SambaPilot signifie « contrôle automatique hors périmètre », pas nécessairement « configuration Samba invalide ».

Un fichier peut donc être inspecté ou servir à un aperçu tout en étant refusé pour ce contrôle. Aucune option n’est retirée et aucun réglage n’est remplacé silencieusement pour forcer son acceptation.

## Exécution et résultat

Le programme est recherché uniquement dans `/usr/bin` et `/usr/sbin`, sans utiliser les shims du `PATH` utilisateur. L’appel utilise une liste fixe d’arguments, sans shell, sans `sudo`, sans saisie interactive et avec un délai maximal de cinq secondes. La configuration système par défaut n’est pas passée à la place du candidat.

La sortie standard de `testparm`, qui peut contenir un affichage complet de la configuration, est écartée. Les messages d’erreur sont limités à leur fin sur 8 Kio, nettoyés des caractères de contrôle et associés à l’empreinte du candidat. Le chemin du dossier temporaire est remplacé dans ces messages.

Pour un plan sur fichier choisi, la source est relue avant et après le contrôle. Un changement de contenu ou une lecture devenue impossible rend le résultat caduc, même si `testparm` a retourné zéro. Ce contrôle ne constitue pas une surveillance continue ni une future autorisation d’application.

Les états possibles dans le JSON sont `accepted`, `rejected`, `unavailable`, `unsupported`, `timeout`, `error` et `stale`. Seul `accepted` correspond à un retour nul du programme après les vérifications de source.

Si `testparm` est absent ou si la plateforme n’est pas Linux, le contrôle est indiqué indisponible. Aucun téléchargement, installation de dépendance ou redémarrage n’est tenté.

## Limites de validation

Selon la [documentation officielle de testparm](https://www.samba.org/samba/docs/current/man-html/testparm.1.html), le programme vérifie la cohérence interne d’une configuration ; un résultat positif ne garantit pas le fonctionnement des services déclarés. SambaPilot conserve donc les messages à examiner, même si le code de retour est nul.

Les permissions Linux, les ACL, les comptes, les accès depuis un autre appareil et les règles de pare-feu restent à vérifier séparément. Le contrôle ne rend jamais le plan applicable dans cette version.

Pendant le développement, les essais couvrent les retours du programme avec des doubles de test, les refus avant lancement, les délais, les erreurs, la protection et le nettoyage des fichiers temporaires ainsi que l’état du fichier source. Aucun vrai `testparm` n’a été exécuté, car il n’est pas installé dans l’environnement de développement. Les essais GTK natifs restent également à effectuer dans une session graphique autorisée.
