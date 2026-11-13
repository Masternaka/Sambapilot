# Cahier des charges de SambaPilot

## Objectif

Centraliser la gestion des partages Samba sur Arch Linux, Debian et Fedora, depuis la préparation initiale jusqu’à la maintenance quotidienne, avec des adaptateurs propres à chaque distribution.

Ce document décrit la cible fonctionnelle, y compris les interventions système encore à développer. Pour le périmètre utilisable aujourd’hui, consulter le [README](../../README.md) et les [guides](../README.md).

Le diagnostic, la matrice des accès fictifs, l’examen d’un fichier choisi, les aperçus de partage, le contrôle facultatif avec `testparm`, les plans descriptifs d’installation et les intentions de pare-feu sont codés. Aucune application de changement système n’est implémentée. Les essais réels Linux, Samba et GTK restent à effectuer.

## Deux interfaces

L’interface graphique permettra de consulter les partages et d’effectuer les opérations courantes avec des formulaires et des aperçus des changements.

L’interface terminal donne accès au même moteur. Les huit commandes actuelles, dont le diagnostic et le dépannage en lecture seule, sont documentées dans le [README](../../README.md) ; les futures commandes d’application restent à définir. Les opérations modifiant la machine devront toujours demander une confirmation explicite ; aucun changement ne sera déclenché au démarrage.

## Installation et configuration initiale

- Détecter l’environnement, les composants installés, les configurations existantes et les services disponibles.
- Proposer les installations nécessaires et expliquer leur rôle avant de demander confirmation.
- Préparer une configuration adaptée au partage de fichiers domestique.
- Préserver les configurations existantes ; signaler les éléments que SambaPilot ne sait pas gérer.
- Ne pas écraser une configuration inconnue ou complexe pour la remplacer par une configuration minimale.

## Dossiers partagés

- Lister les partages, leur chemin, leur état et leurs règles d’accès.
- Créer et modifier un partage à partir d’un dossier choisi par l’utilisateur.
- Choisir le nom, la description, la visibilité et les droits d’accès.
- Activer ou désactiver un partage et retirer sa déclaration sans supprimer le dossier ni son contenu.
- Vérifier les chemins, les doublons et les valeurs de configuration avant application.

## Utilisateurs et permissions

- Gérer l’accès des comptes Samba et leur correspondance avec les comptes Linux.
- Distinguer les changements des comptes Linux de ceux des comptes Samba et obtenir l’accord pour chacun.
- Définir les utilisateurs ou groupes autorisés, en lecture seule ou en lecture et écriture.
- Examiner les propriétaires, les groupes, les permissions Linux et les ACL éventuelles des dossiers.
- Expliquer les conflits entre les permissions du système de fichiers et les règles Samba.
- Présenter séparément toute modification récursive des droits, avec son périmètre et ses limites de restauration.
- Réserver l’accès invité à une activation explicite.
- Ne pas enregistrer les mots de passe dans le dépôt, les journaux, les aperçus ou les arguments des commandes.

## Pare-feu et réseau

- Détecter le gestionnaire de pare-feu et les règles existantes avant toute proposition.
- Présenter les règles à ajouter ou à retirer, avec les interfaces, les réseaux et les adresses concernés.
- Tenir compte d’IPv4 et d’IPv6 dans le périmètre d’accès retenu.
- Proposer un accès limité au réseau local choisi ; ne pas ouvrir automatiquement tous les réseaux.
- Ne pas désactiver le pare-feu ni remplacer l’ensemble de ses règles.
- Identifier les règles créées par SambaPilot pour pouvoir les retirer sans affecter les autres.
- Si le pare-feu n’est pas pris en charge ou si l’état est ambigu, bloquer sa modification et expliquer le problème.

## Services et diagnostic

- Afficher l’état des services et distinguer leur démarrage immédiat de leur activation au démarrage de l’ordinateur.
- Vérifier la configuration avant tout rechargement ou redémarrage.
- Expliquer l’impact d’une interruption sur les connexions en cours.
- Présenter les erreurs utiles : dossier inaccessible, compte non autorisé, configuration invalide, service arrêté ou accès réseau bloqué.
- Distinguer un contrôle local d’un test de connexion depuis un autre appareil.

## Confirmation, sauvegarde et restauration

Avant chaque intervention, afficher les changements concrets : fichiers, comptes, droits, services, paquets et règles réseau concernés. L’utilisateur doit pouvoir annuler sans modification.

Après confirmation, vérifier que l’état de la machine correspond toujours à celui de l’aperçu. Si cet état a changé, recalculer la proposition et demander une nouvelle confirmation.

Créer des sauvegardes datées des configurations concernées et conserver un compte rendu sans secrets. Les sauvegardes locales sensibles devront être protégées et rester hors du dépôt.

Une restauration est elle-même une modification nécessitant un aperçu et une confirmation. Distinguer les configurations restaurables des effets qui demandent un traitement séparé, comme les paquets installés, les comptes, les mots de passe et les permissions récursives. Ne pas promettre un retour arrière intégral sans preuve.

En cas d’échec, indiquer les actions effectuées, celles qui n’ont pas été réalisées et les moyens de récupération disponibles.
