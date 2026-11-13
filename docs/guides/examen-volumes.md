# Examiner le volume d’un dossier partagé

## Périmètre

L’examen distingue le **point de montage attendu**, le montage qui couvre effectivement le chemin et l’existence du dossier lorsque sa consultation est prise en charge. Un dossier `/mnt/medias` peut exister sur le système de fichiers parent alors que le disque habituellement monté à cet endroit est absent ; la présence du dossier ne suffit donc pas.

La fonction est un constat ponctuel en lecture seule. Elle ne monte ni ne démonte de volume, ne crée pas le dossier choisi, ne modifie pas fstab et n’active aucun partage. Elle ne bloque pas la préparation d’un aperçu de partage : l’application des configurations n’existe toujours pas et les plans restent non applicables.

Vous fournissez explicitement le dossier et le point attendu. L’identité du disque n’est pas confirmée : aucun UUID, catalogue de disques ou fstab n’est consulté. Les permissions, ACL, accès Samba, règles SELinux/AppArmor et restrictions réseau restent hors de ce constat.

## Exemples sans Linux

Depuis la racine, avec Python déjà disponible :

```sh
python3 -B -m sambapilot examiner-volume --demo mounted --path /mnt/medias/films --mountpoint /mnt/medias
python3 -B -m sambapilot examiner-volume --demo unmounted --path /mnt/medias/films --mountpoint /mnt/medias
python3 -B -m sambapilot examiner-volume --demo readonly --path /mnt/medias/films --mountpoint /mnt/medias --json
```

Les cinq scénarios fictifs sont `mounted`, `unmounted`, `readonly`, `missing-path` et `unknown`. Ils ne lisent aucun fichier de l’hôte et ne lancent aucun processus. Les chemins saisis servent uniquement à la simulation.

## Consultation locale explicite sur Linux

```sh
python3 -B -m sambapilot examiner-volume --local --path /mnt/medias/films --mountpoint /mnt/medias
```

Adapter les deux chemins au dossier à examiner. `--local` et `--demo` sont obligatoires au choix et mutuellement exclusifs. Le dossier doit être situé dans le point attendu, distinct de `/`. Les chemins doivent être Linux absolus, sans `.` ou `..`, variable `%`, caractère de contrôle, antislash ou barre finale.

Sur un système autre que Linux, aucune table ni métadonnée du dossier n’est consultée : le résultat reste inconnu. Aucun outil ou paquet supplémentaire n’est installé pour débloquer le constat.

Le code `0` indique une simulation produite ou une table locale obtenue et analysée ; il ne garantit ni le montage attendu, ni l’existence du dossier, ni un accès effectif. Le code `2` indique des arguments refusés, une plateforme non prise en charge ou une table locale inaccessible/non concluante. Le rapport reste disponible en cas d’état local inconnu.

## Interpréter le résultat

| Information | Signification |
| --- | --- |
| `expected_mounted: true` | Un point correspondant à celui choisi figure dans le constat ; ce n’est pas une preuve d’identité du disque. |
| `expected_mounted: false` | Ce point ne figure pas dans la table lue ; aucune inspection du dossier n’est alors effectuée. |
| `expected_mounted: null` | Lecture impossible, table non reconnue, empilement ambigu ou changement pendant la consultation. |
| `actual_mount` | Montage couvrant lexicalement le chemin, éventuellement le volume parent ou un montage imbriqué. |
| `directory_status` | `present`, `missing`, `not-directory`, `not-checked` ou `unknown`. Un lien refusé est rangé dans `not-directory`. |
| `on_expected_mount: true` | Dossier constaté sur le point choisi, avec périphérique correspondant à la table relue. Aucun droit utilisateur déduit. |
| `on_expected_mount: false` | Point attendu absent ou montage imbriqué différent. |
| `on_expected_mount: null` | Le dossier n’a pas été confirmé ou sa consultation reste hors périmètre. |
| `read_only` | Option de lecture seule du montage constaté ; `false` ne signifie pas que le compte peut écrire. |

Le schéma JSON de cette commande est 1. Les inconnues restent `null`, distinctes de `false`. Le rapport conserve une date UTC et l’empreinte de la table lorsqu’elle est exploitable, ainsi que les deux chemins choisis. Les sources brutes de montage ne sont pas reproduites : elles pourraient contenir des noms ou informations d’authentification réseau. `can_apply` reste faux.

## Détails des sondes

Le lecteur consulte uniquement `/proc/self/mountinfo`, dans l’espace de montages du processus, avec une limite de 1 Mio et une lecture UTF-8 stricte. Il prend en compte les points imbriqués et les options de montage et de superbloc ; les empilements ambigus ne sont pas résolus arbitrairement. Il n’exécute ni `mount`, `umount`, `findmnt`, `testparm`, `sudo` ni commande de service.

Les métadonnées du dossier ne sont consultées que si le point attendu couvre directement le chemin et si les montages traversés appartiennent au périmètre local reconnu : ext2/ext3/ext4, btrfs, xfs, tmpfs, overlay, vfat, exfat, ntfs3 et f2fs. Les systèmes automatiques, distants, FUSE ou inconnus sont laissés sans consultation du dossier. Les dossiers sont ouverts composant par composant avec `O_PATH`, `O_DIRECTORY` et `O_NOFOLLOW`, sans lecture de leur contenu ni écriture. Les liens symboliques ne sont pas suivis. La table est relue après l’observation ; un changement invalide le résultat. Ce constat n’est pas un verrou contre de futurs changements de montage.

Références techniques : [mountinfo dans la documentation du noyau](https://www.kernel.org/doc/Documentation/filesystems/proc.txt), [format mountinfo](https://man7.org/linux/man-pages/man5/proc_pid_mountinfo.5.html), [drapeaux d’ouverture Linux](https://man7.org/linux/man-pages/man2/open.2.html).

## GTK et validation

Dans **Maintenance**, les chemins et résultats initiaux sont fictifs. Choisir un scénario affiche un exemple ; **Examiner ces chemins localement (lecture seule)** demande la consultation Linux dans un fil séparé. Modifier un chemin efface le résultat et invalide le retour local en attente ; revenir à un exemple ou fermer la fenêtre invalide aussi ces retours. La source affichée dans le bandeau ne mélange pas un constat local et les exemples.

Les tests locaux utilisent des tables et appels de métadonnées simulés. Ils ne prouvent aucun montage ou rendu GTK réel. La CI prépare l’analyse de la vraie table du conteneur et la consultation de dossiers temporaires présents, absents et liés symboliquement ; elle ne monte aucun disque. Les essais réels avec un disque externe et la stabilité des changements de montage restent à effectuer sur les cibles autorisées.
