# Diagnostic par partage

## Une fiche depuis la déclaration choisie

La fiche regroupe les réglages Samba connus, les incertitudes, les pistes de dépannage, les adresses de connexion facultatives et un éventuel constat du dossier/volume. Elle utilise le même inventaire dans le terminal et GTK, avec la source, son empreinte SHA-256 et sa date de lecture.

Elle ne calcule pas les permissions effectives et ne teste aucun accès client. Une visibilité déclarée ou une autorisation d’écriture ne constitue pas une preuve de découverte réseau ou de droit réel. Les champs `effective_read`, `effective_write` et `network_verified` restent `null`, distincts d’un refus ; `can_apply` reste faux.

La sortie JSON de cette fiche possède son propre schéma 1 ; les adresses et le volume joint conservent leurs structures et dates respectives.

Un fichier choisi peut provenir d’un autre serveur. Son chemin Linux et un nom de serveur saisi ne prouvent pas que le dossier appartient à cet ordinateur. Les observations locales sont donc séparées des déclarations et ne sont jamais attachées implicitement à un serveur distant.

## Démonstration utilisable sans Linux

Depuis la racine, avec Python déjà disponible :

```sh
python3 -B -m sambapilot diagnostic-partage --demo --share Famille
python3 -B -m sambapilot diagnostic-partage --demo --share Medias --symptom readonly --server serveur.example.invalid
python3 -B -m sambapilot diagnostic-partage --demo --share Famille --demo-volume unmounted --mountpoint /srv/partages --json
```

Le serveur n’est ni résolu ni contacté. Le volume reste fictif et les identités sont celles des exemples. Les symptômes sont `invisible`, `denied` et `readonly`, comme dans le [dépannage](diagnostic-depannage.md).

## Fichier choisi, sans consultation locale implicite

```sh
python3 -B -m sambapilot diagnostic-partage --config /chemin/vers/smb.conf --share Documents --symptom denied
```

`--demo` ou `--config` est obligatoire et les deux s’excluent. Le partage doit être présent et unique dans un inventaire sans blocage ; la sélection ignore la casse mais reprend le nom déclaré. Les sections spéciales restent hors périmètre. Une déclaration avancée ou un nom non portable peut être examiné, même si sa connexion ou son volume ne peuvent pas être préparés.

`--server` est facultatif. Il prépare les [adresses de connexion](fiche-connexion.md), avec leurs limites de noms DNS/IPv4 et de noms de partage. Un nom non portable produit une fiche de diagnostic avec l’explication d’indisponibilité des adresses. Une valeur serveur invalide passée au terminal est refusée avant de lire le fichier ; un identifiant ou mot de passe intégré n’est pas repris dans le message d’erreur.

Sans demande de volume, seul le fichier choisi est lu. Aucun service, compte, dossier, montage, ACL ou pare-feu de cet ordinateur n’est consulté.

## Joindre un constat de volume

Pour une simulation, `--demo-volume` exige `--demo` et un `--mountpoint` explicite. Les cinq scénarios et les limites sont ceux de l’[examen des volumes](examen-volumes.md).

Sur Linux, lorsque le dossier décrit appartient bien à **cet ordinateur**, le terminal peut recevoir cette confirmation explicite :

```sh
python3 -B -m sambapilot diagnostic-partage --config /chemin/vers/smb.conf --share Documents --local-volume --mountpoint /mnt/donnees
```

`--local-volume` confirme cette portée locale et exige `--config`. Le dossier provient uniquement de la déclaration sélectionnée ; aucun autre chemin n’est deviné. Le point attendu doit être fourni explicitement et contenir ce dossier. Un chemin inconnu ou non pris en charge bloque la consultation. Une simulation de volume ne peut pas être jointe à un fichier réel et un constat local ne peut pas être lancé depuis les exemples.

La déclaration est relue avant le constat par le chargement initial du terminal, puis après le constat. Un changement d’empreinte ou une relecture impossible refuse le résultat. La date du fichier et celle du volume restent distinctes. Hors Linux, le volume reste inconnu, sans consultation du dossier ou de la table.

La commande renvoie `0` lorsqu’une fiche est produite, même si des informations restent inconnues ; `2` pour des arguments ou une source refusés, un chemin non utilisable ou une configuration devenue obsolète pendant le constat. Aucun code ne certifie un accès Samba.

## Parcours GTK

Dans **Partages**, sélectionner **Diagnostic de ce partage…** sur un exemple ou une déclaration du fichier choisi. La fiche s’ouvre immédiatement, sans sonde locale. Elle affiche les réglages et les incertitudes, avec le symptôme sélectionnable.

- Renseigner un serveur prépare les adresses. La copie Windows ou SMB exige un clic ; aucun gestionnaire de fichiers n’est lancé.
- Dans les exemples, fournir le point attendu puis demander **Examiner le volume fictif**.
- Sur un fichier choisi, fournir le point attendu, cocher **Je confirme que le dossier décrit appartient à cet ordinateur**, puis sélectionner **Examiner le dossier sur cet ordinateur**. La simple ouverture ou la coche seule ne lance rien.

La consultation locale s’effectue dans un fil séparé. Le fichier est vérifié avant et après ce constat. S’il a changé ou n’est plus lisible, les adresses et le constat sont invalidés et la fiche demande de recharger la source. Le fichier source n’est jamais modifié.

Changer le serveur, le point attendu, le symptôme, le scénario ou la confirmation locale abandonne le constat joint et invalide les retours en attente. Changer ou effacer la source ferme la fiche ; sélectionner un autre partage ouvre une nouvelle fiche. Aucun ancien résultat ne peut être réintroduit après ces actions. La fiche n’est pas une surveillance continue : sans nouveau constat, elle décrit la lecture datée, pas les changements extérieurs ultérieurs.

La fiche contient des chemins, noms de partages, comptes et groupes déclarés. Elle n’inclut pas la configuration brute, le candidat ou les valeurs d’options inconnues. Aucun export de document n’est effectué. Une adresse déjà copiée dans le presse-papiers n’est pas effacée automatiquement lors de l’invalidation.

## Vérification

Les tests ordinaires couvrent la liaison à la bonne déclaration, l’absence de lecture locale implicite, les inconnues, les volumes de portée incompatible, la conservation de la date et les changements de fichier. Les tests GTK et le contrôle du paquet installé préparent l’ouverture, les copies simulées, les confirmations et l’invalidation. Les copies réelles, le rendu et les constats sur les cibles restent à vérifier en CI ou dans une session autorisée. Aucun essai local simulé ne prouve une authentification, des permissions ou une connexion réseau réelle.
