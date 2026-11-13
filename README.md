# SambaPilot

SambaPilot prépare un utilitaire de gestion des partages Samba pour **Arch Linux, Debian et Fedora**. Le terminal et l’interface graphique GTK reposent sur le même moteur Python. Les profils des trois distributions sont implémentés ; leur validation native reste à confirmer. Voir la [compatibilité Linux](docs/guides/compatibilite-linux.md).

La version actuelle, **0.1.0.dev0**, permet de diagnostiquer et de préparer des changements. Elle ne possède aucune fonction d’application : aucune installation, modification de configuration, gestion de compte, modification de permission ou ouverture de port n’est exécutée.

## État du projet

| Fonction | Disponible aujourd’hui | Limites |
| --- | --- | --- |
| Diagnostic | Rapport en lecture seule dans le terminal et le tableau de bord GTK, profils Arch/Debian/Fedora, démonstrations et JSON. | Lecture locale sur demande, sans lecture de configuration ni test de connexion. |
| Dépannage | Pistes adaptées à un partage invisible, un accès refusé ou une écriture impossible, en terminal et GTK. | Les causes non vérifiées restent explicites ; aucune réparation automatique. |
| Utilisateurs et accès | Matrice fictive en terminal et GTK, filtres et explications des conflits. | Aucun compte, groupe ou ACL réel collecté ; les droits affichés sont des estimations. |
| Examen de configuration | Inventaire d’un fichier explicitement choisi, en terminal et GTK, avec affichage de ses déclarations dans la page Partages. | Déclarations locales uniquement, sans héritage ni résolution des inclusions. |
| Préparation des partages | Ajout, modification ou retrait d’une déclaration, candidat et comparaison en mémoire. | Configuration fictive ou fichier choisi ; périmètre prudent, sans enregistrement ni application. |
| Rapport Markdown | Aperçu et enregistrement explicite de l’inventaire, depuis le terminal ou GTK. | Chemins et identifiants inclus et signalés ; pas de fichier brut ni de valeurs d’options inconnues ; aucun écrasement. |
| Contrôle Samba | Option explicite `--validate` et bouton GTK utilisant une copie temporaire privée. | Linux avec `testparm` déjà installé ; configurations simples, exécution réelle encore à vérifier. |
| Préparation d’installation | Plan descriptif fictif ou constat local, avec paquets et services propres à Arch, Debian ou Fedora. | Requêtes locales pacman, dpkg-query ou RPM ; aucune transaction calculée ni exécutée. |
| Pare-feu | Intentions SMB pour un gestionnaire, une interface et des sources déclarés. | Aucune lecture des règles existantes, commande native ou application. |
| Laboratoire de sauvegarde | Scénario de sauvegarde, comparaison et restauration dans un dossier temporaire privé. | Données fictives uniquement ; aucun accès à une configuration active ni sauvegarde durable. |
| Interface graphique | Huit rubriques GTK, formulaires et données partagées avec le terminal. | Rendu, parcours clavier et tests natifs encore à vérifier dans une session graphique. |

Les plans gardent `can_apply: false`, même après un contrôle Samba accepté. Une information inconnue reste inconnue et ne devient pas une autorisation.

## Essayer depuis les sources

**Python 3.9 ou ultérieur doit déjà être disponible.** Le moteur et le terminal n’ont aucune dépendance Python externe. Toutes les commandes suivantes se lancent depuis la **racine du dépôt**, à côté de `Makefile` et de `pyproject.toml`.

```sh
python3 -B -m sambapilot --version
python3 -B -m sambapilot --help
python3 -B -m sambapilot diagnostic --demo
python3 -B -m sambapilot diagnostic --demo --distribution debian
python3 -B -m sambapilot depannage --demo --distribution fedora --symptom readonly
python3 -B -m sambapilot permissions --demo
```

Le dossier `sambapilot/` est le paquet Python : rester à la racine pour lancer ces commandes. Aucune installation du projet n’est nécessaire. L’option `-B` évite de créer des caches Python.

Les scénarios `fresh`, `configured` et `restricted` sont fictifs et ne consultent pas la machine. `--demo` sans scénario choisit `configured` pour le diagnostic et le dépannage, et `fresh` pour la préparation d’installation. `--distribution arch|debian|fedora` choisit le profil fictif et exige `--demo`. Les sept commandes terminal de rapport ou de plan acceptent `--json`.

```sh
python3 -B -m sambapilot diagnostic --demo restricted --json
python3 -B -m sambapilot preparer-installation --demo fresh
python3 -B -m sambapilot plan-partage --demo --action create --name Documents --path /srv/partages/documents --user alex
python3 -B -m sambapilot plan-pare-feu --manager ufw --interface enp3s0 --source 192.168.1.0/24
```

L’interface et le réseau de cet exemple sont à adapter ; leur existence n’est pas vérifiée et aucun port n’est ouvert.

Pour l’interface graphique, GTK **4.10 ou ultérieur** et PyGObject doivent déjà être accessibles à l’interpréteur Python utilisé :

```sh
python3 -B -m sambapilot gui --demo
```

GTK est optionnel et n’est chargé que par cette commande. Le drapeau `--demo` est obligatoire ; les lectures d’un fichier choisi ou du constat local se demandent ensuite explicitement dans leur rubrique. Aucune dépendance manquante n’est installée automatiquement.

## Examiner des données locales

Les commandes suivantes consultent l’hôte ou un fichier choisi, sans appliquer de réglage :

```sh
python3 -B -m sambapilot diagnostic
python3 -B -m sambapilot depannage --local --symptom invisible
python3 -B -m sambapilot preparer-installation --local
python3 -B -m sambapilot examiner-config --config /chemin/vers/smb.conf
```

Le diagnostic local est réservé à Linux. Il consulte l’identification de distribution, les métadonnées de `/etc/samba/smb.conf`, les exécutables système et des propriétés systemd. Les unités Samba dépendent du profil détecté. Il ne lit pas le contenu de `smb.conf`, ne demande pas `sudo` et ne lance aucun outil de pare-feu. Hors Linux, il produit un rapport non pris en charge sans poursuivre les sondes. Le [dépannage](docs/guides/diagnostic-depannage.md) réutilise ce constat sans sonde supplémentaire.

La préparation locale d’installation ajoute des requêtes sur une liste fermée de paquets, avec `pacman --query` sur Arch, `dpkg-query --show` sur Debian ou `rpm --query` sur Fedora. Elle ne télécharge aucun paquet. Un service actif ou un outil présent ne prouve pas que Samba fonctionne ni qu’un pare-feu limite les accès.

L’examen de configuration lit uniquement le fichier régulier UTF-8 choisi, limité à 1 Mio. Pour préparer un partage à partir de ce fichier, remplacer `--demo` par `--config /chemin/vers/smb.conf` dans `plan-partage`. La source est relue avant l’aperçu pour refuser un contenu devenu obsolète. Dans GTK, la page **Partages** permet de choisir une configuration, de consulter ses déclarations et réglages inconnus, de rechercher par nom ou chemin et de filtrer les incertitudes, puis de revenir aux exemples. Chaque déclaration propose des explications et, lorsque le moteur la prend en charge, un accès direct à la préparation d’une modification. Le bouton **Recharger le fichier** actualise cette lecture ponctuelle ; les droits effectifs et la matrice des accès restent séparés de cet inventaire. Dans le formulaire de préparation, **Recharger sans perdre ma saisie** propose une comparaison puis une adoption explicite de la nouvelle source, avant de régénérer l’aperçu.

L’option `--validate` demande séparément le contrôle du candidat avec `testparm` déjà installé sur Linux. Elle crée puis nettoie une copie temporaire privée et ne remplace jamais la configuration source. Le JSON d’un plan contient le candidat complet ; l’inventaire n’exporte pas les valeurs des options inconnues.

Le [guide d’export Markdown](docs/guides/export-rapport.md) décrit l’aperçu, les informations personnelles incluses et l’enregistrement explicite du rapport sans écrasement.

## Codes de sortie

| Commande | Codes |
| --- | --- |
| `diagnostic` | `0` : rapport Linux ou démonstration produit ; `2` : hors Linux ou arguments invalides. |
| `depannage` | `0` : pistes produites ; `2` : hors Linux ou arguments invalides. Un code `0` ne certifie pas la cause. |
| `permissions` | `0` : matrice fictive produite ; `2` : arguments invalides, dont absence de `--demo`. |
| `examiner-config` | `0` : inventaire produit, et export enregistré si demandé ; `2` : lecture impossible, structure bloquée, arguments invalides ou erreur d’export. |
| `plan-partage` | `0` : aperçu produit, et contrôle accepté si demandé ; `2` : préparation impossible ; `4` : contrôle demandé non accepté ou indisponible. |
| `preparer-installation` | `0` : plan descriptif à examiner ; `2` : plan bloqué ou arguments invalides. |
| `plan-pare-feu` | `0` : intentions produites ; `2` : demande invalide. |
| `gui` | `3` : dépendances ou session GTK indisponibles ; `2` : arguments invalides. |

Un code `0` ne certifie ni une installation réussie ni un accès effectif à Samba.

## Développement et vérification

Depuis la racine, avec Python et `make` déjà disponibles :

```sh
make test
make check
make demo
```

Au **13 novembre 2026**, sur macOS : **296 tests réussis et 42 tests natifs ignorés** (338 découverts : 38 GTK et 4 Samba ignorés). Les tests ordinaires utilisent des sondes simulées et des fichiers temporaires ; ils ne nécessitent ni Samba, ni systemd, ni droits administrateur. Le [bilan actuel](docs/validation/validation-socle.md) précise les autres contrôles et leurs limites.

Un workflow GitHub Actions prépare les vérifications Python, GTK4, Samba et distribution. Après chaque push et réussite des contrôles, il construit les archives Python puis le paquet Arch `.pkg.tar.zst` et les conserve comme artefacts pendant 30 jours. La version modifiée du workflow n’a pas été exécutée pendant cette intervention ; le conditionnement et les essais natifs restent à valider. Les essais Linux, pare-feu et connexion depuis un autre appareil restent également à effectuer. Voir le [bilan de validation](docs/validation/validation-socle.md).

Les cibles `make test-gtk`, `make test-samba`, `make test-native` et `make check-dist` sont décrites dans le [guide de vérification automatisée](docs/validation/verification-automatisee.md). Elles n’installent aucune dépendance ; les tests natifs restent désactivés par défaut.

Le [guide de distribution Linux](docs/guides/distribution-linux.md) explique où télécharger ces fichiers dans GitHub Actions et comment évoluer vers **Masternaka/master-archrepo**, le dépôt personnel Arch/pacman retenu pour installer et mettre à jour plusieurs applications sur Linux. Aucun dépôt pacman, signature ou canal stable n’est encore publié.

Le [laboratoire de sauvegarde/restauration](docs/guides/simulation-sauvegarde-restauration.md), disponible avec `make demo-backup`, teste les garanties de copie et de reprise uniquement sur des configurations fictives dans un dossier temporaire.

La [recette courte Linux](docs/validation/recette-linux.md) prépare les essais futurs sur une copie fictive. Le [bilan actuel](docs/validation/validation-socle.md) distingue les fonctions testées ici des validations natives et des constructions encore attendues. La priorité est de confirmer un run CI réussi pour ce lot avant d’ajouter d’autres fonctions d’application système.

## Suite du projet et autorisation

L’application contrôlée des changements, la gestion réelle des comptes et permissions, les sauvegardes, la restauration et les tests réseau restent à développer. Toute future intervention devra examiner l’état courant, présenter les changements concrets, obtenir une confirmation explicite, sauvegarder les réglages concernés, appliquer puis vérifier le résultat.

La modification de ce dépôt n’autorise aucune installation ni modification de l’environnement de l’ordinateur. Le [guide des assistants](AGENTS.md) précise cette règle.

## Organisation du dépôt

```text
Sambapilot/
├── .github/           # Consignes et workflow de vérification GitHub
├── docs/
│   ├── README.md      # Index de la documentation
│   ├── guides/        # Utilisation du terminal et de GTK4
│   ├── conception/    # Exigences, architecture et feuille de route
│   └── validation/    # Vérifications réalisées et limites
├── sambapilot/        # Moteur Python, terminal et interface GTK4
├── tests/             # Tests ordinaires et intégrations GTK/Samba optionnelles
├── scripts/           # Contrôles et préparation de la recette Arch
├── packaging/arch/    # Modèle PKGBUILD et lanceur GTK4
├── AGENTS.md          # Consignes pour les assistants
├── Makefile           # Vérifications et démonstration
├── MANIFEST.in        # Fichiers inclus dans la distribution source
├── pyproject.toml     # Métadonnées et conditionnement Python
└── README.md
```

Le paquet reste directement dans `sambapilot/` pour permettre le lancement depuis les sources sans installation. L’interface graphique retenue reste GTK4.

## Documentation

L’[index de la documentation](docs/README.md) regroupe les guides d’utilisation, le cahier des charges, l’architecture, la feuille de route et les vérifications réalisées.
