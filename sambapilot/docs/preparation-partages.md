# Préparer les changements de partage

## Périmètre disponible

SambaPilot peut préparer l’ajout, la modification et le retrait d’une déclaration de partage à partir d’une configuration fictive ou d’un fichier choisi explicitement. Le terminal et la fenêtre GTK utilisent le même moteur de validation et de comparaison.

Les plans restent en mémoire. Aucune configuration n’est enregistrée, aucun dossier n’est créé ou supprimé, aucun compte ni droit n’est modifié et aucun service n’est rechargé. L’aperçu ne modifie pas non plus les exemples du tableau de bord ou de la matrice.

L’[examen d’un fichier choisi](inspection-configuration.md) peut servir de point de départ à un plan en lecture seule. Le [contrôle explicite avec testparm](validation-samba.md) est codé pour les configurations prises en charge, avec l’outil déjà installé sur Linux. L’application des changements reste à développer.

## Dans l’interface graphique

Depuis la racine du dépôt, avec les dépendances graphiques déjà disponibles :

```sh
cd sambapilot
python3 -B -m sambapilot gui --demo
```

Dans **Partages**, utiliser « Préparer un nouveau partage », « Préparer une modification » ou « Préparer le retrait ». Le formulaire est aussi accessible par la rubrique **Préparer un partage**.

Pour travailler à partir d’un fichier :

1. Ouvrir **Examiner une configuration** et choisir un fichier.
2. Après son examen, utiliser « Préparer un ajout » ou sélectionner une section puis demander une modification ou un retrait.
3. Vérifier la source affichée dans le formulaire et le bandeau **Fichier choisi · Aucun enregistrement**.
4. Générer l’aperçu. Le fichier est relu pour comparer son contenu à celui du chargement initial.

Le préremplissage d’une modification accepte uniquement des réglages explicites et compris : chemin simple, liste d’accès reconnue, lecture seule et visibilité déclarées, accès invité explicitement désactivé. Les réglages manquants, avancés ou ambigus ne sont pas remplacés par des valeurs supposées. Certains synonymes reconnus à l’inspection restent refusés par le moteur de réécriture prudent.

Le retrait n’a pas besoin de deviner les paramètres absents, mais reste refusé si la section contient des options avancées ou répétées. L’ajout conserve les autres sections, y compris leurs options non interprétées.

Pour une création ou une modification :

1. Indiquer le nom et le chemin Linux du dossier.
2. Choisir au moins un utilisateur ou un groupe autorisé. Séparer plusieurs identifiants par des virgules et saisir les groupes sans préfixe.
3. Choisir la lecture seule ou la lecture et l’écriture, puis la visibilité dans la liste des partages.
4. Générer l’aperçu et examiner le résumé ainsi que les lignes retirées et ajoutées.

Le nom n’est pas modifiable lorsqu’on prépare la modification d’un partage existant : le renommage n’est pas encore pris en charge. Le retrait affiche uniquement la déclaration à retirer ; les réglages du dossier sont désactivés dans ce mode.

Changer un champ efface l’aperçu précédent. Une demande invalide ne conserve pas un ancien plan valide. « Annuler la préparation » vide le formulaire et retourne aux partages. Aucun bouton ne permet d’appliquer le plan dans cette version.

Pour un plan sur fichier choisi, l’annulation retourne à l’examen de configuration. Effacer le rapport ou choisir un autre fichier abandonne aussi toute préparation associée au fichier précédent. Les boutons des partages fictifs rouvrent toujours une session de démonstration, sans réutiliser le fichier choisi.

## Dans le terminal

Depuis le dossier `sambapilot`, préparer un nouveau partage en lecture seule :

```sh
python3 -B -m sambapilot plan-partage --demo --action create --name Documents --path /srv/partages/documents --user alex
```

Préparer la modification du partage fictif Medias, avec écriture pour le groupe famille :

```sh
python3 -B -m sambapilot plan-partage --demo --action update --name Medias --path /srv/partages/medias --group famille --writable
```

Préparer le retrait de sa déclaration :

```sh
python3 -B -m sambapilot plan-partage --demo --action remove --name Medias
```

Pour préparer une modification à partir d’un fichier choisi, remplacer `--demo` par `--config` :

```sh
python3 -B -m sambapilot plan-partage --config /chemin/vers/smb.conf --action update --name Medias --path /srv/partages/medias --group famille --writable
```

Les options `--demo` et `--config` sont obligatoires au choix et mutuellement exclusives. Le fichier est lu puis relu avant de générer l’aperçu, sans écriture. L’utilisateur doit fournir l’ensemble des réglages souhaités dans le terminal ; aucun héritage n’est déduit automatiquement.

Les options `--user` et `--group` sont répétables. `--hidden` propose de masquer le partage dans la liste ; cela ne supprime pas les droits d’accès directs. Une modification demande tous les réglages souhaités : les listes d’accès fournies remplacent les précédentes dans la proposition.

L’option `--json` produit un plan structuré contenant la configuration candidate, la comparaison, les empreintes de la configuration de départ et du résultat proposé, et `can_apply: false`. Pour un fichier choisi, le champ `source` identifie son chemin. Le texte complet du candidat inclut les options non interprétées qui sont conservées ; ce format est donc différent de l’inventaire, qui n’affiche pas leurs valeurs. Aucun fichier JSON n’est enregistré automatiquement.

Le code de sortie est `0` si l’aperçu est produit et `2` si la demande est invalide. Un aperçu produit ne prouve ni la validité de la configuration par Samba ni l’accès réel au dossier.

Avec `--validate`, un contrôle distinct est demandé sur une copie temporaire. Le code `4` signale un contrôle non accepté ou indisponible ; le code `0` signifie alors que `testparm` a accepté le candidat et que les vérifications de source ont réussi. Cela ne prouve pas l’accès réel et n’applique rien.

## Validations et préservation

- Les noms sont limités à 80 caractères : lettres, chiffres, espaces, points, tirets et traits de soulignement, avec une lettre ou un chiffre au début. Les sections `global`, `homes` et `printers` sont réservées.
- Les noms de partage sont comparés sans distinction de casse pour détecter les doublons.
- Le chemin doit être absolu, sans variable Samba, guillemet, caractère de contrôle ou traversée `..`. La racine `/` est refusée.
- Les identifiants de comptes et de groupes suivent un format simple ; les listes vides et les doublons sont refusés.
- La proposition désactive explicitement l’accès invité et conserve la lecture seule par défaut.
- Les groupes Linux sont générés avec le préfixe Samba `+`, pour désigner les groupes UNIX sans résolution préalable comme netgroups NIS. Voir les règles de `valid users` et `invalid users` dans la [documentation officielle de smb.conf](https://www.samba.org/samba/docs/current/man-html/smb.conf.5.html).
- Lors d’une création, la configuration de départ est conservée intégralement. Lors d’une modification, les autres sections et les commentaires de la section cible sont préservés ; seuls les paramètres gérés sont remplacés ou ajoutés.
- Lors d’un retrait, la section cible et ses commentaires sont retirés de la configuration candidate ; les autres sections sont conservées.
- Le BOM UTF-8 éventuel et les fins de ligne CRLF sont conservés dans le candidat.
- Les sections en double, les inclusions, les configurations indirectes et les lignes continuées bloquent la préparation. Une section cible comportant des paramètres avancés, inconnus ou répétés n’est pas réécrite ou retirée automatiquement.

Le moteur n’est pas un interpréteur complet de Samba. Les paramètres globaux peuvent influencer les accès. Les dossiers, les comptes, les groupes, les permissions Linux, les ACL et les règles réseau ne sont pas vérifiés par ce plan.

## État de référence et autorisation

Le plan porte une empreinte du contenu de départ. Lors d’une préparation sur fichier, la lecture est bornée et suit les mêmes règles que l’inspection. Chaque génération d’aperçu relit le chemin choisi et compare les octets à l’état initial, y compris le BOM et les fins de ligne. Si le fichier est devenu illisible, a été remplacé par un lien symbolique final ou a changé de contenu, le plan précédent est abandonné et aucun nouvel aperçu n’est produit.

Un changement de contenu nécessite de recharger le fichier et d’examiner ses nouveaux réglages. La vérification a lieu au moment de la génération : ce n’est pas une surveillance continue du fichier. Aucun plan n’est actuellement applicable.

Une future application devra relire l’état courant, valider la configuration, présenter l’intervention précise, obtenir une confirmation explicite, sauvegarder les réglages puis vérifier le résultat. La préparation d’un aperçu ne constitue jamais cette autorisation.
