# Examiner une configuration Samba

## Objectif

Lire un fichier explicitement choisi pour inventorier ses déclarations locales de partages, sans modifier la configuration ni déduire des permissions effectives. Cette lecture est indépendante des exemples et des plans de démonstration.

Le fichier n’est pas validé par Samba : aucun `testparm`, service, outil réseau ou programme externe n’est lancé. Le moteur ne lit pas les comptes, les groupes, les dossiers partagés ou leurs ACL.

## Utilisation dans le terminal

Depuis le dossier `sambapilot`, indiquer le fichier à examiner :

```sh
python3 -B -m sambapilot examiner-config --config /chemin/vers/smb.conf
python3 -B -m sambapilot examiner-config --config /chemin/vers/smb.conf --json
```

Sur la machine Linux cible, le chemin peut être `/etc/samba/smb.conf` s’il existe et si le compte courant peut le lire. La commande ne choisit aucun fichier par défaut et ne demande pas `sudo` en cas de refus.

Codes de sortie : `0` si l’inventaire local est produit, même avec des options non interprétées ; `2` si les arguments sont invalides, la lecture impossible ou la structure hors du périmètre pris en charge. Le code `0` ne signifie pas que Samba est correctement configuré.

## Utilisation dans la fenêtre GTK

Ouvrir `python3 -B -m sambapilot gui --demo`, puis **Examiner une configuration**.

- « Choisir un fichier… » demande une sélection explicite avec le sélecteur GTK.
- « Examiner l’exemple fictif » produit un rapport sans lire de fichier.
- « Effacer le rapport » retire les données affichées de la mémoire de la fenêtre.

La rubrique affiche un bandeau « Examen de fichier · Lecture seule ». Le fichier peut ensuite servir à [préparer un aperçu](preparation-partages.md) via les boutons dédiés. Ce parcours affiche un bandeau de fichier choisi ; les autres pages conservent leurs données fictives. Aucun plan de démonstration n’est converti silencieusement en plan sur fichier.

La lecture est effectuée dans un fil séparé pour ne pas bloquer la fenêtre. Un résultat devenu obsolète après une nouvelle sélection, un effacement ou une fermeture n’est pas affiché. Une annulation ou une erreur ne conserve pas un ancien rapport présenté comme celui du nouveau fichier.

## Informations affichées

Pour chaque section ordinaire du fichier :

- le nom et le chemin déclarés ;
- la lecture seule, la visibilité et l’accès invité, s’ils sont déclarés localement ;
- les utilisateurs et les groupes UNIX reconnus dans `valid users` ;
- les destinataires non résolus et les noms des options non interprétées ;
- les ambiguïtés nécessitant une vérification.

Les synonymes courants sont reconnus, notamment `writable`, `writeable`, `write ok`, `browsable` et `public`. Des déclarations concurrentes d’un même paramètre restent inconnues plutôt que de choisir arbitrairement une valeur.

Une valeur absente reste inconnue : les réglages globaux et les valeurs par défaut ne sont pas appliqués. Une liste d’accès vide est distinguée d’une liste absente, sans conclure à une autorisation effective.

Le préfixe `+` est identifié comme groupe UNIX. Les noms avec `@`, les domaines et les substitutions restent non résolus ; aucune consultation NSS ou NIS n’est effectuée. Les chemins contenant des variables sont affichés comme déclarés, sans développer ces variables ni accéder aux dossiers.

Les sections `global`, `homes` et `printers` sont signalées séparément. Les partages dynamiques ne sont pas inventés à partir de ces sections.

## Limites de lecture

Seuls les fichiers réguliers directement sélectionnés sont acceptés. Un lien symbolique final, un dossier ou un fichier spécial est refusé. Un fichier de plus de **1 Mio**, un encodage autre qu’UTF-8 ou un changement détecté pendant la lecture bloque l’opération. Un BOM UTF-8 est accepté ; l’empreinte SHA-256 correspond aux octets originaux.

Les inclusions, les directives indirectes, les sections en double, les lignes continuées et les structures inconnues bloquent l’inventaire. Aucun autre fichier n’est ouvert pour tenter de résoudre ces cas. Un rapport bloqué ne signifie pas que le serveur n’a aucun partage.

Les options avancées ne sont pas effacées : leur nom est signalé, sans reproduire leur valeur dans le rapport. Le contenu brut du fichier n’est ni exporté dans le JSON ni enregistré par l’application. Les valeurs reconnues, comme les chemins et les identifiants, peuvent néanmoins contenir des informations personnelles ; le rapport reste destiné à l’utilisateur qui a choisi ce fichier.

## Validation réalisée et étapes suivantes

La lecture est testée avec des fichiers temporaires, notamment pour les droits refusés, les fichiers spéciaux, la taille, l’encodage, les changements de contenu et l’absence de modification du fichier lu. Le traitement des configurations et la sortie terminal sont testés automatiquement.

L’ouverture du sélecteur et le rendu GTK restent à vérifier dans une session graphique autorisée. La lecture de la configuration réelle de l’ordinateur Omarchy n’a pas été effectuée pendant le développement.

La lecture est reliée aux plans en mémoire, avec relecture du fichier avant chaque aperçu. Restent à développer : l’interprétation de la configuration effective avec Samba, la validation des candidats et la collecte prudente des permissions Linux. Aucune de ces étapes n’autorise une installation ou une modification système sans accord explicite.

Références : [format et sémantique de smb.conf](https://www.samba.org/samba/docs/current/man-html/smb.conf.5.html), [sélecteur de fichiers GTK 4.10](https://docs.gtk.org/gtk4/class.FileDialog.html).
