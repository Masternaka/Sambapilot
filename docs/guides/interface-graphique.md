# Interface graphique de SambaPilot

## État actuel

La première interface native GTK est codée. Le tableau de bord et la matrice des accès fonctionnent en démonstration. L’examen et la page Partages peuvent afficher les déclarations d’un fichier choisi explicitement, sans les convertir en droits effectifs. Aucun compte, aucune permission et aucun réglage système ne sont modifiés par les actions de cette fenêtre.

L’affichage réel reste à vérifier dans un environnement disposant de GTK et d’une session graphique. Il n’a pas été validé visuellement pendant ce développement sur macOS.

## Lancement

Prérequis déjà installés pour l’interpréteur utilisé : Python 3.9 ou ultérieur, PyGObject et GTK **4.10 ou ultérieur**. Le terminal reste utilisable sans GTK. Ces dépendances ne sont ni installées ni téléchargées par SambaPilot.

Depuis la racine du dépôt :

```sh
python3 -B -m sambapilot gui --demo
```

Sur la machine cible, utiliser l’interpréteur Python ayant accès aux bibliothèques GTK installées. Une installation dans un autre environnement Python ne garantit pas leur disponibilité dans l’interpréteur courant.

Si PyGObject, GTK ou la session graphique sont indisponibles, la commande affiche un message sur la sortie d’erreur et retourne le code `3`. Le drapeau `--demo` est obligatoire ; son absence retourne le code `2` sans ouvrir la fenêtre.

## Navigation

Le [diagnostic et dépannage](diagnostic-depannage.md) du tableau de bord propose trois distributions fictives et un bouton de lecture locale explicite. Une consultation locale ne remplace pas les sources des autres pages.

L’application utilise l’icône « dossier connecté » : un dossier bleu avec trois nœuds turquoise. Les PNG transparents sont inclus dans le paquet Python ; GTK les recherche dans ses ressources locales, sans copier de fichier dans le thème de l’utilisateur. Le [guide des icônes](icones-application.md) décrit les fichiers et les limites de validation.

| Rubrique | Fonctions de cette version |
| --- | --- |
| Tableau de bord | Diagnostic local demandé, exemples Arch/Debian/Fedora, dépannage selon le symptôme et raccourcis vers les accès fictifs. |
| Installation | Plans descriptifs d’exemple ou constat local explicitement demandé, sans installation. |
| Partages | Exemples fictifs ou déclarations d’un fichier choisi, détails, source et empreinte, rechargement explicite et accès au rapport de préparation. Les actions des exemples restent disponibles après retour à la démonstration. |
| Utilisateurs et accès | Matrice, filtres par compte et partage, recherche par nom ou chemin, filtre des conflits et détail de la ligne sélectionnée. |
| Préparer un partage | Formulaire, aperçu, vérification de source, contrôle Samba explicite et annulation sans application. |
| Examiner une configuration | Choix explicite d’un fichier, inventaire en lecture seule, passage à la préparation d’un aperçu et effacement du rapport. |
| Pare-feu | Formulaire de périmètre déclaré : gestionnaire, interface, sources IPv4/IPv6, zone et NetBIOS optionnel, sans lecture ou application des règles. |
| Maintenance | États fictifs des services et présentation des sauvegardes et restaurations encore à développer. |

La mention « Mode démonstration » reste visible sur les pages d’exemples. La rubrique d’examen de configuration affiche « Examen de fichier · Lecture seule » et identifie la source du rapport. Le formulaire sur fichier affiche « Fichier choisi · Aucun enregistrement » et le chemin source. Les droits inconnus sont écrits explicitement. Les couleurs éventuelles du thème ne sont pas nécessaires pour distinguer les résultats.

La rubrique Installation indique « Constat local · Aucune installation » si l’utilisateur demande d’examiner cet ordinateur. Ses exemples restent séparés des informations locales et aucun bouton n’exécute les étapes proposées.

La rubrique Pare-feu affiche **Périmètre déclaré · Aucun port ouvert**. Son formulaire ne présélectionne aucun réseau ni gestionnaire. Les résultats sont des intentions et ne prouvent pas l’effet d’un ajout sur le pare-feu existant. Voir le [guide du périmètre réseau](preparation-pare-feu.md).

Le bouton « Réinitialiser » retire les filtres. Lorsqu’aucune ligne ne correspond, la fenêtre affiche un état vide et efface l’ancienne sélection. Les explications distinguent les règles Samba, les permissions de fichiers et les informations manquantes.

Le [formulaire de préparation des partages](preparation-partages.md) génère uniquement un aperçu en mémoire. Modifier un champ invalide l’aperçu précédent. Une annulation vide le formulaire sans changer la configuration fictive ni la machine.

Dans le formulaire sur fichier, **Recharger sans perdre ma saisie** prépare une comparaison de source. **Utiliser cette source rechargée** demande une adoption distincte, avec nouvelle vérification du fichier, puis un nouvel aperçu reste nécessaire. Les saisies brutes sont conservées, les conflits sont refusés et aucune fusion n’est automatique. Voir le [parcours de reprise](preparation-partages.md#reprendre-après-une-modification-extérieure).

Après un aperçu, **Contrôler avec Samba** demande un contrôle distinct avec `testparm` déjà installé. Il utilise une copie temporaire et affiche son résultat séparément. Modifier le formulaire invalide ce résultat ; aucun contrôle n’est lancé automatiquement par la préparation.

Le raccourci `Ctrl+Q` ferme l’application sur Linux. Les contrôles utilisent les widgets GTK standards pour permettre la navigation au clavier ; le parcours complet et l’accessibilité restent à vérifier sur la fenêtre réelle.

## Consulter les partages d’un fichier

Dans **Partages**, choisir **Choisir une configuration…**, ou lire le fichier dans **Examiner une configuration**, puis utiliser **Afficher les partages du fichier**. Ce deuxième parcours demande un choix explicite : examiner un fichier ne remplace pas automatiquement les exemples.

La page affiche le chemin source, l’empreinte de la lecture et les réglages déclarés pour chaque section ordinaire : chemin, lecture seule, visibilité, accès invité, destinataires reconnus ou non résolus et noms des options non interprétées. Une liste absente, vide ou ambiguë reste distinguée. Aucun réglage global ou par défaut n’est appliqué pour combler une information inconnue.

La recherche porte sur le **nom et le chemin déclarés**, sans tenir compte de la casse ; les espaces en début et fin de recherche sont ignorés. Le menu propose toutes les déclarations, les réglages incomplets, les réglages ambigus ou les options/destinataires non pris en charge. La recherche se combine avec le filtre choisi. Une déclaration peut relever de plusieurs catégories, consultables séparément.

« Incomplet » désigne des réglages locaux absents ou un chemin vide ; cela ne prouve pas que la configuration effective de Samba est invalide. « Ambigu » couvre les répétitions, synonymes concurrents, booléens non reconnus et chemins nécessitant une interprétation. La catégorie « non pris en charge » couvre les options inconnues et destinataires non résolus. Une liste d’accès explicitement vide reste différente d’une liste absente.

Le compteur indique le nombre affiché sur le total lu. Une recherche sans résultat affiche un état vide, sans réintroduire d’autres déclarations. **Réinitialiser les filtres** rétablit toutes les déclarations du même fichier ; choisir ou recharger une source remet aussi les filtres à zéro. Les filtres sont désactivés sur les exemples, pendant une lecture et pour un inventaire bloqué.

Chaque carte explique les incertitudes et la vérification suivante, sans deviner de valeur ni modifier le fichier. **Préparer une modification** ouvre directement le formulaire du même partage lorsque le moteur peut reprendre ses réglages. Sinon, le bouton reste désactivé et la raison est affichée. Le moteur vérifie aussi les contraintes du rédacteur : un synonyme compris à l’inspection peut rester refusé pour une modification automatique.

**Voir le rapport et préparer un aperçu** reste disponible pour consulter la déclaration dans le rapport. La relecture de source avant génération d’un aperçu est conservée ; l’activation du bouton ne prouve pas que le fichier est resté inchangé. Aucun aperçu n’est appliqué.

**Recharger le fichier** demande une nouvelle lecture et retire les anciennes cartes pendant son exécution. Une erreur ou une annulation laisse un état vide expliqué, sans réafficher un ancien fichier ou le remplacer silencieusement par des exemples. Un inventaire bloqué affiche ses explications et ne signifie pas que le serveur n’a aucun partage.

**Afficher les exemples** rétablit les cartes fictives et leurs actions, tout en conservant le rapport choisi dans sa rubrique tant qu’il n’est pas effacé ou remplacé. Le tableau de bord et la matrice des accès restent fictifs. Les deux sources ne sont pas fusionnées.

L’affichage est une lecture ponctuelle : le fichier n’est pas surveillé en continu. La page n’inspecte ni les dossiers partagés, ni les permissions Linux, ni les ACL, ni le réseau. Effacer le rapport efface aussi les déclarations affichables du fichier.

## Export d’un rapport

**Exporter un rapport Markdown…** est disponible après un examen, ainsi que dans la page Partages pour un fichier chargé. Une fenêtre montre le contenu complet et signale les chemins et identifiants inclus avant de proposer **Choisir où enregistrer…**. Le nom doit être nouveau, avec l’extension `.md` ; aucune destination existante n’est remplacée.

L’export contient l’inventaire complet, même si la page Partages est filtrée. Changer ou effacer la source invalide l’aperçu et les réponses tardives du sélecteur. Aucun fichier n’est créé par la simple ouverture ou fermeture de cet aperçu. Voir le [guide d’export](export-rapport.md).

## Organisation du code

- `presentation.py` construit les données d’écran et filtre les résultats, sans dépendre de GTK.
- `report_export.py` prépare le Markdown et enregistre explicitement un nouveau fichier ; `gtk_report.py` gère son aperçu et le choix de destination.
- `gui.py` vérifie les dépendances optionnelles et lance la fenêtre.
- `gtk_app.py` contient l’application, les pages et les interactions GTK.
- `gtk_setup.py` contient la page de préparation d’installation ; `setup.py` construit le même plan pour les deux interfaces.
- `gtk_firewall.py` contient le formulaire réseau ; `firewall.py` valide le périmètre et construit les intentions communes au terminal et à GTK.
- `diagnostic.py`, `access.py` et `demo.py` restent la source commune des informations pour le terminal et le graphique.

GTK est chargé seulement pour la commande `gui`. Le moteur et les commandes terminal ne dépendent pas de PyGObject. La fenêtre ne propose aucune action privilégiée et ne demande jamais `sudo`.

## Vérification sur un environnement graphique autorisé

Les tests ordinaires vérifient les filtres, les compteurs, les explications, la cohérence avec les rapports du terminal et les erreurs de lancement. Ils ne construisent pas de widgets.

Trente-quatre tests natifs sont prévus pour construire la fenêtre et vérifier la navigation, les formulaires, les sources et les résultats de contrôle. Ils sont ignorés par défaut. Pour les exécuter avec les dépendances déjà disponibles et une session graphique accessible, depuis la racine du dépôt :

```sh
SAMBAPILOT_GTK_TESTS=1 python3 -B -m unittest discover -s tests -p 'test_gtk_integration.py' -v
```

Vérifier aussi manuellement :

1. La lisibilité à différentes tailles de fenêtre et avec les thèmes des trois distributions.
2. Le parcours au clavier dans la barre latérale et les filtres.
3. Le bouton « Examiner les conflits » et le détail de `alex / Famille`.
4. Le filtrage d’un partage et la recherche sans résultat, puis la réinitialisation.
5. La distinction entre les refus établis et les accès inconnus.
6. Le bandeau de démonstration sur les pages d’exemples et le bandeau de lecture seule dans l’examen de configuration.
7. La préparation d’un partage, son aperçu, la modification d’un champ puis l’annulation.
8. La modification et le retrait d’un partage fictif, sans changement des exemples existants.
9. Le choix puis l’annulation d’un fichier de configuration, les erreurs de lecture et l’effacement du rapport, sans modification des exemples.
10. Le passage d’un fichier choisi à un aperçu, le refus si le fichier change, puis l’annulation ou le retour à un exemple sans mélange des sources.
11. La demande explicite de contrôle Samba, le cas d’un outil absent et l’invalidation après modification du formulaire.
12. Les scénarios de préparation d’installation, le constat local explicitement demandé et le retour à un exemple sans affichage d’un résultat devenu obsolète.
13. Le formulaire de pare-feu sans valeur présélectionnée, le choix de zone firewalld, les erreurs et l’invalidation après modification ou annulation.

14. Dans Partages, choisir un fichier, vérifier les recherches combinées aux catégories, les résultats vides et la réinitialisation, puis préparer directement une modification prise en charge. Vérifier les motifs de refus, le retour aux exemples, le rechargement et l’annulation sans conserver les anciennes cartes.

15. Modifier extérieurement un fichier de travail pendant une préparation, constater le refus de l’aperçu, relire sans perdre les champs, examiner la comparaison, adopter puis générer un nouvel aperçu. Vérifier le refus après un second changement et l’abandon des lectures obsolètes après annulation.
16. Ouvrir l’aperçu du rapport, vérifier les informations incluses et le mode fictif/fichier, enregistrer vers un nouveau nom, refuser un nom existant, annuler et changer de source avant une réponse du sélecteur. Utiliser uniquement des fichiers de travail choisis explicitement.

Ces vérifications ne demandent aucune installation ni application de configuration. Toute installation préalable de dépendances doit recevoir une autorisation distincte.

## Références

- [PyGObject : application GTK en Python](https://pygobject.gnome.org/getting_started.html).
- [GTK : application et cycle de vie des fenêtres](https://docs.gtk.org/gtk4/class.Application.html).
- [GTK : navigation avec StackSidebar](https://docs.gtk.org/gtk4/class.StackSidebar.html).
- [GTK : initialisation sans arrêt brutal si l’affichage est indisponible](https://docs.gtk.org/gtk4/func.init_check.html).
- [GTK : texte indicatif de recherche, disponible depuis GTK 4.10](https://docs.gtk.org/gtk4/method.SearchEntry.set_placeholder_text.html).
