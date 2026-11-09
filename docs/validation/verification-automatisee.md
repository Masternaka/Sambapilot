# Vérifications automatisées Linux, GTK4 et distribution

## Objectif et état

La CI et les essais natifs sont préparés pour faire avancer SambaPilot sans nécessiter immédiatement un ordinateur Omarchy disponible. Le workflow [ci.yml](../../.github/workflows/ci.yml) contient quatre jobs. Sa présence dans le dépôt ne signifie pas qu’il a été exécuté : aucune publication ni exécution distante n’a eu lieu pendant cette préparation.

| Job | Vérifications prévues |
| --- | --- |
| Python | Syntaxe, liens locaux, tests ordinaires, bilans JSON et démonstrations sous Python 3.9, 3.12 et 3.14 sur Ubuntu 24.04. |
| Linux natif | Tests ordinaires, 34 tests GTK activés sous Xvfb et 4 tests avec le vrai `testparm`, avec le Python système Ubuntu et un contrôle strict refusant les tests natifs ignorés. |
| Distribution | Après réussite des tests : sources, wheel reconstruit depuis ces sources, contenu des archives, installation temporaire et commandes, export et simulation lancés hors du dépôt ; fichiers conservés comme artefact. |
| Arch | Construction depuis l’archive source vérifiée, tests et installation dans un conteneur Arch temporaire, puis conservation du paquet `.pkg.tar.zst`. |

Le workflow est prévu pour les push, pull requests et lancements manuels, après sa publication autorisée. Il conserve les constructions réussies comme artefacts GitHub pendant 30 jours, sans créer de release ni alimenter un dépôt pacman. Son accès au contenu du dépôt reste en lecture seule. Le [guide de distribution Omarchy](../guides/distribution-omarchy.md) décrit les fichiers obtenus et la préparation du futur dépôt personnel.

## Effets limités aux runners GitHub

Le job natif installe GTK4, PyGObject, Xvfb, les outils de session D-Bus et `samba-common-bin` sur le runner temporaire. Il prépare également les dossiers Samba par défaut `/run/samba`, `/var/lib/samba` et `/var/cache/samba` pour permettre le contrôle de configuration sans installer ni démarrer le serveur Samba.

Le job distribution installe les outils de construction Python sur son runner et SambaPilot dans un environnement virtuel situé dans son dossier temporaire. Le job Arch met à jour son conteneur, installe les outils et dépendances, crée un compte temporaire de construction et installe le paquet construit dans ce conteneur pour vérifier les commandes. Aucun de ces jobs n’intervient sur l’ordinateur de l’utilisateur.

Ces commandes d’installation ne sont pas des instructions à appliquer localement. Toute installation locale doit recevoir l’autorisation distincte prévue par AGENTS.

## Vérifications locales sans installation

Avec Python et make déjà disponibles, depuis la racine :

```sh
make check
make test
make demo
```

`make check` analyse la syntaxe des fichiers Python de `sambapilot/`, `tests/` et `scripts/`. Il vérifie aussi l’existence et le confinement dans le dépôt des cibles de liens Markdown du README, d’AGENTS et des documents dans `docs/`. Il ne vérifie ni les ancres ni le contenu des pages externes. Aucun module applicatif n’est importé par ce contrôle.

`make test` utilise `scripts/run_tests.py` et ignore par défaut les tests natifs GTK et Samba. Tout autre test ignoré fait échouer ce lanceur. `make test-native` active les deux suites, exige qu’elles soient présentes et refuse les tests ignorés ou échecs attendus. Le compteur est découvert dynamiquement, sans nombre de tests fixé dans le workflow. Les 4 nouveaux tests Samba sont activés uniquement avec `SAMBAPILOT_SAMBA_TESTS=1`. Lorsqu’ils sont demandés, un outil absent ou une plateforme inadaptée produit une erreur : le test ne peut pas être déclaré réussi ou ignoré silencieusement.

## Bilans et essais du paquet installé

Le lanceur accepte `--report /chemin/vers/nouveau-bilan.json` dans un dossier déjà existant et refuse d’écraser un fichier. Il décrit le statut, les tests découverts, les méthodes réussies ou ignorées et les suites natives présentes. Les règles du lanceur sont testées, notamment une suite vide/incomplète, une suite native absente et plusieurs sous-tests en échec.

La CI conserve un bilan par version de Python et un bilan natif, même si les tests échouent. Si la préparation du runner échoue avant le lanceur, le bilan peut manquer : les logs restent nécessaires. Ces bilans ne contiennent pas le contenu des fichiers de test ni les clés ou réglages de la machine.

`scripts/smoke_installed.py` est réservé à un paquet déjà installé dans le runner ou conteneur autorisé. Il refuse les sources du dépôt, compare les versions, exécute le point d’entrée installé et les commandes fictives, puis contrôle l’export Markdown et le laboratoire de sauvegarde sur des données temporaires. Il ne constitue pas un essai graphique du paquet installé.

Les artefacts de construction sont nommés par commit et tentative. Le job Python expose l’identifiant de son artefact et le job Arch le télécharge précisément, y compris lors d’une relance partielle conservant les sorties d’un job déjà réussi. Aucun de ces transferts n’est testé à distance pendant cette préparation.

Voir le [bilan actuel](validation-socle.md) et la [recette Omarchy](recette-omarchy.md).

## Tests natifs optionnels

Sur Linux, avec les dépendances déjà disponibles et l’environnement prêt :

```sh
make test-samba
make test-gtk
```

Le contrôle Samba utilise uniquement des configurations fictives et des fichiers temporaires. Il vérifie l’acceptation d’une création, d’une modification, d’un retrait et d’une configuration minimale, la préservation d’un fichier source et le contrat JSON du terminal. Les répertoires et comptes déclarés ne sont pas créés. Aucun service n’est démarré ou rechargé, aucun port ouvert et aucun partage appliqué.

Le programme `testparm` peut tenir compte de chemins et de valeurs compilés dans Samba. Ses répertoires système par défaut doivent donc déjà exister dans l’environnement de test. Un refus de ce programme reste un échec à examiner ; ces tests ne créent pas ces répertoires localement pour contourner l’erreur.

Les tests GTK demandent une session graphique accessible. En CI, Xvfb fournit un affichage X11 virtuel avec un rendu logiciel ; cela ne valide pas Wayland, Hyprland, le thème Omarchy, les interactions visuelles ou l’accessibilité complète.

## Vérification de distribution

[MANIFEST.in](../../MANIFEST.in) inclut le code, les tests, les scripts, les documents, les modèles de paquet Arch et les fichiers de développement nécessaires dans l’archive source. Le wheel reste limité au paquet Python et à ses métadonnées.

Avec les outils de construction déjà installés et leur utilisation autorisée, `python3 -B -m build --no-isolation` produit les archives dans `dist/`, puis :

```sh
make check-dist
```

Cette dernière commande lit les archives sans les extraire ni installer le paquet. Elle contrôle le point d’entrée, l’absence de dépendances d’exécution et la présence du code attendu ; elle compare aussi les fichiers de l’archive source au dépôt. Utiliser un dossier de sortie sans anciennes versions, car une seule archive de chaque type est acceptée.

La construction locale n’a pas été exécutée : setuptools 58.0.4 est disponible sur la machine de développement, alors que le projet exige au moins 61, et le module `build` est absent. Aucun outil n’a été installé ou mis à jour pour contourner cette limite. La vérification complète du conditionnement reste donc en attente du job CI.

## Première reprise sur Omarchy

Après une exécution CI réussie, vérifier dans une session Omarchy autorisée le lancement GTK4 sous Wayland, les formulaires, la sélection de fichiers et les retours réels des sondes en lecture seule. La gestion des comptes, ACL, services et pare-feu ainsi que les accès depuis un autre appareil restent des validations distinctes.

Références utilisées pour préparer le workflow : [setup-python](https://github.com/actions/setup-python/tree/v6), [checkout](https://github.com/actions/checkout/tree/v5), [GTK4 dans Ubuntu 24.04](https://packages.ubuntu.com/noble/gir1.2-gtk-4.0), [outils Samba](https://packages.ubuntu.com/noble/samba-common-bin), [construction Python](https://build.pypa.io/en/stable/explanation/how-it-works.html) et [contenu des distributions setuptools](https://setuptools.pypa.io/en/latest/userguide/miscellaneous.html).

Références pour les relances : [sorties conservées des jobs non relancés](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs), [téléchargement par identifiant](https://github.com/actions/download-artifact/blob/v4/action.yml) et [sortie artifact-id](https://github.com/actions/upload-artifact/blob/v4/action.yml).
