# Recommandations pour SambaPilot

Ces ajouts complètent le [cahier des charges](cahier-des-charges.md). Ils constituent une feuille de route ; ils ne sont pas tous disponibles dans l’application.

## Ordre proposé

| Priorité | Fonctionnalité | Objectif |
| --- | --- | --- |
| 1 | Vue « Qui peut accéder à quoi ? » | Croiser les utilisateurs, les groupes et les partages ; expliquer la lecture, l’écriture, les refus et les informations inconnues. |
| 2 | Assistant de dépannage | Guider les recherches quand un partage n’apparaît pas, refuse un accès ou empêche l’écriture. |
| 3 | Guide de connexion par appareil | Afficher l’adresse du partage et les étapes de connexion depuis Windows, macOS et Linux. |
| 4 | Profils de partage | Préparer un dossier personnel, familial, multimédia en lecture seule ou de travail ; présenter les droits avant application. |
| 5 | Protection des disques externes | Vérifier qu’un disque est bien monté avant d’activer son partage et signaler sa disparition. |
| 6 | Détection des modifications externes | Comparer les réglages courants à l’état précédent et signaler les changements manuels avant d’intervenir. |
| 7 | Connexions actives et fichiers ouverts | Afficher les sessions et avertir avant une opération qui pourrait interrompre des utilisateurs. |
| 8 | Corbeille par partage | Proposer la conservation des fichiers supprimés via Samba, leur restauration et un nettoyage confirmé. |
| 9 | Profil macOS et Time Machine | Préparer les réglages adaptés aux clients Apple et, en option, un partage dédié aux sauvegardes Time Machine. |

## Première étape : vue des accès

### Livré dans cette première version

- Un modèle de comptes, de groupes et de règles de partage, indépendant des interfaces.
- Un calcul séparé des droits déclarés Samba et des observations de permissions de fichiers.
- Une matrice utilisateur × partage en texte et en JSON.
- Des explications pour les conflits et les informations manquantes.
- Un jeu de démonstration sans lecture des comptes, des fichiers ou de la configuration de la machine.

La commande `python3 -B -m sambapilot permissions --demo` affiche cette démonstration depuis le dossier `sambapilot`.

### Règles d’interprétation

Le résultat est une **estimation à partir de données déclarées**, pas une preuve d’accès réel. Une information inconnue reste inconnue. Lecture et écriture sont évaluées séparément ; l’écriture seule doit pouvoir être représentée.

Le modèle couvre les comptes activés ou désactivés, les listes d’utilisateurs ou de groupes autorisés, la lecture seule et les exceptions d’écriture. Une exception d’écriture n’accorde pas à elle seule l’accès à un partage. Les listes d’accès vides représentent l’absence de restriction par liste pour un compte authentifié ; ce n’est pas un accès invité.

Les observations de fichiers représentent les capacités de lecture, d’écriture et de traversée pour une identité donnée. Elles ne sont pas déduites des seuls bits de permissions d’un dossier. Elles doivent rester inconnues si les ACL ou les autres contrôles nécessaires ne sont pas établis.

Un réglage Samba hors du modèle rend l’estimation inconnue. Le lecteur de configuration futur devra notamment reconnaître les options avancées, les inclusions, les ACL Windows, les substitutions d’identité et les listes de lecture avant de produire une estimation fiable.

### À développer ensuite

- Collecter les comptes, les groupes et la configuration effective sur Linux en lecture seule.
- Établir les permissions Linux, les ACL et la traversée des dossiers parents sans effectuer de test d’écriture implicite.
- Relier les observations aux règles effectives de Samba, y compris les options non prises en charge.
- Afficher la même matrice dans l’interface graphique.
- Ajouter des tests de connexion explicites depuis un appareil client.

Le réseau, le pare-feu, l’authentification réelle, les permissions de chaque fichier enfant et les effets d’une session déjà ouverte ne sont pas prouvés par la matrice.

## Fonctions complémentaires

Les profils de partage devront rester modifiables et ne jamais attribuer de droits sans aperçu. La protection des disques devra distinguer un répertoire existant d’un volume réellement monté. La détection des modifications externes devra bloquer une application fondée sur un état devenu obsolète.

Le suivi des connexions pourra s’appuyer sur les informations de [smbstatus](https://www.samba.org/samba/docs/current/man-html/smbstatus.1.html). La corbeille pourra utiliser [vfs_recycle](https://www.samba.org/samba/docs/4.22/man-html/vfs_recycle.8.html), avec une gestion de l’espace et des droits de restauration ; elle ne remplace pas une sauvegarde. Le profil Apple et Time Machine devra respecter les contraintes de [vfs_fruit](https://www.samba.org/samba/docs/current/man-html/vfs_fruit.8.html).

Les règles du modèle d’accès sont à rapprocher de la [documentation officielle de smb.conf](https://www.samba.org/samba/docs/current/man-html/smb.conf.5.html). Le modèle actuel ne remplace pas Samba pour interpréter une configuration réelle.

## Autorisation préalable

Ces recommandations n’autorisent aucune installation ni modification de l’ordinateur. Toute future opération sur les comptes, les fichiers, les services ou le pare-feu devra présenter les changements, obtenir une confirmation explicite et prévoir les sauvegardes adaptées.
