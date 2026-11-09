# Bilan de validation de SambaPilot

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
| Diagnostic Linux | `test_diagnostic.py`, `test_system.py` | Sondes et réponses systemd simulées ; aucune validation d’un hôte Omarchy réel. |
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

Le workflow comporte quatre jobs :

1. **Python** : syntaxe, liens, démonstrations et suite sur Python 3.9, 3.12 et 3.14.
2. **Linux natif** : suite complète sous GTK4/Xvfb avec testparm réel ; le lanceur exige la présence des deux suites et refuse les tests ignorés ou échecs attendus.
3. **Distribution Python** : après réussite des tests, sources, wheel reconstruit depuis les sources, contrôle des archives puis essais du paquet installé hors du dépôt.
4. **Arch** : archive source sélectionnée par identifiant d’artefact, empreintes et commit vérifiés, construction non privilégiée et essais dans un conteneur Arch temporaire.

Les essais du paquet installé portent sur les versions, les commandes fictives, les plans non applicables, l’examen/export Markdown et le laboratoire de sauvegarde. Le script refuse de prendre les sources du dépôt pour un paquet installé. Ces essais restent à exécuter dans les runners.

Les noms d’artefacts incluent la tentative du workflow. Le job Arch utilise l’identifiant fourni par le job Python : une relance partielle peut ainsi conserver le résultat du job déjà réussi sans chercher un fichier inexistant pour la nouvelle tentative. Cette préparation est contrôlée statiquement ; aucune relance distante n’est effectuée ici.

## Lire les preuves après un push autorisé

Dans **Actions → Vérifications SambaPilot → exécution**, examiner :

- les bilans `sambapilot-tests-python-<version>-<commit>-<tentative>` ;
- le bilan `sambapilot-tests-native-<commit>-<tentative>` ;
- les archives Python et Arch des jobs effectivement réussis.

Les bilans JSON sont conservés même après un échec de tests, si le lanceur a pu s’exécuter. Un échec de préparation du runner peut ne produire aucun bilan : consulter alors les logs. Les compteurs `tests_run` suivent unittest et incluent ses tests ignorés ; `executed` les exclut. `passed` compte les méthodes sans échec ni test ignoré, y compris lorsque plusieurs sous-tests échouent dans une méthode.

Un bilan Python ordinaire `passed` avec les suites natives ignorées ne valide pas GTK ou Samba. Le bilan natif doit indiquer `native_required: true`, un statut réussi, les deux suites présentes, aucun test ignoré et aucun échec. Les traces de construction et d’installation restent nécessaires en plus des bilans de tests.

Voir le [guide de CI](verification-automatisee.md) et la [distribution Omarchy](../guides/distribution-omarchy.md).

## Validations restantes

Aucun run GitHub, paquet construit, affichage GTK natif, environnement Omarchy, accès réseau Samba, règle de pare-feu ou transaction pacman n’est validé pendant cette stabilisation locale. Le conditionnement local reste non exécuté : `build` est absent et setuptools disponible ne satisfait pas le minimum déclaré ; aucun outil n’est installé pour contourner cela.

Les essais GTK en CI utiliseront X11/Xvfb ; ils ne remplaceront pas la recette Wayland/Hyprland et du thème sur Omarchy. La [recette courte](recette-omarchy.md) prépare ces essais sur une copie fictive lorsque l’ordinateur sera disponible.

La restauration du laboratoire est temporaire et ne comporte pas le verrouillage contre d’autres programmes, le catalogue durable ou les métadonnées nécessaires à une restauration réelle. Les signatures de paquets, la publication et l’activation de `master-archrepo` restent séparées de cette étape.

## Prochaine reprise

1. Vérifier `git status` et préparer une publication incluant la réorganisation, le code, les scripts, les tests, le conditionnement et les documents, après autorisation explicite de commit/push.
2. Après publication autorisée de la correction, examiner le nouveau run GitHub : les 34 tests GTK et les 4 tests Samba doivent tous réussir avant d’annoncer la construction validée. Ne pas contourner un échec natif en ignorant les tests concernés.
3. Quand Omarchy sera disponible, effectuer la recette courte avec les dépendances déjà présentes ; planifier séparément toute installation nécessaire.

Aucun commit, push, déploiement, installation locale, création de signature ou activation pacman n’est réalisé dans cette stabilisation.
