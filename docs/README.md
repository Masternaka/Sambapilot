# Documentation de SambaPilot

SambaPilot dispose d’un moteur commun au terminal et à GTK pour le diagnostic, l’examen de configuration et la préparation de changements. Les fonctions d’application système restent à développer. Toutes les commandes des guides se lancent depuis la racine du dépôt.

## Classement des documents

- `guides/` : fonctions utilisables, commandes et parcours GTK4.
- `conception/` : cahier des charges, architecture et propositions d’évolution.
- `validation/` : résultats de vérification datés et essais restant à effectuer.

Les nouveaux documents sont ajoutés dans la rubrique correspondante et référencés ici. Les sources restent dans `sambapilot/` et les tests dans `tests/`, à la racine.

## Utiliser les fonctions disponibles

| Guide | Contenu |
| --- | --- |
| [Présentation et démarrage](../README.md) | État du projet, prérequis, onze commandes, exemples et codes de sortie. |
| [Diagnostic par partage](guides/diagnostic-partage.md) | Déclarations et incertitudes, connexion, dépannage et constat de volume facultatif sur demande. |
| [Examen des volumes](guides/examen-volumes.md) | Point attendu, volume parent, lecture seule et métadonnées du dossier, sans montage ni activation. |
| [Fiche de connexion](guides/fiche-connexion.md) | Adresses Windows et SMB, instructions macOS/Linux, copie explicite et limites. |
| [Compatibilité Linux](guides/compatibilite-linux.md) | Profils Arch, Debian et Fedora, paquets, services, schémas JSON et limites. |
| [Diagnostic et dépannage](guides/diagnostic-depannage.md) | Tableau de bord local sur demande, exemples et pistes selon le symptôme. |
| [Distribution Python et paquet Arch](guides/distribution-linux.md) | Artefacts après un push, paquet Arch et étapes vers un dépôt personnel pacman. |
| [Interface graphique](guides/interface-graphique.md) | Prérequis GTK, huit rubriques, limites et parcours de vérification. |
| [Icône de l’application](guides/icones-application.md) | Dossier connecté, tailles PNG, ressources GTK et intégration au paquet Arch. |
| [Examen de configuration](guides/inspection-configuration.md) | Lecture d’un fichier choisi, déclarations locales et refus prudents. |
| [Préparation des partages](guides/preparation-partages.md) | Ajout, modification et retrait d’une déclaration, aperçu et comparaison. |
| [Profils de partage](guides/profils-partage.md) | Préréglages personnel, familial et médias, personnalisables et réservés aux créations. |
| [Simulation sauvegarde/restauration](guides/simulation-sauvegarde-restauration.md) | Laboratoire temporaire, intégrité des copies, aperçu et refus de restauration. |
| [Export Markdown](guides/export-rapport.md) | Aperçu et enregistrement explicite de l’inventaire, informations incluses et refus d’écrasement. |
| [Contrôle avec Samba](guides/validation-samba.md) | Demande explicite avec `testparm`, copie temporaire et interprétation du résultat. |
| [Préparation d’installation](guides/preparation-installation.md) | Plans descriptifs, scénarios fictifs et constat local sans installation. |
| [Préparation du pare-feu](guides/preparation-pare-feu.md) | Périmètre déclaré et intentions SMB, sans lecture ni application de règles. |

Le diagnostic et la matrice fictive des accès sont présentés dans le README. Les règles de la matrice sont détaillées dans les [recommandations](conception/recommandations.md).

## Comprendre et poursuivre le projet

| Document | Rôle |
| --- | --- |
| [Cahier des charges](conception/cahier-des-charges.md) | Objectifs et exigences, y compris les fonctions futures. |
| [Architecture et feuille de route](conception/architecture-et-roadmap.md) | Modules actuels, décisions techniques et étapes restantes. |
| [Recommandations](conception/recommandations.md) | État de la vue des accès et propositions complémentaires. |
| [CI et distribution](validation/verification-automatisee.md) | Jobs préparés, tests natifs optionnels et contrôles du paquet Python. |
| [Bilan actuel de validation](validation/validation-socle.md) | Résultats locaux, correspondance fonctionnalités/tests, preuves CI attendues et première reprise. |
| [Recette courte Linux](validation/recette-linux.md) | Essais futurs depuis les sources, sur une copie fictive, avec résultats attendus. |
| [Historique des lots](validation/historique-validation-2026-11-09.md) | Vérifications successives conservées ; les anciens totaux ne décrivent pas l’état actuel. |
| [Guide des assistants](../AGENTS.md) | Autorisation préalable, organisation, conventions et vérifications. |

Le lot du 13 novembre 2026 ajoute les profils Arch, Debian et Fedora et le diagnostic/dépannage partagé. Les tests ordinaires sont contrôlés localement ; les suites natives et la CI restent à confirmer. Le [bilan actuel](validation/validation-socle.md) conserve les résultats datés et leurs limites.

Les liens vers les documentations externes des composants sont des références techniques ; cette revue du dépôt ne constitue pas une nouvelle vérification de leur contenu.
