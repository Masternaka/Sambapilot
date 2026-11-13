# Distribution Python et paquet Arch Linux

## Ce qui est préparé

Le workflow [ci.yml](../../.github/workflows/ci.yml) s’exécute après chaque push, sur les pull requests et sur lancement manuel. Après réussite des tests Python et Linux natifs, il construit les archives Python puis un paquet natif Arch Linux. Les archives Python sont communes à Arch, Debian et Fedora. Aucun paquet natif `.deb` ou `.rpm` de SambaPilot n’est encore préparé ; voir les [profils Linux](compatibilite-linux.md).

Il reste à publier ces changements et à observer une première exécution réussie. Aucune construction Arch, installation sur Linux, publication de release ou création de dépôt de paquets n’a été réalisée pendant cette préparation locale.

## Fichiers disponibles après un run réussi

Dans GitHub : ouvrir le dépôt, **Actions**, puis l’exécution **Vérifications SambaPilot**. La section **Artifacts** propose :

| Artefact | Contenu |
| --- | --- |
| `sambapilot-python-<commit>-<tentative>` | Wheel `.whl`, sources `.tar.gz`, `COMMIT.txt` et `SHA256SUMS`. |
| `sambapilot-arch-<commit>-<tentative>` | Paquet `.pkg.tar.zst`, recette `PKGBUILD`, `COMMIT.txt` et `SHA256SUMS`. |

La conservation demandée est de 30 jours, dans les limites des réglages GitHub. Ces fichiers sont des constructions de développement, pas un canal stable de mise à jour. Une pull request produit également des artefacts si tous les contrôles réussissent ; leur présence ne signifie pas que le code a été accepté ou publié en version stable.

Les noms incluent la tentative pour éviter les collisions lors des relances. Les bilans de tests sont téléchargeables séparément ; voir le [bilan de validation](../validation/validation-socle.md).

Les empreintes détectent une différence de contenu. Elles ne constituent pas des signatures de confiance : les paquets de développement ne sont pas signés.

Le job de distribution Python attend la réussite de la matrice Python, des tests natifs Ubuntu et des profils Arch, Debian et Fedora. Le job Arch utilise l’archive source sélectionnée par l’identifiant renvoyé par le job Python du même run, vérifie ses empreintes et le commit déclaré avant de construire. Si un contrôle échoue ou si le run est annulé, les étapes dépendantes ne sont pas exécutées. Un artefact Python déjà produit peut rester disponible même si la construction Arch échoue ensuite ; vérifier le résultat du job correspondant.

## Composition du paquet Arch

La recette est préparée depuis [PKGBUILD.in](../../packaging/arch/PKGBUILD.in) par [prepare_arch_build.py](../../scripts/prepare_arch_build.py). Le générateur ne construit et n’installe rien : il copie l’archive choisie dans un nouveau dossier et produit une recette contenant sa véritable empreinte SHA-256. Les dossiers existants sont refusés.

Le paquet inclut :

- le module Python et la commande `sambapilot` ;
- le [lanceur d’application](../../packaging/arch/sambapilot.desktop), qui ouvre explicitement `sambapilot gui --demo`, et les [icônes PNG](icones-application.md) destinées au thème hicolor ;
- des dépendances déclarées vers Python, GTK4 à partir de 4.10 et PyGObject.

Samba est une dépendance optionnelle pour le contrôle explicite avec `testparm`. L’installation de SambaPilot ne crée aucun partage, ne modifie aucun compte, ne configure aucun pare-feu et n’active aucun service. La préparation actuelle de l’application reste descriptive.

La version suit `__version__` dans le projet. Pour les constructions GitHub, `pkgrel` utilise le numéro d’exécution du workflow : plusieurs push pour la même version peuvent ainsi produire des révisions Arch différentes. Ce numéro reste propre à ce workflow ; un futur canal stable devra définir une politique de versions et de révisions indépendante, en évitant les retours vers une révision inférieure pour une même version.

Le conteneur `archlinux:base-devel` est mis à jour et reçoit ses dépendances de construction. `makepkg` est lancé avec un utilisateur non administrateur. Le paquet est ensuite installé et ses commandes de démonstration vérifiées uniquement dans ce conteneur temporaire. Aucun accès à la machine Linux personnelle n’est nécessaire pour cette CI.

La première exécution devra confirmer ces étapes. Le conteneur Arch est évolutif ; la recette et les empreintes ne garantissent pas une construction identique dans le temps.

## Futur dépôt personnel Arch uniquement : master-archrepo

Le dépôt GitHub cible est **Masternaka/master-archrepo** : [adresse prévue](https://github.com/Masternaka/master-archrepo). Son nom est fixé par l’utilisateur ; son existence, son hébergement et son contenu ne sont pas vérifiés dans cette préparation. Le nom de la section pacman sera également `master-archrepo`.

L’objectif est de l’ajouter une fois à un ordinateur Arch Linux, avec sa clé de signature vérifiée, puis d’installer et de mettre à jour les applications personnelles avec pacman. Chaque nouvelle application disposera de son propre paquet, sans nécessiter une nouvelle configuration de dépôt sur l’ordinateur.

Le parcours cible est le suivant :

1. Développer une application dans son dépôt GitHub.
2. Construire et tester son paquet Arch dans GitHub Actions.
3. Retenir une version pour diffusion, la signer et l’ajouter à `master-archrepo`.
4. Mettre à jour et signer la base pacman, puis publier un ensemble cohérent de fichiers sur une adresse HTTPS durable.
5. Laisser pacman installer l’application ou proposer sa nouvelle version sur Arch Linux.

Les push de développement construisent actuellement des artefacts temporaires. La sélection des versions et leur transfert vers `master-archrepo` restent à implémenter ; aucun transfert automatique entre dépôts n’est actif. Les versions publiées devront être croissantes selon les règles de pacman.

## Utilisation prévue sur Arch Linux uniquement

Les commandes suivantes illustrent le résultat attendu **après** publication du dépôt, validation des signatures et configuration autorisée de la machine. Elles ne sont pas exécutées pendant cette préparation.

Pour installer SambaPilot depuis le dépôt personnel et mettre le système à jour :

```sh
sudo pacman -Syu master-archrepo/sambapilot
```

Pour mettre à jour le système et les applications personnelles déjà installées :

```sh
sudo pacman -Syu
```

Cette deuxième commande concerne tous les dépôts configurés et les paquets installés, pas uniquement SambaPilot. Elle ne s’exécute pas toute seule : la configuration du dépôt n’ajoute aucun service ou planificateur de mises à jour automatiques. La compatibilité avec le parcours de mise à jour propre à la version Arch Linux utilisée sera vérifiée sur la cible.

L’intégration initiale devra présenter l’URL de distribution réelle, l’empreinte de la clé et les modifications exactes de configuration. Elle sauvegardera les fichiers concernés et documentera le retrait du dépôt. Aucun exemple avec une URL fictive n’est présenté comme prêt à appliquer dans `/etc/pacman.conf`.

## Répartition entre les projets

Le dépôt de paquets est distinct des dépôts de code des applications :

| Élément | Responsabilité |
| --- | --- |
| Dépôt de chaque application | Sources, tests et construction du paquet Arch. |
| `Masternaka/master-archrepo` | Sélection des versions publiées, signatures, base pacman et catalogue des applications personnelles. |
| Hébergement HTTPS | Distribution durable des paquets et de la base du dépôt. |
| Ordinateur Arch Linux | Configuration explicite de la confiance et du dépôt, puis installation avec pacman. |

Ce sera un dépôt **Arch/pacman**, réservé aux cibles Arch ; Debian et Fedora utilisent leurs propres formats et gestionnaires. Les artefacts GitHub temporaires serviront aux essais ; un hébergement durable devra conserver les fichiers des versions publiées et fournir une adresse stable.

## Étapes restantes pour le dépôt personnel

1. Obtenir une première construction CI réussie et vérifier le paquet sur un environnement Arch Linux autorisé, y compris sa désinstallation.
2. Définir la licence du projet : aucun fichier de licence n’est actuellement présent et aucune licence n’est inventée dans la recette. Ce choix reste à faire avant une distribution publique.
3. Créer ou préparer `Masternaka/master-archrepo`, choisir son hébergement HTTPS durable et définir une politique de versions stables et de versions d’essai. Le nom du dépôt est déjà choisi.
4. Mettre en place la signature des paquets et de la base pacman, avec une clé conservée hors des sources. Ne jamais partager une clé privée dans le chat ou le dépôt.
5. Construire la base avec `repo-add`, vérifier ses signatures et sa cohérence avec les paquets, puis publier les versions retenues dans le canal associé à `master-archrepo`.
6. Documenter la configuration de pacman, l’import de la clé, l’installation, les mises à jour et la suppression du dépôt. Chaque application garde sa provenance et ses dépendances propres.

Le dépôt pourra alors distribuer plusieurs applications personnelles. Cette préparation ne crée pas ce dépôt et ne modifie pas `/etc/pacman.conf` ni le trousseau de clés d’une machine. L’autorisation de préparer des fichiers dans SambaPilot ne vaut pas autorisation d’activer ce futur dépôt sur Arch Linux.

## Prochaine reprise

Publier les modifications du projet après autorisation, puis ouvrir le premier run GitHub Actions. Corriger les éventuels échecs de tests, de construction ou d’installation dans le conteneur avant d’annoncer le paquet comme utilisable. La construction locale reste non effectuée : aucun outil Arch ni nouvelle dépendance Python n’a été installé sur cette machine.

Références : [PKGBUILD](https://man.archlinux.org/man/PKGBUILD.5.en), [makepkg](https://man.archlinux.org/man/makepkg.8.en), [repo-add et signatures](https://man.archlinux.org/man/repo-add.8.en), [images officielles Arch](https://github.com/archlinux/archlinux-docker), [artefacts GitHub](https://docs.github.com/en/actions/tutorials/store-and-share-data), [configuration des dépôts pacman](https://man.archlinux.org/man/pacman.conf.5.en) et [installation et mises à jour pacman](https://man.archlinux.org/man/pacman.8.en).
