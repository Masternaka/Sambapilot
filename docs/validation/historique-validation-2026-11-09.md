# Historique des vérifications du 9 novembre 2026

Les résultats ci-dessous décrivent les lots successifs. Le [bilan actuel](validation-socle.md) est la référence pour l’état présent du projet.

## Périmètre livré

Le premier socle fournit un moteur de diagnostic, un adaptateur Linux, un adaptateur de démonstration et une interface terminal avec sortie texte ou JSON. Il inclut une matrice des accès sur des données de démonstration et le code d’une première fenêtre GTK utilisant ces données. Il inclut aussi l’examen de fichiers choisis, les aperçus de partage, le contrôle facultatif avec `testparm`, la préparation descriptive d’installation et les intentions de pare-feu. Il ne fournit aucune commande appliquant une installation ou une modification système.

## Revue locale du 9 novembre 2026

Vérifications effectuées depuis la racine du dépôt sur macOS avec Python 3.9.6, sans installation de dépendances :

| Vérification | Résultat |
| --- | --- |
| `make test` | 205 tests découverts : 188 réussis et 17 tests GTK ignorés, aucun échec. |
| `make check` | Syntaxe de 29 fichiers Python vérifiée, sans génération de bytecode. |
| Exemples documentés | 14 commandes distinctes d’aide, de démonstration et de plan réseau exécutées avec les codes attendus. |
| Liens internes | 39 liens locaux vérifiés dans 13 documents Markdown. |
| `git diff --check` | Aucun défaut d’espacement signalé sur les différences suivies. |

Les tests GTK sont ignorés par défaut tant que `SAMBAPILOT_GTK_TESTS=1` n’est pas demandé ; ce résultat ne constitue pas une vérification des dépendances graphiques installées. Les tests créent et nettoient des fichiers temporaires de travail, sans appliquer de configuration sur la machine.

Les commandes d’exemple et les liens internes de la documentation sont également vérifiés dans cette revue. Les déplacements de fichiers déjà présents dans l’arbre de travail sont conservés ; aucun commit ni publication n’est réalisé.

## Vérification après classement du dépôt

Le 9 novembre 2026, dix documents sont déplacés dans `docs/guides/`, `docs/conception/` et `docs/validation/`. L’index reste dans `docs/README.md`. Le README, AGENTS, les liens relatifs et le chemin d’aide affiché en cas de dépendance GTK manquante sont actualisés.

Après classement : `make test` donne 188 réussites et 17 tests GTK ignorés ; `make check` valide la syntaxe de 29 fichiers ; `make demo` produit le diagnostic fictif attendu. Les 39 liens internes des 13 documents Markdown sont valides.

La comparaison des empreintes avant/après confirme que les 32 fichiers de code, tests et configuration hors `gui.py` sont identiques. Dans `gui.py`, seul le chemin du guide change. Aucun fichier existant n’est supprimé : l’inventaire ne révèle aucun artefact inutile. Les déplacements déjà présents avant cette intervention sont conservés. Les essais graphiques et système restent hors de cette vérification.

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

`make check` vérifie désormais la syntaxe Python du code, des tests et des scripts, ainsi que les cibles locales des liens Markdown, sans générer de bytecode. Les scénarios `fresh`, `configured` et `restricted` représentent respectivement un environnement sans Samba, des services actifs et des informations inaccessibles. Ce sont des simulations, pas une validation de Samba.

## Vérifications de la matrice des accès

Les tests couvrent les autorisations par utilisateur et par groupe, la lecture seule, les exceptions d’écriture, les comptes désactivés, les observations manquantes et les conflits avec les permissions de fichiers. Ils vérifient aussi la traversée des chemins, l’écriture sans lecture, les options hors du modèle et les données en double ou associées à une autre identité.

Le mode `permissions --demo` est testé avec les accès aux fichiers et aux processus bloqués par des doubles de test. La sortie JSON conserve les valeurs inconnues sous forme de `null`, distinctes d’un refus `false`. Les tests existants du diagnostic restent exécutés avec les nouveaux tests.

La matrice ne collecte pas encore les comptes, les ACL ni les configurations réelles. Elle ne certifie aucun accès au serveur et ne valide pas les permissions de l’arborescence complète.

## Limites de validation

Lors de la première revue, la suite comprend 188 tests sans GTK et dix-sept tests natifs optionnels. La préparation CI ci-dessous ajoute ensuite quatre tests Samba optionnels. Les tests sans GTK couvrent aussi les données de présentation, les filtres, les états vides, les détails des conflits, la parité avec le terminal et les dépendances graphiques manquantes. Les dix-sept tests natifs sont ignorés lors de la revue locale ; aucune session GTK n’est ouverte. La syntaxe du code GTK est vérifiée, mais cela ne prouve pas la construction des widgets ni leur rendu.

Les tests de préparation des partages vérifient la création, la modification et le retrait sur des chaînes de configuration. Ils couvrent la préservation des autres sections et des commentaires, les fins de ligne, les doublons, les valeurs injectables, les options avancées refusées, les configurations indirectes, les empreintes d’état et l’invalidation des aperçus. Le terminal de préparation est testé sans accès aux fichiers ni lancement de processus. Aucun `testparm` réel n’a été lancé.

L’examen de configuration est testé sur des fichiers temporaires : lecture sans drapeau d’écriture, contenu et date de modification préservés, refus des fichiers spéciaux et des liens symboliques finaux, UTF-8, limite de taille, changements pendant la lecture et droits insuffisants. Les inclusions ne sont jamais ouvertes. Les options non interprétées sont signalées sans exporter leur valeur. Ces essais ne constituent pas une lecture de la configuration réelle de l’ordinateur cible.

La préparation sur fichier choisi est testée avec les mêmes fichiers temporaires : création, modification, retrait, conservation du BOM et des fins de ligne, contrôle de l’empreinte source, refus après modification ou disparition du fichier, annulation et absence d’écriture. Les réglages inconnus ne sont pas devinés pour préremplir un formulaire. Le JSON de plan conserve le candidat complet, à la différence du JSON d’inventaire. Les sources terminal `--demo` et `--config` sont vérifiées comme obligatoires au choix et mutuellement exclusives.

Le contrôle Samba est testé avec un processus simulé : permissions 0700/0600 des éléments temporaires, contenu exact du candidat, arguments fixes sans shell, délai, refus des configurations hors périmètre, retours acceptés ou rejetés, erreurs, nettoyage et vérification de source avant et après. Les tests vérifient que le contrôle n’est jamais déclenché implicitement. Aucun `testparm` réel n’est exécuté lors de cette revue ; les tests ne valident pas une exécution réelle de Samba.

La préparation d’installation est testée sur des observations simulées : paquets absents, installés ou inconnus, erreurs de base, incohérences avec les exécutables, service masqué, démarrage automatique et pare-feu non choisi implicitement. Les tests vérifient que les appels pacman sont uniquement des requêtes sur des paquets fixes et qu’aucune consultation de paquet n’est lancée sur un environnement hors périmètre. Aucune vraie transaction ou requête pacman n’a été effectuée.

Les intentions de pare-feu sont testées sans processus, lecture de fichier ou connexion réseau : CIDR IPv4/IPv6, appareils uniques, refus des ouvertures à toutes adresses, bits d’hôte, chevauchements, paramètres de gestionnaire et zone, NetBIOS explicite et empreintes stables. Ces tests ne prouvent ni la validité d’une traduction native ni l’effet des règles sur un gestionnaire réel ; aucun pare-feu n’a été interrogé ou modifié.

Le développement initial est effectué sur macOS avec Python 3.9.6. Les requêtes Linux sont testées avec des résultats simulés ; aucun service réel n’a été interrogé dans ces tests.

Restent à vérifier sur un environnement Omarchy autorisé : les chemins détectés, l’identification de l’environnement, les retours réels de systemd et les restrictions de lecture d’un compte ordinaire.

Aucune installation de dépendances, modification système, connexion Samba, règle de pare-feu ou interface GTK n’est validée par cette suite. Le conditionnement Python n’a pas été exécuté. Un workflow GitHub Actions est maintenant préparé ; aucune validation CI distante n’a encore été effectuée.

## Préparation CI et intégration native

Un workflow à trois jobs est ajouté : tests sur Python 3.9/3.12/3.14, suite complète avec GTK4 et Samba sous Linux, puis construction et contrôle de distribution. Les 4 tests Samba sont optionnels, activés seulement sur demande explicite ; ils ne sont pas exécutés localement. Le détail et les effets sur les runners temporaires sont décrits dans le [guide de vérification automatisée](verification-automatisee.md).

Après cet ajout, la suite locale découvre 209 tests : 188 réussis et 21 ignorés (17 GTK et 4 Samba). Le YAML du workflow est analysé localement ; cela ne valide ni son exécution dans GitHub Actions ni le résultat des dépendances natives. Le conditionnement reste en attente : les outils locaux disponibles ne satisfont pas les prérequis et aucune installation n’est effectuée.

Les contrôles finaux vérifient la syntaxe de 32 fichiers Python et les 46 liens locaux des 14 documents. Des fixtures temporaires confirment que les scripts refusent les liens absents ou hors dépôt, la syntaxe invalide, un wheel contenant du code altéré et une archive source incomplète. Ces fixtures ne remplacent pas une construction réelle du paquet.

## Construction après push et préparation Arch

Le workflow est étendu à quatre jobs. Les constructions attendent la réussite des tests ; les archives Python sont conservées et transférées au job Arch avec contrôle SHA-256 et du commit. Le modèle makepkg produit un paquet de développement et un lanceur GTK4 ; le paquet est prévu pour être installé et contrôlé uniquement dans le conteneur CI temporaire. Aucun dépôt pacman, aucune signature et aucune release ne sont publiés.

Les quatre tests du générateur vérifient l’empreinte réelle de l’archive et sa préservation, le refus des révisions invalides, le refus d’une source ne correspondant pas à la version et la conservation d’un dossier de sortie existant. La suite locale découvre désormais 213 tests : 192 réussis et 21 ignorés. Le YAML à quatre jobs et le modèle shell sont analysés sans exécuter makepkg ni installer de dépendances.

Les constructions réelles Python et Arch restent en attente d’une première exécution GitHub. Le [guide de distribution](../guides/distribution-omarchy.md) conserve les étapes restantes pour le futur dépôt personnel et la première action de reprise.

## Partages d’un fichier choisi dans GTK

La page Partages peut afficher les déclarations locales d’une configuration explicitement choisie, avec chemin et empreinte source, détails des réglages, valeurs inconnues et limites. Le rapport reste séparé de la démonstration et de la matrice fictive. Le retour aux exemples conserve leurs actions. Le rechargement et la nouvelle sélection retirent les anciens résultats ; les résultats de lecture obsolètes ne remplacent pas la source courante.

Huit tests ordinaires vérifient les détails déclarés sans permissions effectives déduites, l’absence d’héritage global, les listes vides/absentes/ambiguës, les identités partielles, les options avancées sans leurs valeurs brutes, les inventaires bloqués, les sections spéciales, le refus d’un rapport fictif et la préservation d’un fichier temporaire avec BOM et fins de ligne CRLF. Six tests GTK supplémentaires préparent les parcours fichier/exemples, le retour au rapport, l’effacement, les erreurs, les résultats obsolètes, le rechargement et l’annulation ; ils ne sont pas exécutés localement.

La suite découvre désormais 227 tests : 200 réussis et 27 ignorés (23 GTK et 4 Samba). `make check` vérifie la syntaxe de 35 fichiers Python et les 56 liens locaux de 15 documents. Aucun fichier système n’est modifié. Le rendu et le comportement natifs GTK, la CI distante et les essais Omarchy restent à confirmer.

## Recherche, catégories et préparation directe des déclarations

L’inventaire expose deux champs complémentaires par déclaration (`missing_fields`, `ambiguous_fields`) ; les options non interprétées et les destinataires non résolus restent séparés. Les filtres de la page Partages combinent une recherche par nom/chemin avec une catégorie. Les explications ne traitent pas les valeurs locales absentes comme une preuve de configuration effective invalide. La préparation directe reste conditionnée au moteur existant, et une impossibilité est expliquée sans conserver un ancien aperçu.

Neuf tests ordinaires supplémentaires couvrent la casse et les espaces de recherche, les paramètres absents ou concurrents, les booléens invalides, les substitutions, les catégories multiples, les intersections sans résultat, les inventaires bloqués, les listes vides, l’absence de fuite des valeurs d’options et les contraintes supplémentaires du rédacteur. Trois tests GTK supplémentaires sont préparés pour les filtres/réinitialisations, la modification directe et les refus avec invalidation ; ils restent ignorés localement.

Résultat local : 239 tests découverts, 209 réussis et 30 ignorés (26 GTK et 4 Samba). Syntaxe de 35 fichiers Python et 56 liens locaux valides. Aucun test natif, déploiement, installation ou changement système n’est effectué pour ce lot.

## Export Markdown de l’inventaire

Le moteur prépare un document à partir du rapport déjà lu, sans nouvelle sonde. La date UTC de lecture est conservée dans le champ facultatif `read_at`, distinct de la date de création du document. Les informations personnelles incluses sont signalées, les textes dynamiques échappés et le fichier brut, les candidats, commentaires et valeurs inconnues exclus. L’écriture explicite publie un fichier complet privé sans écraser de destination existante.

Quinze tests ordinaires ajoutés vérifient le contenu, les dates, les modes fictifs ou bloqués, l’absence de relecture implicite, l’échappement, les permissions, les fichiers/liens/dossiers existants, les erreurs, le nettoyage et une création concurrente de destination. Ils couvrent aussi l’aperçu terminal, la confirmation explicite et la conservation du code de sortie d’un inventaire bloqué. Quatre tests GTK supplémentaires préparent les parcours d’aperçu complet malgré les filtres, d’enregistrement, de refus d’écrasement, d’annulation et de source obsolète ; ils restent ignorés localement.

Résultat local : 258 tests découverts, 224 réussis et 34 ignorés (30 GTK et 4 Samba), syntaxe de 38 fichiers Python et 61 liens locaux de 16 documents vérifiés. Les exports des tests sont créés uniquement dans des dossiers temporaires ; aucune configuration active n’est écrite. Les essais natifs GTK, la CI et les constructions de paquets restent à confirmer.

## Reprise de préparation après changement externe

Le moteur propose une relecture à examiner, liée à la session d’origine, puis une adoption explicite après une nouvelle lecture et une vérification de l’action. Une seconde modification de la source, un conflit de création, une cible devenue absente/incomplète/avancée ou un fichier inaccessible refuse la reprise. L’ancienne session conserve sa source et perd son ancien candidat. L’adoption réussie fournit une nouvelle session sans candidat ; le formulaire conserve ses valeurs brutes sans fusion automatique.

Dix tests ordinaires supplémentaires couvrent la séparation relecture/adoption, la génération ultérieure d’un aperçu, la seconde modification, les sessions distinctes, les structures bloquées, les cibles modifiées, les collisions de noms, le retrait, les lectures refusées et la préservation du BOM/CRLF et des métadonnées de source. Quatre tests GTK sont ajoutés pour la conservation exacte des champs, le parcours complet, les résultats obsolètes après annulation et les refus conservant une saisie invalide ; ils ne sont pas exécutés localement.

Résultat local : 272 tests découverts, 234 réussis et 38 ignorés (34 GTK et 4 Samba). La syntaxe de 38 fichiers Python et les 63 liens locaux de 16 documents sont vérifiés. Les comparaisons restent en mémoire et les fichiers temporaires sont les seules sources modifiées par les tests. Aucune configuration active n’est enregistrée. La validation native GTK/Omarchy et la CI distante restent en attente.

## Laboratoire de sauvegarde/restauration

Un module autonome crée son propre dossier temporaire et un fichier fictif à partir de données en mémoire, sans chemin de configuration réelle en entrée. Il produit des copies datées privées et vérifiées, prépare une comparaison et restaure exclusivement son fichier fictif après confirmation. L’état remplacé est sauvegardé pour éprouver un retour vers cet état. Les sauvegardes sont jetables à la fermeture et ne constituent pas une fonctionnalité de sauvegarde durable.

Vingt-deux tests ordinaires supplémentaires couvrent les octets BOM/CRLF, les dates et permissions, l’intégrité, l’aperçu sans écriture, les confirmations, les restaurations et leur reprise, les cibles modifiées, les liens, les données altérées, les erreurs de lecture/écriture/remplacement, les collisions et le nettoyage. Les échecs de lecture et d’écriture sont injectés ; le verrouillage contre des processus extérieurs et la durabilité après panne restent hors validation.

La suite découvre désormais 294 tests : 256 réussis et 38 ignorés (34 GTK et 4 Samba). La syntaxe de 40 fichiers Python est vérifiée. Aucune configuration active n’est lue ou restaurée par ces essais. Les limites et le scénario reproductible sont décrits dans le [guide de simulation](../guides/simulation-sauvegarde-restauration.md).
