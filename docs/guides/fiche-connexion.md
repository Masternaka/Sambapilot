# Se connecter à un partage depuis un autre appareil

## Fonction disponible

SambaPilot prépare une fiche avec l’adresse Windows, l’adresse SMB pour macOS/Linux et les étapes à suivre sur le client. La fiche repose sur un partage fictif ou une déclaration d’un fichier choisi, avec sa source, son empreinte et sa date de lecture lorsqu’elle existe.

Vous indiquez explicitement le nom DNS ou l’IPv4 du serveur. SambaPilot ne peut pas déduire cette adresse du chemin local tel que `/srv/partages/famille`. Il ne contacte aucun serveur, ne résout aucun nom, ne teste aucun compte, ne monte aucun dossier et n’ouvre aucun gestionnaire de fichiers.

Un partage déclaré masqué peut disposer d’une adresse directe ; cela ne prouve pas un accès autorisé. Les réglages de lecture seule sont présentés comme déclarés ; les permissions effectives, le réseau et l’authentification restent inconnus.

## Démonstration depuis n’importe quel ordinateur

Python doit déjà être disponible. Depuis la racine du dépôt :

```sh
python3 -B -m sambapilot fiche-connexion --demo --share Famille --server serveur.example.invalid
python3 -B -m sambapilot fiche-connexion --demo --share Medias --server 192.0.2.10 --json
```

Ces adresses sont des exemples. Aucune connexion n’est tentée. La génération fonctionne sans Linux, GTK ni Samba.

Pour une configuration choisie explicitement :

```sh
python3 -B -m sambapilot fiche-connexion --config /chemin/vers/smb.conf --share Documents --server serveur.local
```

`--demo` ou `--config` est obligatoire, au choix. Le partage doit figurer une seule fois dans l’inventaire analysé sans blocage. Le choix est insensible à la casse et l’adresse reprend le nom déclaré. Le fichier choisi est lu selon les limites habituelles de l’examen ; il n’est jamais modifié. Le code `0` signifie que la fiche est produite, sans certifier l’accès ; `2` indique des arguments ou une source refusés.

La sortie JSON utilise son propre schéma 1. `network_verified` vaut `null` : absence de vérification, distincte d’un accès refusé. `can_apply` reste faux. Aucun mot de passe ni nom de compte n’est accepté dans l’adresse du serveur.

## Fenêtre GTK

Dans **Partages**, choisir **Préparer les adresses…** sur un exemple ou un partage du fichier courant. Saisir uniquement le serveur, puis sélectionner **Préparer les adresses**. Les deux boutons copient respectivement l’adresse Windows et l’adresse SMB ; ils ne lancent pas une connexion. La copie utilise le presse-papiers de la session graphique uniquement après un clic explicite.

Changer le serveur efface la fiche et désactive la copie jusqu’à une nouvelle préparation. Choisir, recharger ou effacer une source, revenir aux exemples ou fermer la fenêtre principale ferme la fiche. Elle ne surveille pas les modifications externes du fichier : la date affichée reste celle de la lecture source. Pour actualiser les déclarations, recharger le fichier puis ouvrir une nouvelle fiche.

Les adresses contiennent le serveur et le partage ; la fiche contient aussi le chemin source lorsqu’un fichier est choisi. Aucun export de fichier n’est effectué par cette fonction. Un texte déjà copié dans le presse-papiers n’est pas effacé automatiquement lorsque la fiche change.

## Depuis les clients

| Client | Adresse pour l’exemple Famille | Parcours |
| --- | --- | --- |
| Windows | `\\serveur.local\Famille` | Ouvrir l’Explorateur et saisir l’adresse dans sa barre d’adresse. |
| macOS | `smb://serveur.local/Famille` | Finder → Aller → Se connecter au serveur. |
| Linux avec gestionnaire compatible SMB | `smb://serveur.local/Famille` | Barre d’emplacement du gestionnaire ; GNOME Fichiers propose aussi Autres emplacements → Connexion à un serveur. |

Si le serveur demande une authentification, utiliser un compte autorisé. SambaPilot n’enregistre pas ces identifiants. La prise en charge SMB du gestionnaire client doit déjà être disponible ; aucune dépendance n’est installée automatiquement.

Les espaces et lettres accentuées du partage sont encodés dans l’URI SMB, sans modifier le nom déclaré. La première version accepte les noms de partage simples pris en charge par le moteur. Elle refuse les noms non portables ou terminés par un point, les URL comme valeur du serveur, les chemins, les ports personnalisés, les identifiants intégrés, les noms DNS non ASCII et IPv6. Ces limites évitent de présenter une adresse approximative comme prête à utiliser.

Références : [Microsoft — accès et lecteurs réseau](https://support.microsoft.com/en-us/windows/experience/connectivity-networking/file-sharing-over-a-network-in-windows), [Apple — connexion aux ordinateurs et serveurs partagés](https://support.apple.com/en-sg/guide/mac-help/mchlp1140/27/mac/27), [GNOME — parcourir les fichiers d’un serveur](https://help.gnome.org/gnome-help/nautilus-connect.html), [PyGObject — presse-papiers GTK4](https://pygobject.gnome.org/tutorials/gtk4/clipboard.html). Les consignes sont adaptées en français ; elles ne prouvent pas une connexion réelle depuis ces clients.

## Vérifications et limites

Les tests ordinaires vérifient les adresses, les refus, l’encodage, la préservation de la source et l’absence d’accès réseau. Les tests GTK préparent la génération, l’invalidation et la copie avec un presse-papiers simulé ; ils restent à exécuter en CI. Le contrôle du paquet installé prépare aussi cette fiche fictive. Aucun essai de connexion réel, aucun rendu graphique ni presse-papiers réel n’a été validé localement.
