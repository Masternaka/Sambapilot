# Préparer l’installation de Samba

## Périmètre disponible

SambaPilot décrit les étapes nécessaires pour préparer Samba sur Arch Linux, Debian ou Fedora. Le plan repose sur un constat des outils, des services, de la présence de la configuration et des paquets propres au profil détecté. La [matrice Linux](compatibilite-linux.md) précise les noms de paquets et de services.

Il reste **descriptif et non applicable**. Il n’installe rien, ne télécharge aucun paquet, ne synchronise aucun dépôt et ne modifie aucun fichier, compte, service ou pare-feu. Le champ JSON `can_apply` reste faux.

La transaction exacte, ses dépendances, ses conflits et les éventuelles mises à jour ne sont pas encore calculés. Ce plan ne constitue donc pas une demande d’autorisation pour exécuter une installation.

## Depuis le terminal

Depuis la racine du dépôt, essayer les trois scénarios fictifs :

```sh
python3 -B -m sambapilot preparer-installation --demo fresh
python3 -B -m sambapilot preparer-installation --demo configured --distribution debian
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

La rubrique **Installation** affiche initialement le scénario fictif sans Samba. Deux menus permettent de choisir le scénario et la distribution fictive. Leur modification revient immédiatement aux exemples et invalide une consultation locale en attente ; le bouton « Préparer l’exemple » permet aussi de régénérer le plan.

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
4. Le service `smbd.service` sur Debian ou `smb.service` sur Arch et Fedora : conserver un service actif, proposer un démarrage seulement après les prérequis, ou diagnostiquer un état inconnu ou en échec.
5. Le démarrage automatique, distinct de l’activité actuelle du service.
6. Le gestionnaire de pare-feu, les règles effectives et le réseau à choisir.
7. Les essais depuis un autre appareil, avec des comptes autorisés et non autorisés.

Un service masqué bloque la proposition de démarrage : aucun démasquage automatique n’est prévu. Une configuration inaccessible n’est jamais considérée absente ni remplaçable. Plusieurs services de pare-feu actifs demandent un examen ; aucun gestionnaire ni sous-réseau n’est choisi arbitrairement.

## Consultations locales

Le diagnostic reste en lecture seule. Si la distribution est reconnue et son outil système détecté, la préparation consulte la base locale des paquets. Pour Arch :

```text
/usr/bin/pacman --query -- samba
/usr/bin/pacman --query -- smbclient
```

Sur Debian, les requêtes utilisent `dpkg-query --show` avec un format explicite du nom, de l’état et de la version. Un paquet dépaqueté ou partiellement configuré reste inconnu ; des fichiers de configuration résiduels ne signifient pas que le paquet est installé. Sur Fedora, les requêtes utilisent `rpm --query` avec un format explicite du nom et de la version. Ni apt ni dnf ne sont exécutés.

Les chemins `/usr/bin` et `/usr/sbin` sont acceptés pour les outils de requête. Aucun exécutable provenant d’un shim utilisateur n’est lancé. Les noms de paquets et les chemins de programme forment des listes fermées. Les appels sont sans shell, sans `sudo`, sans saisie interactive et limités à trois secondes chacun.

Un retour d’erreur ne prouve pas une absence : seule la réponse explicite « paquet introuvable » est interprétée comme telle. Les erreurs de base, les réponses inattendues, les refus et les délais dépassés restent inconnus et bloquent la proposition concernée.

Sur un système hors Linux, inconnu ou dont les familles sont ambiguës, les requêtes de paquets ne sont pas lancées et le plan est bloqué. Aucun marqueur de bureau n’est recherché. Le gestionnaire et le service attendus viennent du profil, sans supposer un pare-feu ou une politique SELinux/AppArmor.

## Validation réalisée et suites

Les tests simulent les consultations des paquets et des services. Ils couvrent les trois scénarios, les erreurs, les incohérences, les services masqués et la séparation du démarrage automatique. Les scénarios fictifs sont vérifiés sans accès aux fichiers ni lancement de processus.

Aucune vraie requête pacman, dpkg ou RPM ni installation sur les cibles n’a été exécutée localement. La CI prépare ces contrôles dans des conteneurs temporaires, sans constituer encore une preuve de réussite. Les essais natifs GTK restent à effectuer. Le diagnostic local existant et les requêtes de paquets devront être vérifiés ensemble sur la cible autorisée.

Avant toute future application, il faudra relire l’état, présenter la transaction exacte et les changements de configuration, sauvegarder ce qui doit l’être et obtenir une autorisation explicite pour les interventions concernées. L’empreinte incluse dans le plan identifie le constat actuel ; elle ne remplace pas cette relecture ni cette autorisation.

Références officielles : [opération de requête pacman](https://man.archlinux.org/man/pacman.8.en), [paquet Samba et dépendance smbclient](https://archlinux.org/packages/extra/x86_64/samba/), [fichiers et unités de service du paquet Samba](https://archlinux.org/packages/extra/x86_64/samba/files/).
