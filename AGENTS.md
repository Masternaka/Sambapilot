# Guide pour les assistants IA

## Règle impérative : autorisation préalable

**Ne jamais rien installer ni rien modifier sur l’ordinateur de l’utilisateur sans son autorisation explicite préalable pour l’intervention concernée.**

- Une demande de modification de fichiers dans ce dépôt autorise uniquement les changements nécessaires à cette demande dans le dépôt. Elle n’autorise pas leur application à l’ordinateur.
- Avant toute installation ou modification de l’environnement de la machine, expliquer précisément l’action proposée, les fichiers ou réglages concernés et ses effets, puis attendre l’autorisation explicite de l’utilisateur.
- Cette règle couvre notamment l’installation, la mise à jour et la suppression de logiciels ou de dépendances, la copie de configurations hors du dépôt, la création de liens symboliques, ainsi que la modification des dotfiles actifs, des services et des paramètres système.
- Ne pas exécuter un script d’installation, de configuration, de maintenance ou un utilitaire susceptible de modifier la machine sans cette autorisation, même si ce script se trouve dans le dépôt ou si son exécution est présentée comme un test.
- Ne jamais considérer une proposition, une absence de réponse ou une autorisation donnée pour une autre intervention comme un accord.

## Périmètre actuel du projet

SambaPilot est un utilitaire Python destiné à Omarchy, avec une interface terminal et une interface GTK4 optionnelle utilisant le même moteur. GTK4 reste le choix retenu pour poursuivre le développement graphique. La version déclarée est `0.1.0.dev0` et le minimum Python est 3.9.

Le code actuel fournit des diagnostics, des lectures de fichiers choisis et des plans descriptifs. Il ne contient aucune application de changements système. Ne pas présenter une préparation d’installation comme un installateur ni une intention de pare-feu comme une règle appliquée. Tous les plans conservent `can_apply: false`.

## Organisation et commandes

Travailler depuis la racine du dépôt :

- `sambapilot/` : paquet Python, moteur, terminal et interfaces GTK.
- `tests/` : tests `unittest`, avec intégrations GTK et Samba optionnelles.
- `scripts/` : contrôles sans installation, dont syntaxe, liens Markdown et archives Python.
- `.github/workflows/ci.yml` : CI Python, Linux natif, distribution Python et paquet Arch ; installations uniquement sur les runners et conteneurs temporaires.
- `packaging/arch/` : modèle PKGBUILD et lanceur de démonstration. Le générateur dans `scripts/` prépare une recette avec empreinte réelle et refuse les sorties existantes.
- `docs/` : documentation française ; commencer par [l’index](docs/README.md).
  - `guides/` : utilisation du terminal et de GTK.
  - `conception/` : exigences, architecture et recommandations.
  - `validation/` : résultats datés et limites des vérifications.
- `Makefile` : commandes locales de test, de syntaxe et de démonstration.
- `pyproject.toml` : métadonnées et conditionnement setuptools, sans dépendance Python d’exécution.

Ne pas faire `cd sambapilot` pour lancer l’application. Utiliser depuis la racine :

```sh
python3 -B -m sambapilot diagnostic --demo
python3 -B -m sambapilot permissions --demo
make test
make check
make demo
```

Ces vérifications n’installent aucune dépendance et n’appliquent aucun réglage système. Les tests créent et nettoient des fichiers temporaires de travail. Examiner les commandes avant de les exécuter ; la règle d’autorisation préalable reste applicable aux scripts qui changeraient l’environnement.

Les tests GTK sont ignorés par défaut. Leur activation, avec des dépendances déjà disponibles et une session graphique accessible, est décrite dans [le guide GTK](docs/guides/interface-graphique.md). Ne pas installer GTK, PyGObject ou Samba pour débloquer un test sans autorisation explicite.

## Conventions de développement

- Rédiger les explications et la documentation en français.
- Garder le moteur et le terminal indépendants de GTK ; charger `gi` uniquement lors du lancement graphique.
- Réutiliser les validations du moteur dans les deux interfaces.
- Séparer les données fictives, le fichier choisi et le constat local ; ne jamais consulter l’hôte implicitement dans une démonstration.
- Préserver les réglages, les commentaires, les fins de ligne et le BOM pris en charge lors de la construction d’un candidat. Refuser les cas complexes plutôt que deviner ou remplacer des réglages.
- Invalider les aperçus et contrôles après un changement de formulaire ou de source ; vérifier l’empreinte du fichier aux étapes prévues.
- Garder les informations inconnues explicites (`None`/`null`), distinctes d’un refus. Distinguer règles Samba, permissions de fichiers et accès réseau réel.
- Pour les sondes, conserver les listes fermées de programmes, arguments et unités, `shell=False`, les délais et l’absence de `sudo` ou de saisie interactive.
- Ne lancer `testparm` que sur demande explicite, sur une copie temporaire privée et dans le périmètre reconnu. Une acceptation ne rend pas le plan applicable.
- Ne pas ajouter de secrets, de configurations personnelles, de sauvegardes réelles ou de mots de passe dans le dépôt, les journaux ou les arguments de processus.
- Préserver les modifications déjà présentes dans l’arbre de travail ; ne pas annuler une réorganisation ou des changements de l’utilisateur.
- Ne pas créer de commit ni publier sur GitHub sans demande explicite.

## Rangement du dépôt

Conserver les fichiers d’entrée et de configuration à la racine (`README.md`, `AGENTS.md`, `Makefile`, `pyproject.toml`). Placer le code dans `sambapilot/`, les tests dans `tests/` et les nouveaux documents dans la rubrique correspondante de `docs/`, puis actualiser son index. Éviter les copies de documentation et les dossiers vides créés pour des fonctions futures.

Ne supprimer que les artefacts identifiés comme générés ou inutiles, après examen des références. Conserver les données, les sauvegardes, les tests et les fichiers nécessaires au conditionnement. Les caches et sorties de construction restent ignorés par Git.

## Documentation et compte rendu

Mettre à jour les guides concernés lorsqu’une fonction ou une commande change. Le [README](README.md) décrit le périmètre disponible ; le [cahier des charges](docs/conception/cahier-des-charges.md) décrit la cible ; la [feuille de route](docs/conception/architecture-et-roadmap.md) distingue les étapes livrées des travaux restants.

Rapporter les résultats réels des commandes, en distinguant les tests réussis des tests ignorés. `make check` vérifie la syntaxe Python et les cibles locales des liens Markdown ; il ne vérifie pas les ancres ou les pages externes. Des processus simulés ne valident pas systemd, pacman ou `testparm` sur la cible ; les tests ordinaires ne prouvent pas le rendu GTK, les ACL, les règles de pare-feu ou une connexion Samba. Consigner les limites dans le [bilan de validation](docs/validation/validation-socle.md).

Les tests Samba réels exigent `SAMBAPILOT_SAMBA_TESTS=1` (`make test-samba`) et Linux avec `testparm` déjà disponible. Ne pas les activer implicitement en local. Voir le [guide CI et distribution](docs/validation/verification-automatisee.md) pour les effets des jobs et les limites de validation.

Les constructions réussies peuvent être conservées comme artefacts GitHub, sans release ni publication pacman automatique. Le futur dépôt personnel est `Masternaka/master-archrepo`, avec la section pacman `master-archrepo`. Il doit utiliser les paquets Arch, des signatures et un hébergement durable ; ne pas activer de dépôt ni importer de clé sur la machine sans autorisation explicite. Ne pas attribuer une licence au projet sans décision de l’utilisateur. Voir le [guide de distribution](docs/guides/distribution-omarchy.md).

L’export Markdown est une écriture de document sur demande explicite, distincte d’une application de configuration système. Ne pas exporter automatiquement, remplacer un fichier existant ou inclure le fichier brut/candidat. Signaler les chemins et identifiants inclus, préserver les dates de lecture et invalider les aperçus lors d’un changement de source. Voir le [guide d’export](docs/guides/export-rapport.md).

Le laboratoire `backup_simulation.py` et `make demo-backup` utilisent exclusivement leur propre dossier temporaire et les données fictives. Ne pas ajouter de chemin de configuration réelle ou de restauration système à ce laboratoire. Ses sauvegardes jetables ne sont pas des sauvegardes utilisateur durables ; voir le [guide de simulation](docs/guides/simulation-sauvegarde-restauration.md).

Pour la stabilisation, conserver le [bilan actuel](docs/validation/validation-socle.md) distinct de l’historique des lots. `make test` utilise le lanceur contrôlant les tests ignorés ; `make test-native` exige GTK et Samba sans ignorer de tests. Les essais de `smoke_installed.py` portent sur un paquet déjà installé dans un environnement autorisé et ne doivent pas être présentés comme exécutés localement sans preuve. La [recette Omarchy](docs/validation/recette-omarchy.md) prépare les validations manuelles restantes.
