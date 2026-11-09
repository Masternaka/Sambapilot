# Architecture et étapes de développement

## Décisions prises

- Nom du projet : **SambaPilot**.
- Cible initiale : l’ordinateur Omarchy à la maison.
- Deux interfaces : graphique et terminal.
- Moteur commun pour les validations, les propositions de changements et les opérations système.
- Autorisation explicite avant toute installation ou modification de la machine.

## Architecture actuelle et extensions prévues

| Élément | Responsabilité |
| --- | --- |
| Interface graphique | Afficher l’état, recueillir les choix et présenter les changements à confirmer. |
| Interface terminal | Donner accès au même moteur et aux mêmes confirmations depuis le terminal. |
| Moteur commun | Représenter les partages et les accès, vérifier les demandes et construire les opérations proposées. |
| Adaptateurs système | Isoler les interactions avec Samba, les paquets, les comptes, les permissions, les services et le pare-feu. |
| Exécution privilégiée (à développer) | Effectuer uniquement les opérations validées nécessitant des droits administrateur. |
| Sauvegarde et compte rendu (à développer) | Conserver les configurations précédentes et les résultats des opérations sans secrets. |

Les interfaces ne devront pas modifier directement le système. Le moteur séparera l’inspection de l’application des changements. L’interface graphique ne devra pas être entièrement lancée avec les droits administrateur.

La proposition de changements devra préciser son état de référence, les actions prévues, leurs effets et les possibilités de restauration. L’exécution vérifiera à nouveau les entrées et l’état courant ; elle ne devra pas accepter une commande système arbitraire fournie par une interface.

## Organisation du dépôt

Toutes les commandes se lancent depuis la racine du dépôt, à côté de `Makefile` et de `pyproject.toml`. Le dossier `sambapilot/` contient le paquet Python ; il ne faut pas s’y placer pour lancer `python3 -B -m sambapilot`.

| Fichiers | Rôle actuel |
| --- | --- |
| `sambapilot/__main__.py`, `cli.py` | Entrée du module et sept commandes terminal. |
| `diagnostic.py`, `system.py`, `demo.py` | Rapports, sondes Linux et données fictives. |
| `access.py`, `presentation.py` | Estimation des accès déclarés et modèle de présentation sans GTK. |
| `inspection.py` | Lecture bornée et inventaire des déclarations locales. |
| `planning.py`, `file_planning.py` | Candidats, comparaison, sessions et vérification de source. |
| `backup_simulation.py` | Laboratoire temporaire de sauvegarde/restauration, indépendant des configurations actives. |
| `report_export.py`, `gtk_report.py` | Rapport Markdown, enregistrement sans écrasement et aperçu GTK. |
| `validation.py` | Contrôle facultatif d’une copie privée avec `testparm`. |
| `setup.py`, `firewall.py` | Plans descriptifs d’installation et intentions réseau. |
| `gui.py`, `gtk_app.py`, `gtk_setup.py`, `gtk_firewall.py` | Chargement optionnel de GTK et interfaces graphiques. |
| `tests/` | Tests standard et intégrations GTK/Samba optionnelles. |
| `scripts/` | Syntaxe/liens, lanceur de tests avec bilan, contrôle des archives et essais d’un paquet déjà installé. |
| `.github/workflows/ci.yml` | Jobs Python, Linux natif, distribution Python et Arch, préparés mais non exécutés. |
| `packaging/arch/` | Modèle de recette makepkg et lanceur GTK4. |
| `docs/guides/` | Guides des fonctions terminal et GTK4. |
| `docs/conception/` | Exigences, architecture, feuille de route et recommandations. |
| `docs/validation/` | Bilan de validation et essais restants. |

`pyproject.toml` déclare la version `0.1.0.dev0`, Python 3.9 minimum, aucune dépendance d’exécution Python et le point d’entrée `sambapilot = sambapilot.cli:main`. Le backend de construction est setuptools ; le conditionnement n’a pas été vérifié dans cette revue.

## Choix techniques

- **Python 3.9 ou ultérieur** pour le moteur et le terminal ; bibliothèque standard uniquement pour le premier socle, avec `argparse`, `dataclasses` et `unittest`.
- **GTK 4.10 ou ultérieur avec PyGObject** pour l’interface graphique. La première fenêtre de démonstration est codée ; ses dépendances restent optionnelles et ne sont pas installées automatiquement. Le support de Wayland par GTK et ses liaisons Python permettent de garder le même moteur.
- **Sondes injectables** : le moteur reçoit un adaptateur de lecture seule. L’adaptateur Linux consulte l’hôte ; l’adaptateur de démonstration fournit des données fictives et ne consulte jamais l’hôte.
- **Rapport structuré** : les interfaces consomment le même modèle. La sortie JSON comporte un numéro de schéma pour permettre son évolution.

Le moteur actuel ne possède aucune fonction d’exécution de changements. Le diagnostic utilise des requêtes `systemctl show` sur une liste fermée d’unités. La préparation d’installation ajoute des requêtes locales pacman sur deux paquets fixes. Le contrôle testparm reste explicitement demandé et limité aux candidats pris en charge. Les états d’activité et d’activation au démarrage restent distincts.

La prise en charge des paquets, des services et du pare-feu devra être fondée sur l’environnement effectivement détecté et sur les documentations officielles à jour. Aucun gestionnaire de pare-feu ne sera supposé présent ou actif.

### Références officielles consultées

- [Omarchy : outils de développement et Python](https://omarchy.org/manual/development-tools/).
- [GTK 4 : support de Wayland](https://docs.gtk.org/gtk4/wayland.html).
- [PyGObject : interface GTK depuis Python](https://pygobject.gnome.org/getting_started.html).
- [Arch Linux : fichiers du paquet Samba, dont les unités smb et nmb](https://archlinux.org/packages/extra/x86_64/samba/files/).
- [systemd : commande systemctl et propriétés des unités](https://www.freedesktop.org/software/systemd/man/latest/systemctl.html).

## Étapes de développement

### 1. Socle et diagnostic

État : implémenté et testé avec des sondes simulées ; validation réelle Omarchy encore à effectuer.

- Choisir et documenter la pile technique.
- Créer le moteur commun et une première interface terminal en lecture seule.
- Détecter l’environnement et afficher les composants, les services et les configurations présents.
- Préparer des données fictives pour travailler sans modifier la machine.

Critère de validation : le diagnostic n’effectue aucune installation ni écriture système et explique les environnements non pris en charge.

### 2. Plans de configuration et partages

État : le modèle des accès, la matrice en démonstration et la préparation des configurations candidates sont disponibles. Le formulaire GTK et le terminal utilisent le même moteur pour créer, modifier ou retirer une déclaration sur une configuration fictive, avec comparaison et invalidation des aperçus. La collecte réelle et l’application restent à développer. Le contrôle facultatif des candidats avec `testparm` est codé ; son exécution réelle reste à vérifier. Voir le [guide de préparation](../guides/preparation-partages.md).

L’[examen d’un fichier choisi](../guides/inspection-configuration.md) est disponible dans les deux interfaces et peut alimenter un aperçu de modification sans écriture. Les sessions sur fichier relisent la source avant chaque aperçu et refusent un contenu devenu obsolète. Une reprise explicite peut relire et comparer le fichier sans perdre les champs saisis, puis adopter la source après une seconde vérification ; aucun candidat n’est généré automatiquement et aucune fusion de réglages n’est effectuée. Les sources de démonstration et de fichier choisi restent distinctes. La page Partages peut désormais présenter les déclarations du fichier choisi, leurs réglages inconnus et leur source, avec rechargement explicite et retour aux exemples. Une recherche et des filtres distinguent les réglages locaux manquants, ambigus et les options/destinataires non pris en charge. L’accès direct à la modification utilise les validations de `FilePlanSession`, sans application. Cela ne relie pas l’inventaire à la matrice fictive des accès. L’export Markdown de l’inventaire est disponible avec aperçu, dates UTC, signalement des chemins et identifiants, puis enregistrement explicite sans écrasement ; il ne constitue pas une sauvegarde de configuration. Le traitement de la configuration complète avec Samba et la collecte réelle des comptes et des ACL restent à développer.

Le [contrôle explicite des candidats avec testparm](../guides/validation-samba.md) est désormais codé pour un sous-ensemble de configurations simples. Il utilise le programme système déjà installé et une copie temporaire privée. Son fonctionnement réel avec Samba et le parcours GTK restent à vérifier ; les retours sont simulés dans les tests actuels. L’interprétation complète, la collecte des permissions effectives et l’application des changements restent à développer.

- Modéliser les partages, les utilisateurs, les groupes et les permissions.
- Développer la [vue « Qui peut accéder à quoi ? »](recommandations.md) en gardant les informations inconnues explicites.
- Préparer les configurations candidates et leur comparaison avec l’existant.
- Tester les validations, les conflits et la préservation des réglages existants sur des fichiers temporaires.

Critère de validation : un aperçu complet peut être produit et annulé sans changement de l’environnement.

### 3. Application contrôlée

Un [laboratoire de sauvegarde/restauration](../guides/simulation-sauvegarde-restauration.md) éprouve déjà la copie exacte, l’intégrité, les aperçus, les refus et la reprise sur des fichiers fictifs. Il ne fournit aucune restauration de configuration active ni stockage durable.

État : [préparation d’installation descriptive](../guides/preparation-installation.md) disponible dans les deux interfaces, avec états des paquets, étapes et points bloquants. Aucune transaction d’installation ni exécution de changement n’est encore implémentée.

La [préparation du pare-feu](../guides/preparation-pare-feu.md) produit aussi des intentions à partir des choix explicites de gestionnaire, d’interface et de sources IPv4/IPv6. La lecture des règles effectives, la traduction native et l’application restent à développer.

- Ajouter l’installation, les comptes, les permissions, les services et les adaptateurs de pare-feu pris en charge.
- Mettre en place les confirmations, les sauvegardes et la vérification de l’état avant application.
- Gérer les échecs partiels et la restauration des configurations.

Critère de validation : les opérations système sont testées dans un environnement Omarchy isolé et explicitement autorisé, y compris les refus de confirmation et les erreurs.

### 4. Interface graphique

État : première fenêtre en démonstration codée, avec navigation, tableau de bord, partages, matrice filtrable et formulaire de préparation des changements. La rubrique Installation propose des plans fictifs ou un constat local explicitement demandé. La rubrique Pare-feu propose un formulaire de périmètre déclaré et des intentions de règles. La maintenance conserve des états fictifs et présente les fonctions à venir. Les tests de présentation et de planification passent ; les essais natifs GTK et la validation visuelle restent à effectuer. Voir le [guide de l’interface graphique](../guides/interface-graphique.md).

- Construire les écrans de diagnostic, de partages, d’accès et de pare-feu.
- Réutiliser les validations et les opérations du moteur.
- Présenter les changements et les résultats de façon cohérente avec l’interface terminal.

Critère de validation : une même demande produit le même plan dans les deux interfaces, avec une utilisation possible au clavier.

### 5. Validation et distribution

Priorité de stabilisation : confirmer le premier run CI, lire les bilans de tests puis suivre la [recette Omarchy](../validation/recette-omarchy.md). Les contrôles natifs deviennent stricts et les essais du paquet installé couvrent les nouveaux parcours d’export et de simulation. Le [bilan actuel](../validation/validation-socle.md) décrit les preuves acquises et restantes.

État : workflow CI préparé avec matrice Python, tests GTK4 sous affichage virtuel et contrôles réels `testparm` optionnels. Le conditionnement est préparé avec contrôle du wheel et de l’archive source. Les jobs n’ont pas été exécutés ; voir le [guide de vérification automatisée](../validation/verification-automatisee.md).

- Vérifier les accès réels depuis un autre appareil, en lecture et en écriture, avec des comptes autorisés et non autorisés.
- Vérifier les restrictions réseau, la conservation des partages existants et la récupération après erreur.
- Documenter l’installation de SambaPilot, son utilisation, ses limites et sa désinstallation.
- Confirmer le paquet Arch préparé en CI et poursuivre vers le dépôt personnel pacman signé `Masternaka/master-archrepo`, selon le [guide de distribution](../guides/distribution-omarchy.md).

Critère de validation : distinguer dans le compte rendu les tests automatisés, les essais dans l’environnement isolé et les vérifications sur l’ordinateur cible. Toute intervention sur cet ordinateur nécessite son autorisation préalable.
