# Préparer l’installation de Samba

## Périmètre disponible

SambaPilot peut décrire les étapes nécessaires pour préparer Samba sur un environnement Linux identifié comme Arch. Le plan repose sur un constat des outils, des services, de la présence de la configuration et des états des paquets `samba` et `smbclient`.

Il reste **descriptif et non applicable**. Il n’installe rien, ne télécharge aucun paquet, ne synchronise aucun dépôt et ne modifie aucun fichier, compte, service ou pare-feu. Le champ JSON `can_apply` reste faux.

La transaction exacte, ses dépendances, ses conflits et les éventuelles mises à jour ne sont pas encore calculés. Ce plan ne constitue donc pas une demande d’autorisation pour exécuter une installation.

## Depuis le terminal

Depuis le dossier `sambapilot`, essayer les trois scénarios fictifs :

```sh
python3 -B -m sambapilot preparer-installation --demo fresh
python3 -B -m sambapilot preparer-installation --demo configured
python3 -B -m sambapilot preparer-installation --demo restricted --json
```

`fresh` représente un environnement sans Samba, `configured` une installation avec services actifs et `restricted` des informations inaccessibles. Les versions des paquets affichées dans les exemples sont fictives.

Pour consulter explicitement l’ordinateur courant :

```sh
python3 -B -m sambapilot preparer-installation --local
python3 -B -m sambapilot preparer-installation --local --json
```

Les options `--demo` et `--local` sont obligatoires au choix et mutuellement exclusives. Aucun examen local n’est déclenché par défaut.

Le code `0` signifie que le plan descriptif a été produit et comporte encore des choix à examiner. Le code `2` indique des arguments invalides ou des points bloquants. Aucun de ces codes ne signifie qu’une installation a eu lieu.

## Depuis la fenêtre GTK

La rubrique **Installation** affiche initialement le scénario fictif sans Samba. Un menu et le bouton « Préparer l’exemple » permettent de consulter les autres scénarios.

Le bouton **Examiner cet ordinateur (lecture seule)** demande explicitement le constat local. Les consultations ont lieu dans un fil séparé ; le bandeau indique « Constat local · Aucune installation ». Revenir à un exemple invalide les résultats locaux encore en attente.

Le raccourci du tableau de bord ouvre cette rubrique. Aucun bouton ne permet d’installer les paquets ou d’exécuter les étapes proposées.

## Lecture des résultats

Les paquets sont déclarés installés uniquement si la base locale le confirme. Un exécutable présent ne suffit pas. Le plan vérifie aussi les incohérences : paquet absent mais exécutable présent, ou paquet installé avec des outils attendus non détectés.

Les étapes utilisent les états suivants :

| État | Signification |
| --- | --- |
| Conserver | Le composant ou l’état existant est conservé ; aucune réinstallation ou interruption proposée. |
| À prévoir | Une intervention pourrait être nécessaire, après définition précise et autorisation. |
| À examiner | Un choix ou une vérification manque avant de définir l’intervention. |
| Après les paquets | L’état devra être réexaminé après une future installation autorisée. |
| Bloqué | Une information inconnue, incohérente ou hors périmètre empêche de proposer l’intervention automatiquement. |

Les étapes couvrent séparément :

1. Les paquets serveur et client.
2. La préparation ou l’examen de la configuration, avec candidat, contrôle et sauvegarde avant une future écriture.
3. Le choix des dossiers, des utilisateurs, des groupes et des permissions.
4. Le service `smb.service` : conserver un service actif, proposer un démarrage seulement après les prérequis, ou diagnostiquer un état inconnu ou en échec.
5. Le démarrage automatique, distinct de l’activité actuelle du service.
6. Le gestionnaire de pare-feu, les règles effectives et le réseau à choisir.
7. Les essais depuis un autre appareil, avec des comptes autorisés et non autorisés.

Un service masqué bloque la proposition de démarrage : aucun démasquage automatique n’est prévu. Une configuration inaccessible n’est jamais considérée absente ni remplaçable. Plusieurs services de pare-feu actifs demandent un examen ; aucun gestionnaire ni sous-réseau n’est choisi arbitrairement.

## Consultations locales

Le diagnostic existant reste en lecture seule. Sur une cible Arch avec le gestionnaire système détecté, deux requêtes supplémentaires consultent les paquets :

```text
/usr/bin/pacman --query -- samba
/usr/bin/pacman --query -- smbclient
```

Le chemin système `/usr/sbin/pacman` est également accepté s’il est détecté. Aucun exécutable provenant d’un shim utilisateur n’est lancé. Les noms de paquets et les chemins de programme forment des listes fermées. Les appels sont sans shell, sans `sudo`, sans saisie interactive et limités à trois secondes chacun.

Un retour d’erreur ne prouve pas une absence : seule la réponse explicite « paquet introuvable » est interprétée comme telle. Les erreurs de base, les réponses inattendues, les refus et les délais dépassés restent inconnus et bloquent la proposition concernée.

La présence du dossier Omarchy reste un indice. Elle ne certifie pas une installation fonctionnelle. Sur un système hors Linux ou non identifié comme Arch, les requêtes de paquets ne sont pas lancées et le plan est bloqué.

## Validation réalisée et suites

Les tests simulent les consultations des paquets et des services. Ils couvrent les trois scénarios, les erreurs, les incohérences, les services masqués et la séparation du démarrage automatique. Les scénarios fictifs sont vérifiés sans accès aux fichiers ni lancement de processus.

Aucune vraie requête pacman ni installation sur Omarchy n’a été exécutée pendant le développement. Les essais natifs GTK restent à effectuer. Le diagnostic local existant et les requêtes de paquets devront être vérifiés ensemble sur la cible autorisée.

Avant toute future application, il faudra relire l’état, présenter la transaction exacte et les changements de configuration, sauvegarder ce qui doit l’être et obtenir une autorisation explicite pour les interventions concernées. L’empreinte incluse dans le plan identifie le constat actuel ; elle ne remplace pas cette relecture ni cette autorisation.

Références officielles : [opération de requête pacman](https://man.archlinux.org/man/pacman.8.en), [paquet Samba et dépendance smbclient](https://archlinux.org/packages/extra/x86_64/samba/), [fichiers et unités de service du paquet Samba](https://archlinux.org/packages/extra/x86_64/samba/files/).
