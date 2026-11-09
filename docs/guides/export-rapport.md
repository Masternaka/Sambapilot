# Exporter un rapport Markdown

## Périmètre

L’export crée un document à partir d’un **rapport de configuration déjà lu**. Il présente la source, les dates, les déclarations de partage, les informations inconnues et les vérifications restantes. Il ne collecte pas un nouveau diagnostic système et ne lance ni testparm ni connexion réseau.

Le document contient le chemin source, les chemins des dossiers et les identifiants reconnus ou non résolus. Ils peuvent être personnels : leur présence est signalée et le contenu est visible avant l’enregistrement. Le fichier brut, les commentaires, les configurations candidates et les valeurs des options non interprétées sont exclus. Les valeurs reconnues ne sont pas anonymisées.

Une configuration peut contenir des informations sensibles dans un chemin ou un identifiant. Relire le document avant de le partager ; l’absence de fichier brut ne garantit pas l’absence de données sensibles.

## Dans GTK4

1. Examiner une configuration choisie, ou examiner l’exemple fictif.
2. Utiliser **Exporter un rapport Markdown…** dans l’examen ; le même bouton est disponible dans Partages lorsque les déclarations d’un fichier sont affichées.
3. Lire l’aperçu et l’avertissement relatif aux chemins et identifiants.
4. Cliquer sur **Choisir où enregistrer…**, puis choisir un nouveau fichier avec l’extension `.md`.

Aucun fichier n’est créé à l’ouverture de l’aperçu. La destination est choisie explicitement ; aucun répertoire n’est créé automatiquement. Un nom existant est refusé, même si le sélecteur GTK propose de le remplacer.

Le contenu enregistré correspond exactement au texte de l’aperçu. Il inclut tout l’inventaire, même si la page Partages est filtrée. Le rapport d’un exemple reste identifié comme fictif ; il ne contient pas des observations réelles de la machine.

Changer, recharger ou effacer la source ferme l’ancien aperçu. Une réponse tardive du sélecteur d’enregistrement ne peut pas exporter cet ancien rapport. Annuler le sélecteur ne crée aucun document et permet de conserver l’aperçu.

La source n’est pas relue ni surveillée au moment de l’export : le rapport décrit la lecture ponctuelle indiquée, pas nécessairement l’état actuel du fichier. Pour actualiser les déclarations, recharger d’abord la source puis préparer un nouvel export.

## Dans le terminal

Depuis la racine, afficher un aperçu sans créer de fichier :

```sh
python3 -B -m sambapilot examiner-config --config /chemin/vers/smb.conf --markdown
```

Après examen du contenu, demander explicitement l’enregistrement en confirmant la présence des chemins et identifiants :

```sh
python3 -B -m sambapilot examiner-config --config /chemin/vers/smb.conf --export /chemin/vers/nouveau-rapport.md --confirm-export
```

Les deux commandes lisent séparément la source : la seconde construit un nouveau rapport de la lecture qu’elle effectue. Il ne faut donc pas supposer qu’elle réutilise les octets de l’aperçu d’une exécution précédente.

`--export` et `--confirm-export` doivent être fournis ensemble. Les formats `--json`, `--markdown` et `--export` sont mutuellement exclusifs. Sans ces options, l’inventaire texte habituel est conservé. Aucun export n’est déclenché implicitement par les autres commandes.

Codes de sortie : `0` si l’inventaire est produit et l’export demandé enregistré ; `2` pour une erreur de lecture, d’arguments ou d’enregistrement, ou pour un inventaire bloqué. Un rapport bloqué peut être exporté pour conserver ses explications, mais la commande garde le code `2` même lorsque ce fichier a été enregistré. Examiner le message et le statut du rapport.

## Contenu et dates

Le document indique :

- la version de SambaPilot, la source et son mode ;
- l’empreinte SHA-256 du contenu lu ;
- la date de lecture UTC, enregistrée à la fin de la lecture réussie ;
- la date UTC de création du rapport, distincte de la précédente ;
- les déclarations locales et leurs limites, sans résoudre les réglages globaux ou les inclusions ;
- les explications sur les réglages manquants, ambigus ou non pris en charge et les vérifications à effectuer.

Une date de lecture non enregistrée reste inconnue ; la date de création de l’export ne la remplace pas. Les snapshots et rapports d’inventaire exposent désormais un champ facultatif `read_at`, également présent dans leur JSON. Les exemples en mémoire ne sont pas présentés comme des fichiers réellement lus.

Un inventaire bloqué n’exporte pas de déclarations présentées comme fiables. Un inventaire vide ne prouve pas l’absence de partages sur le serveur. Les noms, chemins et autres textes fournis par la source sont échappés pour éviter leur interprétation comme liens Markdown, balises HTML ou titres injectés.

## Enregistrement et limites

Le moteur prépare un fichier temporaire privé dans le dossier choisi et publie le fichier complet sans remplacer de destination existante. Les permissions sont `0600` sur les systèmes POSIX pris en charge. Un fichier, un dossier, un lien symbolique ou un nom créé entre-temps reste préservé. Les éléments temporaires sont nettoyés après l’opération.

La publication repose sur les liens physiques du système de fichiers ; une destination incompatible produit une erreur, sans tentative de remplacement. Après une erreur de nettoyage, un fichier complet peut déjà exister : vérifier le message et la destination avant de recommencer.

Cet export n’est ni une sauvegarde complète de `smb.conf`, ni un plan applicable, ni une preuve de droits effectifs. Il ne modifie pas la configuration source et ne change aucun compte, service ou pare-feu.

## Validation

Les tests ordinaires couvrent le contenu, les dates, les modes, l’exclusion des commentaires et valeurs inconnues, l’échappement Markdown/HTML, la préservation de la source, les permissions du fichier créé, les refus d’écrasement, les liens, les erreurs, le nettoyage et les conflits de création de destination. Le parcours terminal conserve ses modes texte et JSON et vérifie la demande explicite d’export.

Les tests natifs GTK de l’aperçu, de l’enregistrement, de l’annulation et des résultats obsolètes sont préparés mais restent à exécuter. Aucun rendu réel GTK ou lecture dans un logiciel Markdown n’est validé par les tests de contenu.

Références GTK utilisées : [sélecteur d’enregistrement](https://docs.gtk.org/gtk4/method.FileDialog.save.html), [résultat et annulation](https://docs.gtk.org/gtk4/method.FileDialog.save_finish.html).
