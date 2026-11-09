# SambaPilot

SambaPilot est un projet d’utilitaire pour installer, configurer et gérer les partages Samba sur mon ordinateur Omarchy à la maison.

Il proposera **une interface graphique et une interface terminal**, reposant sur le même moteur de gestion.

## État du projet

Le premier socle Python est disponible : moteur de diagnostic partagé, interface terminal, sortie JSON et scénarios de démonstration. Le moteur et le terminal fonctionnent sans dépendance Python externe et n’appliquent aucun changement système.

Le diagnostic repère la distribution, un éventuel dossier Omarchy, les exécutables système, le fichier de configuration Samba et l’état de plusieurs services systemd. La présence d’un dossier Omarchy reste un indice, pas une certification de l’installation.

Une première interface graphique GTK est codée en mode démonstration : tableau de bord, partages, matrice filtrable des accès et rubriques de pare-feu et de maintenance. Son affichage réel reste à vérifier avec GTK sur Omarchy. L’installation de Samba et la modification des partages, des comptes, des permissions et du pare-feu restent à développer.

Une première vue « Qui peut accéder à quoi ? » est également disponible en démonstration. Elle croise les règles de partage et les observations de permissions déclarées, avec des explications pour les conflits et les informations inconnues.

La préparation des partages est disponible dans le terminal et dans le formulaire graphique : création, modification ou retrait d’une déclaration, validations et comparaison avant/après. Elle peut partir d’une configuration fictive ou d’un fichier choisi explicitement, avec détection d’un changement de contenu avant génération. Aucun plan n’est appliqué ni enregistré.

Un contrôle explicite du candidat avec `testparm` est également codé, pour Linux avec l’outil déjà installé. Il utilise une copie temporaire privée et ne rend pas le plan applicable. Son exécution réelle avec Samba reste à vérifier ; les tests actuels simulent les retours du programme.

La préparation d’installation fournit aussi un plan descriptif des paquets, de la configuration, des comptes, des services et du pare-feu. Elle peut utiliser des scénarios fictifs ou un constat local en lecture seule. Elle ne calcule pas encore la transaction exacte et n’exécute aucune installation.

La préparation du pare-feu permet de déclarer un gestionnaire, une interface et des sources IPv4/IPv6 pour produire des intentions de règles SMB. Elle ne lit pas encore les règles existantes et ne produit aucune commande native ni application.

L’examen d’un fichier de configuration choisi explicitement est disponible en lecture seule. Il inventorie les déclarations locales sans suivre les inclusions, sans calculer les droits effectifs et sans remplacer les exemples de démonstration.

## Essayer depuis les sources

Python 3.9 ou ultérieur doit déjà être disponible. Depuis la racine du dépôt :

```sh
cd sambapilot
python3 -B -m sambapilot diagnostic --demo
```

Le mode démonstration utilise uniquement des données fictives, sans consulter la machine. Trois scénarios sont disponibles :

```sh
python3 -B -m sambapilot diagnostic --demo fresh
python3 -B -m sambapilot diagnostic --demo configured
python3 -B -m sambapilot diagnostic --demo restricted
python3 -B -m sambapilot diagnostic --demo --json
```

Pour examiner les étapes d’une installation sans exécuter d’intervention :

```sh
python3 -B -m sambapilot preparer-installation --demo fresh
```

L’option explicite `--local` permet un constat sur l’ordinateur courant. La rubrique graphique **Installation** propose les mêmes exemples et un bouton de lecture locale. Voir le [guide de préparation d’installation](docs/preparation-installation.md).

Pour préparer un périmètre réseau déclaré, sans ouvrir de port :

```sh
python3 -B -m sambapilot plan-pare-feu --manager ufw --interface enp3s0 --source 192.168.1.0/24
```

L’interface et le réseau ci-dessus sont des exemples à adapter. La rubrique GTK **Pare-feu** expose le même formulaire, sans présélection. Voir le [guide de préparation du pare-feu](docs/preparation-pare-feu.md).

Pour essayer la matrice des accès :

```sh
python3 -B -m sambapilot permissions --demo
python3 -B -m sambapilot permissions --demo --json
```

Cette vue utilise uniquement des données fictives : elle ne lit pas les comptes, les ACL ou les partages de la machine. Les colonnes de lecture et d’écriture sont des estimations à partir de ces données, avec le détail des deux couches Samba et fichiers. Une information manquante est affichée comme inconnue ; aucune permission n’est appliquée. Le drapeau `--demo` est obligatoire tant que la collecte réelle n’est pas implémentée.

Pour ouvrir l’interface graphique, si GTK 4.10 ou ultérieur et PyGObject sont déjà disponibles pour Python :

```sh
python3 -B -m sambapilot gui --demo
```

L’application n’installe aucune dépendance manquante. Les détails et les limites de validation sont dans le [guide de l’interface graphique](docs/interface-graphique.md).

Pour préparer un nouveau partage en lecture seule sur la configuration fictive :

```sh
python3 -B -m sambapilot plan-partage --demo --action create --name Documents --path /srv/partages/documents --user alex
```

Le [guide de préparation des partages](docs/preparation-partages.md) décrit les options de modification et de retrait, les validations et le formulaire GTK.

Ajouter `--validate` pour demander le contrôle avec Samba déjà installé, ou utiliser **Contrôler avec Samba** après la génération d’un aperçu graphique. Le [guide de validation Samba](docs/validation-samba.md) précise les configurations prises en charge et les codes de sortie.

Pour préparer un aperçu à partir d’un fichier choisi, remplacer `--demo` par `--config /chemin/vers/smb.conf`. Dans la fenêtre, les boutons correspondants sont disponibles après l’examen du fichier. Les configurations complexes ou les réglages incomplets peuvent être refusés ; aucune valeur inconnue n’est supposée pour préremplir le formulaire.

Pour examiner un fichier choisi :

```sh
python3 -B -m sambapilot examiner-config --config /chemin/vers/smb.conf
```

La rubrique graphique **Examiner une configuration** permet aussi de sélectionner un fichier. Les précautions de lecture et les limites d’interprétation sont décrites dans le [guide d’examen de configuration](docs/inspection-configuration.md).

Sur Linux, pour consulter la machine locale en lecture seule :

```sh
python3 -B -m sambapilot diagnostic
```

Cette commande ne demande pas `sudo`. Elle consulte les métadonnées de `/etc/samba/smb.conf` sans lire son contenu, et utilise uniquement des requêtes `systemctl show` pour les services. Elle ne lance ni les outils Samba ni les outils de pare-feu. Les exécutables sont recherchés dans `/usr/bin` et `/usr/sbin`, sans lancer les éventuels outils d’installation automatique présents dans le `PATH` utilisateur.

Un service inaccessible est signalé comme inconnu. La présence d’un outil ou d’un service actif ne prouve pas que les règles du pare-feu autorisent ou bloquent un accès. Les partages et les connexions réseau ne sont pas encore testés.

Sur macOS et les autres systèmes hors Linux, le diagnostic local retourne un rapport non pris en charge sans poursuivre les sondes système ; le mode démonstration reste utilisable.

Codes de sortie : `0` pour un rapport Linux ou une démonstration produits, même si des composants sont absents ou inconnus ; `2` pour un système hors Linux ou une erreur d’arguments. Le code `0` ne signifie pas que Samba est prêt à l’emploi.

## Développement et vérification

Depuis ce dossier :

```sh
make test
make check
make demo
```

Les tests utilisent la bibliothèque standard, des sondes simulées et des fichiers temporaires. Ils ne nécessitent ni Samba, ni systemd, ni droits administrateur. L’option `-B` évite la création de caches Python pendant ces commandes.

Le fichier `pyproject.toml` prépare le conditionnement Python et le futur point d’entrée `sambapilot`. Aucune installation du projet n’est nécessaire pour les commandes ci-dessus.

## Fonctions prévues

- Installer et configurer les composants nécessaires à Samba.
- Ajouter, modifier et retirer des partages de dossiers.
- Gérer les utilisateurs Samba et les accès par utilisateur ou par groupe.
- Gérer les permissions Linux et les droits de lecture et d’écriture des partages.
- Configurer les règles de pare-feu nécessaires et limiter les accès aux réseaux ou aux adresses choisis.
- Vérifier la configuration et gérer les services associés.
- Sauvegarder les réglages et accompagner leur restauration.
- Diagnostiquer les problèmes de configuration et d’accès.

## Principe d’utilisation

Chaque intervention devra suivre le même parcours dans les deux interfaces : examiner l’état actuel, afficher les changements proposés, obtenir une confirmation explicite, sauvegarder les réglages concernés, appliquer les changements puis vérifier le résultat.

La création de ce projet n’autorise aucune installation ni modification de l’environnement de l’ordinateur. Les consignes du [guide des assistants](../AGENTS.md) restent applicables.

## Documentation

- [Cahier des charges](docs/cahier-des-charges.md)
- [Architecture et étapes de développement](docs/architecture-et-roadmap.md)
- [Vérifications du premier socle](docs/validation-socle.md)
- [Recommandations et première vue des accès](docs/recommandations.md)
- [Interface graphique GTK : lancement et vérifications](docs/interface-graphique.md)
- [Préparation des partages et comparaison des changements](docs/preparation-partages.md)
- [Examen d’un fichier de configuration en lecture seule](docs/inspection-configuration.md)
- [Contrôle explicite d’un candidat avec testparm](docs/validation-samba.md)
- [Préparation d’installation, sans exécution](docs/preparation-installation.md)
- [Périmètre réseau et intentions de règles de pare-feu](docs/preparation-pare-feu.md)
