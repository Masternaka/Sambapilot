# Interface graphique de SambaPilot

## État actuel

La première interface native GTK est codée. Les pages de gestion fonctionnent en démonstration, avec les mêmes rapports et règles que le terminal. Une rubrique indépendante peut lire un fichier choisi explicitement. Aucun compte, aucune permission et aucun réglage système ne sont modifiés par les actions de cette fenêtre.

L’affichage réel reste à vérifier dans un environnement disposant de GTK et d’une session graphique. Il n’a pas été validé visuellement pendant ce développement sur macOS.

## Lancement

Prérequis déjà installés pour l’interpréteur utilisé : Python 3.9 ou ultérieur, PyGObject et GTK **4.10 ou ultérieur**. Le terminal reste utilisable sans GTK. Ces dépendances ne sont ni installées ni téléchargées par SambaPilot.

Depuis la racine du dépôt :

```sh
cd sambapilot
python3 -B -m sambapilot gui --demo
```

Sur la machine cible, utiliser l’interpréteur Python ayant accès aux bibliothèques GTK installées. Une installation dans un autre environnement Python ne garantit pas leur disponibilité dans l’interpréteur courant.

Si PyGObject, GTK ou la session graphique sont indisponibles, la commande affiche un message sur la sortie d’erreur et retourne le code `3`. Le drapeau `--demo` est obligatoire ; son absence retourne le code `2` sans ouvrir la fenêtre.

## Navigation

| Rubrique | Fonctions de cette version |
| --- | --- |
| Tableau de bord | Indicateurs fictifs, état du service d’exemple, accès direct à la matrice et au conflit de permissions. |
| Installation | Plans descriptifs d’exemple ou constat local explicitement demandé, sans installation. |
| Partages | Dossiers fictifs, raccourci vers leurs accès et actions pour préparer une création, une modification ou un retrait. |
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

Après un aperçu, **Contrôler avec Samba** demande un contrôle distinct avec `testparm` déjà installé. Il utilise une copie temporaire et affiche son résultat séparément. Modifier le formulaire invalide ce résultat ; aucun contrôle n’est lancé automatiquement par la préparation.

Le raccourci `Ctrl+Q` ferme l’application sur Linux. Les contrôles utilisent les widgets GTK standards pour permettre la navigation au clavier ; le parcours complet et l’accessibilité restent à vérifier sur la fenêtre réelle.

## Organisation du code

- `presentation.py` construit les données d’écran et filtre les résultats, sans dépendre de GTK.
- `gui.py` vérifie les dépendances optionnelles et lance la fenêtre.
- `gtk_app.py` contient l’application, les pages et les interactions GTK.
- `gtk_setup.py` contient la page de préparation d’installation ; `setup.py` construit le même plan pour les deux interfaces.
- `gtk_firewall.py` contient le formulaire réseau ; `firewall.py` valide le périmètre et construit les intentions communes au terminal et à GTK.
- `diagnostic.py`, `access.py` et `demo.py` restent la source commune des informations pour le terminal et le graphique.

GTK est chargé seulement pour la commande `gui`. Le moteur et les commandes terminal ne dépendent pas de PyGObject. La fenêtre ne propose aucune action privilégiée et ne demande jamais `sudo`.

## Vérification sur un environnement graphique autorisé

Les tests ordinaires vérifient les filtres, les compteurs, les explications, la cohérence avec les rapports du terminal et les erreurs de lancement. Ils ne construisent pas de widgets.

Dix-sept tests natifs sont prévus pour construire la fenêtre et vérifier la navigation, les formulaires, les sources et les résultats de contrôle. Ils sont ignorés par défaut. Pour les exécuter avec les dépendances déjà disponibles et une session graphique accessible, depuis le dossier `sambapilot` :

```sh
SAMBAPILOT_GTK_TESTS=1 python3 -B -m unittest discover -s tests -p 'test_gtk_integration.py' -v
```

Vérifier aussi manuellement :

1. La lisibilité à différentes tailles de fenêtre et avec le thème Omarchy.
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

Ces vérifications ne demandent aucune installation ni application de configuration. Toute installation préalable de dépendances doit recevoir une autorisation distincte.

## Références

- [PyGObject : application GTK en Python](https://pygobject.gnome.org/getting_started.html).
- [GTK : application et cycle de vie des fenêtres](https://docs.gtk.org/gtk4/class.Application.html).
- [GTK : navigation avec StackSidebar](https://docs.gtk.org/gtk4/class.StackSidebar.html).
- [GTK : initialisation sans arrêt brutal si l’affichage est indisponible](https://docs.gtk.org/gtk4/func.init_check.html).
- [GTK : texte indicatif de recherche, disponible depuis GTK 4.10](https://docs.gtk.org/gtk4/method.SearchEntry.set_placeholder_text.html).
