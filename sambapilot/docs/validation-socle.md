# Vérifications du premier socle

## Périmètre livré

Le premier socle fournit un moteur de diagnostic, un adaptateur Linux, un adaptateur de démonstration et une interface terminal avec sortie texte ou JSON. Il inclut une matrice des accès sur des données de démonstration et le code d’une première fenêtre GTK utilisant ces données. Il ne fournit pas encore de commande d’installation ou de modification.

## Vérifications automatisées

La suite `make test` couvre notamment :

- la démonstration sans lecture de fichiers hôtes ni lancement de processus ;
- l’arrêt des sondes sur un système hors Linux ;
- les composants absents et les informations inaccessibles ;
- la lecture de l’identification de distribution sans exécution de son contenu ;
- les requêtes systemd limitées aux unités prévues, sans shell, sans saisie de mot de passe et avec un délai maximal ;
- les réponses systemd manquantes, incomplètes, refusées ou trop lentes ;
- le repérage de la configuration sans lecture de son contenu ;
- la recherche des outils système sans utiliser les shims du `PATH` utilisateur ;
- le rapport JSON et le filtrage des caractères de contrôle dans l’affichage terminal.

`make check` vérifie la syntaxe Python sans générer de bytecode. Les scénarios `fresh`, `configured` et `restricted` représentent respectivement un environnement sans Samba, des services actifs et des informations inaccessibles. Ce sont des simulations, pas une validation de Samba.

## Vérifications de la matrice des accès

Les tests couvrent les autorisations par utilisateur et par groupe, la lecture seule, les exceptions d’écriture, les comptes désactivés, les observations manquantes et les conflits avec les permissions de fichiers. Ils vérifient aussi la traversée des chemins, l’écriture sans lecture, les options hors du modèle et les données en double ou associées à une autre identité.

Le mode `permissions --demo` est testé avec les accès aux fichiers et aux processus bloqués par des doubles de test. La sortie JSON conserve les valeurs inconnues sous forme de `null`, distinctes d’un refus `false`. Les tests existants du diagnostic restent exécutés avec les nouveaux tests.

La matrice ne collecte pas encore les comptes, les ACL ni les configurations réelles. Elle ne certifie aucun accès au serveur et ne valide pas les permissions de l’arborescence complète.

## Limites de validation

La suite comprend 188 tests sans GTK et dix-sept tests natifs optionnels. Les tests sans GTK couvrent aussi les données de présentation, les filtres, les états vides, les détails des conflits, la parité avec le terminal et les dépendances graphiques manquantes. Les dix-sept tests natifs ne sont pas exécutés dans l’environnement initial, où PyGObject est absent. La syntaxe du code GTK est vérifiée, mais cela ne prouve pas la construction des widgets ni leur rendu.

Les tests de préparation des partages vérifient la création, la modification et le retrait sur des chaînes de configuration. Ils couvrent la préservation des autres sections et des commentaires, les fins de ligne, les doublons, les valeurs injectables, les options avancées refusées, les configurations indirectes, les empreintes d’état et l’invalidation des aperçus. Le terminal de préparation est testé sans accès aux fichiers ni lancement de processus. Aucun `testparm` réel n’a été lancé.

L’examen de configuration est testé sur des fichiers temporaires : lecture sans drapeau d’écriture, contenu et date de modification préservés, refus des fichiers spéciaux et des liens symboliques finaux, UTF-8, limite de taille, changements pendant la lecture et droits insuffisants. Les inclusions ne sont jamais ouvertes. Les options non interprétées sont signalées sans exporter leur valeur. Ces essais ne constituent pas une lecture de la configuration réelle de l’ordinateur cible.

La préparation sur fichier choisi est testée avec les mêmes fichiers temporaires : création, modification, retrait, conservation du BOM et des fins de ligne, contrôle de l’empreinte source, refus après modification ou disparition du fichier, annulation et absence d’écriture. Les réglages inconnus ne sont pas devinés pour préremplir un formulaire. Le JSON de plan conserve le candidat complet, à la différence du JSON d’inventaire. Les sources terminal `--demo` et `--config` sont vérifiées comme obligatoires au choix et mutuellement exclusives.

Le contrôle Samba est testé avec un processus simulé : permissions 0700/0600 des éléments temporaires, contenu exact du candidat, arguments fixes sans shell, délai, refus des configurations hors périmètre, retours acceptés ou rejetés, erreurs, nettoyage et vérification de source avant et après. Les tests vérifient que le contrôle n’est jamais déclenché implicitement. Le programme `testparm` est absent de l’environnement ; aucune exécution réelle de Samba n’est validée par ces tests.

La préparation d’installation est testée sur des observations simulées : paquets absents, installés ou inconnus, erreurs de base, incohérences avec les exécutables, service masqué, démarrage automatique et pare-feu non choisi implicitement. Les tests vérifient que les appels pacman sont uniquement des requêtes sur des paquets fixes et qu’aucune consultation de paquet n’est lancée sur un environnement hors périmètre. Aucune vraie transaction ou requête pacman n’a été effectuée.

Les intentions de pare-feu sont testées sans processus, lecture de fichier ou connexion réseau : CIDR IPv4/IPv6, appareils uniques, refus des ouvertures à toutes adresses, bits d’hôte, chevauchements, paramètres de gestionnaire et zone, NetBIOS explicite et empreintes stables. Ces tests ne prouvent ni la validité d’une traduction native ni l’effet des règles sur un gestionnaire réel ; aucun pare-feu n’a été interrogé ou modifié.

Le développement initial est effectué sur macOS avec Python 3.9.6. Les requêtes Linux sont testées avec des résultats simulés ; aucun service réel n’a été interrogé dans ces tests.

Restent à vérifier sur un environnement Omarchy autorisé : les chemins détectés, l’identification de l’environnement, les retours réels de systemd et les restrictions de lecture d’un compte ordinaire.

Aucune installation de dépendances, modification système, connexion Samba, règle de pare-feu ou interface GTK n’est validée par cette suite. Le conditionnement Python et les workflows GitHub existants n’ont pas été exécutés.
