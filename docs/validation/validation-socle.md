# Bilan de validation de SambaPilot

## Stabilisation — 13 novembre 2026

Le dernier commit publié avant ce lot, `74754ba`, a une [CI réussie](https://github.com/Masternaka/Sambapilot/actions/runs/43435734134). Ce résultat ne couvre pas les nouvelles fiches, profils et volumes encore locaux au moment de cette vérification.

La stabilisation ajoute un [parcours manuel court](recette-linux.md), harmonise les boutons « Préparer les adresses… » avec leur comportement sans connexion et répartit verticalement les commandes de volume de la fiche pour réduire la largeur nécessaire. Le rendu, le clavier et le presse-papiers restent à examiner sur une session Linux réelle.

## Diagnostic par partage — 13 novembre 2026

La [fiche par partage](../guides/diagnostic-partage.md) relie les déclarations du fichier choisi ou des exemples aux incertitudes, aux pistes communes de dépannage et aux adresses facultatives. Elle conserve la source, son empreinte et sa date. Aucun état du tableau de bord fictif n’est traité comme observation d’un fichier réel ; les droits effectifs et l’accès réseau restent inconnus.

Le dossier et le volume sont examinés seulement sur demande. Les exemples restent séparés des constats locaux. Pour un fichier choisi, GTK exige la confirmation du dossier sur cet ordinateur ; le terminal exige `--local-volume`. Le constat porte sur le chemin déclaré, avec un point attendu explicite, sans le présenter comme état du serveur distant saisi. Une modification du fichier constatée avant/après la lecture locale invalide les résultats.

`make test` traite **426 tests : 370 réussis et 56 natifs ignorés** (52 GTK et 4 Samba), sans erreur ni échec. Les 17 tests ordinaires ajoutés couvrent la sélection du partage, les réglages inconnus, les noms non portables, le refus d’adresses avec secrets, les volumes de chemin/portée incompatibles, la conservation de la source et l’absence de consultation locale implicite. La démonstration CLI avec connexion fictive et volume simulé absent a été exécutée sans accès hôte.

Cinq tests GTK préparent l’ouverture sans sonde, la copie avec presse-papiers simulé, le volume fictif, l’exigence de confirmation locale, l’invalidation et le refus d’une source modifiée. Ils sont ignorés sur ce Mac. Le contrôle du paquet installé inclut la fiche fictive dans le terminal et GTK ; ses processus restent simulés dans la suite locale ordinaire.

`make check` valide **61 fichiers Python** et les cibles locales des liens Markdown ; `git diff --check` réussit. Aucun GTK, presse-papiers réel, constat réel de volume ou contrôle de connexion lancé localement. Aucune installation, application de configuration, publication, création de commit ou push. Les nouveaux parcours natifs et le rendu restent à confirmer en CI et sur les cibles autorisées.

## Examen des volumes — 13 novembre 2026

La commande `examiner-volume` et la rubrique Maintenance distinguent les chemins choisis, le point attendu, le montage couvrant le dossier, les options de lecture seule et les métadonnées accessibles. La lecture locale est explicite et réservée à Linux ; les cinq scénarios fictifs ne consultent pas l’hôte. Aucun volume monté/démonté ni partage activé ; l’identité UUID et les droits restent inconnus. Voir le [guide des volumes](../guides/examen-volumes.md).

`make test` traite **404 tests : 353 réussis et 51 ignorés** (47 GTK et 4 Samba), sans échec ni erreur. Les 22 tests ordinaires ajoutés couvrent les montages parents, imbriqués et empilés, les espaces échappés, les tables illisibles/malformées/trop grandes, les erreurs de métadonnées, le refus des liens et la relecture de table. Les scénarios de démonstration ont été exécutés localement sans lecture de table réelle ni lancement de processus. Le test des descripteurs simule `O_PATH` et les ouvertures sous macOS : il ne valide pas leur comportement Linux natif.

Trois tests GTK préparent les exemples, l’invalidation après changement de chemin, le retour aux exemples et le refus de démarrer une lecture locale avec des chemins invalides. Ils sont ignorés sur ce Mac. Les contrôles du paquet installé ajoutent seulement les scénarios fictifs CLI/GTK ; les processus de ces contrôles restent simulés dans les tests ordinaires.

Le contrôle de profil CI est étendu pour analyser `/proc/self/mountinfo` dans le conteneur et vérifier le lecteur Linux sur ses propres dossiers temporaires présents, absents et liés symboliquement. Il ne crée aucun point de montage. Ces contrôles réels ne sont pas exécutés pendant cette intervention et restent à confirmer en CI ; ils ne remplaceront pas un essai autorisé avec un vrai disque externe.

`make check` valide **58 fichiers Python** et les cibles locales des liens Markdown ; `git diff --check` réussit. Aucun GTK ou contrôle de volume réel lancé localement, aucune installation ou configuration système modifiée, aucun commit ni push. Le rendu graphique, les courses avec de vrais montages et les permissions effectives restent non validés.

## Profils de partage — 13 novembre 2026

Les [profils de partage](../guides/profils-partage.md) personnel, familial et médias en lecture seule complètent les créations, dans le terminal et GTK. Ils suggèrent des noms, chemins et choix de droits/visibilité ; les comptes et groupes ne sont ni déduits ni créés. Les champs restent modifiables, l’accès invité est désactivé et la préparation conserve `can_apply: false`. La modification et le retrait d’une déclaration refusent les profils.

`make test` traite **379 tests : 331 réussis et 48 natifs ignorés** (44 GTK et 4 Samba), sans erreur ni échec. Les 16 tests ordinaires ajoutés couvrent les défauts, les personnalisations, les identités absentes/invalides, les noms en conflit, le refus en modification/retrait avant lecture de fichier et la conservation des commentaires, BOM et fins de ligne. Un exemple CLI médias a été exécuté localement avec des données fictives ; aucun programme système ni réseau consulté.

Trois tests GTK préparent le préremplissage sans identité ni aperçu automatique, la conservation des saisies et l’invalidation, puis la désactivation des profils pour les déclarations existantes. Ils sont ignorés sur ce Mac. Le contrôle du paquet installé inclut les trois profils CLI et un parcours GTK fictif demandant l’aperçu après saisie d’un groupe ; les tests ordinaires de ce contrôleur passent avec les processus simulés.

`make check` valide **54 fichiers Python** et les cibles locales des liens Markdown ; `git diff --check` réussit. Aucun GTK lancé localement, aucune installation ou modification système, aucun contrôle `testparm` ni accès Samba effectué pour ce lot. Aucun commit/push ou lancement CI ; les nouvelles vérifications natives et le rendu restent à confirmer après publication.

## Fiche de connexion — 13 novembre 2026

La [fiche de connexion](../guides/fiche-connexion.md) est ajoutée dans le terminal et sur les partages GTK, avec serveur DNS/IPv4 saisi explicitement, adresses Windows/SMB et instructions Windows/macOS/Linux. Le moteur est indépendant de GTK et ne consulte ni l’hôte ni le réseau. Les données fictives, le fichier choisi, son empreinte et sa date de lecture restent distincts ; un accès non testé est `null`, pas un refus.

`make test` traite **360 tests : 315 réussis et 45 ignorés** (41 GTK et 4 Samba), sans erreur ni échec. Les 17 tests ordinaires ajoutés couvrent les adresses, les espaces et accents, les serveurs et noms non pris en charge, les URL avec identifiants refusées sans reprise du secret dans l’erreur, les sources bloquées et la préservation du fichier/date de lecture. Ils vérifient aussi l’absence de consultation DNS, de fichier implicite ou de processus dans les exemples. La démonstration terminal a été exécutée localement avec `serveur.local`, sans connexion.

Trois tests GTK préparent la génération, la copie avec presse-papiers simulé, l’invalidation après changement de serveur et la fermeture après changement de source. Ils sont ignorés sur ce Mac. Le contrôle du paquet installé inclut désormais la commande fictive et, avec `--gtk`, l’ouverture de la fiche puis son invalidation, sans copie ni accès réseau. Les tests ordinaires du contrôleur passent avec les appels de processus simulés.

`make check` valide la syntaxe de **52 fichiers Python** et les cibles locales des liens Markdown ; `git diff --check` réussit. Aucun lancement de GTK, test de presse-papiers réel, installation ou connexion Samba effectué localement. Aucune exécution distante de ce lot, aucun commit ni push. Les essais natifs peuvent se faire en CI sans ordinateur Linux local ; le rendu et les connexions depuis les appareils clients restent à confirmer ultérieurement.

## Correction du contrôleur CI — 13 novembre 2026

Le [run GitHub 43431525423](https://github.com/Masternaka/Sambapilot/actions/runs/43431525423), sur le commit `44fef000f640fadae94bdfe80299fbccc16dc9ea`, est examiné à partir du journal fourni et des trois artefacts de profils téléchargés en lecture seule. Les bilans `profile.json` d’Arch, Debian et Fedora indiquent chacun **338 tests réussis, aucun test ignoré, aucune erreur**, avec `native_required: true` (38 tests GTK et 4 Samba). La construction des archives, leur contrôle et l’installation du wheel réussissent également avant l’étape suivante.

Les trois fichiers `installed.log` contiennent la même exception : `AttributeError: 'tuple' object has no attribute 'gtk'`, dans `smoke_installed.py`. Une boucle de commandes réutilisait `args`, qui contenait auparavant les options argparse ; la lecture de `args.gtk` échouait après les commandes terminal. Le contrôle GTK du paquet installé n’était donc pas atteint. Les jobs Distribution Python et Paquet Arch sont ignorés à cause de cette dépendance en échec.

La correction sépare `options` et `command_args`. Deux tests de régression parcourent le contrôleur avec et sans `--gtk`, en simulant les appels de processus et la frontière du paquet installé ; ils vérifient que les options survivent aux boucles. Ils ne constituent aucune installation ou validation GTK locale. Le workflow affiche désormais `installed.log` même en cas d’échec, tout en restituant le code de sortie d’origine.

Après correction, `make test` traite **340 tests : 298 réussis et 42 natifs ignorés**, sans erreur ni échec. `make check` et `git diff --check` passent. La syntaxe des blocs shell est contrôlée sans exécuter les installations ; un processus factice vérifie aussi l’affichage du journal et la propagation d’un code d’échec. Aucun logiciel installé sur la machine, aucun commit/push ni relance GitHub réalisé. La correction et la suite du contrôle GTK installé restent à confirmer après un nouveau push autorisé.

## Contrôle du paquet installé — 13 novembre 2026

La prochaine étape de validation est préparée dans les trois profils CI : construction du wheel et des sources, contrôle des archives, installation du wheel local dans un environnement virtuel temporaire, puis contrôle GTK du paquet installé hors du dépôt. L’option `--gtk` de `smoke_installed.py` exige la création de la fenêtre et des huit pages, les trois profils fictifs, les trois symptômes, le décodage GDK des huit PNG et la résolution de l’icône par GTK. Sans cette option, GTK reste non chargé.

Les contrôles locaux traitent **338 tests : 296 réussis et 42 ignorés**, sans échec ni erreur. Les quatre tests supplémentaires vérifient les ressources absentes, mal dimensionnées, tronquées et conformes sur des fichiers temporaires. Le refus d’utiliser les sources comme paquet installé est également vérifié avec `--gtk`. `make check` valide la syntaxe des 49 fichiers Python et les liens locaux. Le YAML et ses 14 blocs shell sont analysés sans exécuter les installations ; `git diff --check` réussit.

Aucun wheel construit ou installé, aucun GTK lancé et aucun job distant exécuté localement pour ce lot. Les validations réelles sont attendues dans les artefacts CI : `profile.json`, `installed.log` et `xvfb.log`. Le [guide CI](verification-automatisee.md) explique les effets et les limites. L’icône du lanceur dans les sessions réelles, le rendu et les connexions Samba restent dans la [recette Linux](recette-linux.md).

## Profils Linux et dépannage — 13 novembre 2026

Le projet cible désormais Arch Linux, Debian et Fedora. Les profils adaptent les noms de paquets, leurs requêtes locales et les unités Samba. L’ancien marqueur de bureau est retiré. Le diagnostic et le plan d’installation passent au schéma JSON 2 ; le [guide de compatibilité](../guides/compatibilite-linux.md) décrit la migration et les limites.

Le tableau de bord propose un constat local explicite, des exemples sélectionnables et un assistant pour trois symptômes. Le terminal utilise le même moteur avec `depannage`. Les consultations asynchrones devenues obsolètes après changement de source ou fermeture sont ignorées. Les données des autres pages restent séparées.

| Contrôle local | Résultat |
| --- | --- |
| `make test` | 334 tests traités : 292 réussis, 42 ignorés (38 GTK et 4 Samba), aucun échec ni erreur. |
| `make check` | Syntaxe de 49 fichiers Python valide ; cibles locales des liens Markdown valides, sans vérification des ancres ou pages externes. |
| Démonstrations | Plan Debian et dépannage Fedora exécutés sans accès hôte ; les tests couvrent les neuf combinaisons distribution/scénario. |
| CI et recette Arch | YAML analysé avec Ruby/Psych : cinq jobs, matrice Arch/Debian/Fedora et dépendances de construction cohérentes ; syntaxe des 14 blocs shell et du modèle PKGBUILD valide. |
| Espacements | `git diff --check` réussi. |

Les tests supplémentaires couvrent les états incomplets dpkg, les erreurs RPM, les noms de services Debian, les distributions inconnues/ambiguës, les pistes inconnues de dépannage et le refus de forcer un profil fictif sur l’hôte réel. Quatre tests GTK sont ajoutés pour les profils, l’invalidation, les erreurs et la séparation des sources ; ils ne sont pas exécutés localement.

La CI est préparée pour des conteneurs Arch, Debian 13 et Fedora 44 : elle consulte leurs bases locales et exécute les suites natives sous Xvfb/D-Bus. Aucune exécution distante de ce lot n’a eu lieu. Les tests locaux simulés ne valident ni les requêtes réelles de paquets, ni systemd, ni le rendu GTK des trois cibles. Les paquets natifs Debian/RPM de SambaPilot restent à préparer. Aucune dépendance, configuration ou application installée sur la machine ; aucun commit ni push.

## Icône — 13 novembre 2026

L’option « dossier connecté » est intégrée aux ressources Python, à GTK et à la recette Arch ; voir le [guide des icônes](../guides/icones-application.md). Le lanceur installé prend le nom `io.github.sambapilot.SambaPilot.desktop` pour correspondre à l’identifiant GTK. Le modèle dans le dépôt garde son nom existant.

- `make test` : 304 tests traités, 266 réussis et 38 ignorés (GTK et Samba), aucun échec.
- `make check` : 43 fichiers Python et 93 cibles locales de liens valides dans 20 documents.
- `bash -n packaging/arch/PKGBUILD.in` et `git diff --check` : réussis.
- PNG 128 pixels inspecté visuellement ; huit tailles produites avec canal alpha, original transparent conservé.

La tentative de construction avec le backend local setuptools 58.0.4 ne constitue pas une construction valide : cette version est inférieure au minimum déclaré (61) et produit des archives `UNKNOWN` sans métadonnées correctes. Aucune dépendance installée pour contourner cette limite. L’inclusion des PNG dans un wheel valide et leur contrôle par `check_distribution.py` restent à confirmer en CI. Aucun rendu GTK, paquet Arch installé ou association de lanceur sous Linux validé localement.

## État au 9 novembre 2026

Version déclarée : `0.1.0.dev0`. La stabilisation locale est effectuée sur macOS avec Python 3.9.6, sans installation de dépendances. Les fonctionnalités d’examen et de préparation sont présentes ; l’application des changements système reste à développer.

| Vérification locale | Résultat |
| --- | --- |
| Suite complète et bilan JSON | 304 tests découverts et traités : 266 réussis, 38 ignorés, aucun échec ou erreur. |
| Tests natifs identifiés | 34 GTK et 4 Samba, désactivés localement ; aucune session native lancée. |
| Syntaxe Python | 43 fichiers analysés. |
| Documentation | 86 cibles locales de liens vérifiées dans 19 documents, sans vérification des ancres ou pages externes. |
| Workflow | YAML, quatre jobs, dépendances et syntaxe des 12 blocs shell contrôlés localement. |
| Recette Arch | Syntaxe du modèle et d’une recette générée contrôlée sans lancer makepkg. |
| Démonstrations | Diagnostic et laboratoire de sauvegarde réussis ; syntaxe de 28 blocs de commandes documentés analysée sans les exécuter. |
| Contrôles d’espacement | `git diff --check` réussi. |

Les comptes ci-dessus proviennent de la suite actuelle, pas des lots antérieurs. L’[historique](historique-validation-2026-11-09.md) conserve leurs résultats et les changements successifs.

## Fonctions et tests associés

Cette correspondance décrit les domaines testés. Elle ne constitue pas une mesure de couverture de code et ne prouve pas que tous les comportements sont couverts.

| Fonction | Tests ou contrôle existants | Frontière de validation |
| --- | --- | --- |
| Diagnostic Linux | `test_diagnostic.py`, `test_system.py` | Sondes et réponses systemd simulées ; aucune validation d’un hôte Linux réel. |
| Accès déclarés | `test_access.py`, `test_presentation.py` | Matrice fictive et informations inconnues ; aucun droit effectif certifié. |
| Inventaire, détails, recherche et catégories | `test_inspection.py`, `test_declared_shares.py` | Contenus fictifs et fichiers temporaires ; pas d’inclusions résolues ni de collecte des ACL. |
| Plans de partage et reprise après changement | `test_planning.py`, `test_file_planning.py` | Candidats et relectures vérifiés sans écriture de configuration active. |
| Rapport Markdown | `test_report_export.py` | Contenu, dates, échappement et nouveaux exports privés dans des dossiers temporaires. |
| Préparation d’installation et pare-feu | `test_setup.py`, `test_firewall.py` | Observations simulées et intentions ; aucune transaction ni règle réelle appliquée. |
| Sauvegarde/restauration | `test_backup_simulation.py` | Laboratoire jetable avec copie exacte, intégrité, refus et erreurs ; aucune sauvegarde durable. |
| GTK4 | `test_gtk_integration.py` | 34 tests préparés, ignorés localement. Leur présence ne valide pas le rendu. |
| Contrôle testparm | `test_validation.py`, `test_samba_integration.py` | Processus simulés localement ; 4 essais réels préparés et ignorés. |
| Préparation du paquet Arch | `test_arch_packaging.py` | Version, empreinte source et refus des sorties existantes ; pas de construction réelle locale. |
| Fiabilité du lanceur de tests | `test_test_runner.py` | Refus d’une suite vide/incomplète, de tests natifs absents/ignorés et de faux succès ; rapport sans écrasement. |
| Archives et paquet installé | `check_distribution.py`, `smoke_installed.py` | Contrôles préparés pour la CI ; construction et installation réelles encore en attente. |

Les tests ordinaires sont découverts depuis `tests/`. Les nouveaux fichiers ne doivent pas être exclus du prochain commit sous prétexte qu’ils sont actuellement non suivis : une réorganisation du dépôt est déjà présente dans l’arbre de travail.

## Garanties préparées dans la CI

### Échec natif observé et correction préparée

Le journal GitHub fourni par l’utilisateur montre 304 tests exécutés, dont 33 erreurs GTK. Le premier test GTK réussit, ainsi que les quatre tests Samba réels. Les 33 erreurs suivantes surviennent dans `setUp`, lors de `app.register(None)` : l’interface `org.gtk.Application` est déjà exportée au chemin `/io/github/sambapilot/Tests`. Elles empêchent les scénarios concernés de commencer et ne constituent pas 33 régressions fonctionnelles distinctes.

La préparation GTK attribue maintenant un identifiant unique à chaque application de test et enregistre ses nettoyages avec `addCleanup`, même si la préparation échoue ensuite. Les actions d’artefacts passent à `upload-artifact@v7` et `download-artifact@v8`, utilisant Node.js 24, pour traiter séparément les avertissements de dépréciation. La correction reste à confirmer par une nouvelle exécution native GitHub ; les tests locaux continuent d’ignorer les 38 tests natifs.

### Organisation du workflow

Le workflow comporte désormais cinq jobs :

1. **Python** : syntaxe, liens, démonstrations et suite sur Python 3.9, 3.12 et 3.14.
2. **Linux natif** : suite complète sous GTK4/Xvfb avec testparm réel ; le lanceur exige la présence des deux suites et refuse les tests ignorés ou échecs attendus.
3. **Profils Linux** : Arch, Debian 13 et Fedora 44, requêtes réelles de paquets et suite native stricte dans des conteneurs temporaires.
4. **Distribution Python** : après réussite des tests, sources, wheel reconstruit depuis les sources, contrôle des archives puis essais du paquet installé hors du dépôt.
5. **Arch** : archive source sélectionnée par identifiant d’artefact, empreintes et commit vérifiés, construction non privilégiée et essais dans un conteneur Arch temporaire.

Les essais du paquet installé portent sur les versions, les commandes fictives, les plans non applicables, l’examen/export Markdown et le laboratoire de sauvegarde. Le script refuse de prendre les sources du dépôt pour un paquet installé. Ces essais restent à exécuter dans les runners.

Les noms d’artefacts incluent la tentative du workflow. Le job Arch utilise l’identifiant fourni par le job Python : une relance partielle peut ainsi conserver le résultat du job déjà réussi sans chercher un fichier inexistant pour la nouvelle tentative. Cette préparation est contrôlée statiquement ; aucune relance distante n’est effectuée ici.

## Lire les preuves après un push autorisé

Dans **Actions → Vérifications SambaPilot → exécution**, examiner :

- les bilans `sambapilot-tests-python-<version>-<commit>-<tentative>` ;
- le bilan `sambapilot-tests-native-<commit>-<tentative>` ;
- les bilans `sambapilot-tests-arch-<commit>-<tentative>`, `sambapilot-tests-debian-<commit>-<tentative>` et `sambapilot-tests-fedora-<commit>-<tentative>` ;
- les archives Python et Arch des jobs effectivement réussis.

Les bilans JSON sont conservés même après un échec de tests, si le lanceur a pu s’exécuter. Un échec de préparation du runner peut ne produire aucun bilan : consulter alors les logs. Les compteurs `tests_run` suivent unittest et incluent ses tests ignorés ; `executed` les exclut. `passed` compte les méthodes sans échec ni test ignoré, y compris lorsque plusieurs sous-tests échouent dans une méthode.

Un bilan Python ordinaire `passed` avec les suites natives ignorées ne valide pas GTK ou Samba. Le bilan natif doit indiquer `native_required: true`, un statut réussi, les deux suites présentes, aucun test ignoré et aucun échec. Les traces de construction et d’installation restent nécessaires en plus des bilans de tests.

Voir le [guide de CI](verification-automatisee.md) et la [distribution Linux](../guides/distribution-linux.md).

## Validations restantes

Aucun run GitHub, paquet construit, affichage GTK natif, environnement Linux, accès réseau Samba, règle de pare-feu ou transaction pacman n’est validé pendant cette stabilisation locale. Le conditionnement local reste non exécuté : `build` est absent et setuptools disponible ne satisfait pas le minimum déclaré ; aucun outil n’est installé pour contourner cela.

Les essais GTK en CI utiliseront X11/Xvfb ; ils ne remplaceront pas la recette dans les sessions Wayland/X11 et les thèmes des trois distributions. La [recette courte](recette-linux.md) prépare ces essais sur une copie fictive lorsque l’ordinateur sera disponible.

La restauration du laboratoire est temporaire et ne comporte pas le verrouillage contre d’autres programmes, le catalogue durable ou les métadonnées nécessaires à une restauration réelle. Les signatures de paquets, la publication et l’activation de `master-archrepo` restent séparées de cette étape.

## Prochaine reprise

1. Vérifier `git status` et préparer une publication incluant la réorganisation, le code, les scripts, les tests, le conditionnement et les documents, après autorisation explicite de commit/push.
2. Après publication autorisée de la correction, examiner le nouveau run GitHub : les 38 tests GTK et les 4 tests Samba doivent tous réussir sur chaque profil avant d’annoncer la construction validée. Ne pas contourner un échec natif en ignorant les tests concernés.
3. Quand les cibles seront disponibles, effectuer la recette courte sur Arch, Debian et Fedora avec les dépendances déjà présentes ; planifier séparément toute installation nécessaire.

Aucun commit, push, déploiement, installation locale, création de signature ou activation pacman n’est réalisé dans cette stabilisation.
