# Recette sur Arch Linux, Debian et Fedora

## Quand l’utiliser

Cette recette est à répéter sur Arch Linux, Debian et Fedora, avec un ordinateur cible disponible, une session graphique et les dépendances déjà présentes pour l’interpréteur Python choisi. Elle ne lance aucune installation. Les premières étapes se font depuis les sources, après un run CI réussi sur le commit à examiner.

Les écritures de travail ci-dessous concernent uniquement un dossier temporaire et les exports explicitement choisis. Les modifications de paquets, services, comptes, permissions, pare-feu, confiance des dépôts de paquets et configuration active restent hors de cette recette.

## Parcours court pour le premier essai — environ dix minutes

Attendre une CI verte sur **le même commit** que celui testé. Avec les dépendances déjà présentes, lancer depuis la racine :

```sh
python3 -B -m sambapilot gui --demo
```

1. Vérifier le logo, la lisibilité et la navigation au clavier. Réduire la fenêtre : les commandes et résultats doivent rester accessibles.
2. Dans Partages, ouvrir « Diagnostic de ce partage… » sur Famille. Vérifier la source fictive, les droits inconnus et les trois symptômes.
3. Saisir `serveur.example` pour préparer les adresses. Copier une adresse dans un éditeur, sans ouvrir de connexion ; effacer le serveur doit désactiver la copie.
4. Indiquer le point `/srv/partages`, demander un volume fictif puis changer le point attendu : le constat précédent doit disparaître. Revenir aux exemples doit fermer la fiche.
5. En création de partage, préremplir un profil, choisir explicitement les identités puis demander un aperçu. Vérifier que les valeurs déjà saisies sont conservées et qu'aucun changement n'est appliqué.

Pour chaque étape, noter **Réussi**, **Échec** ou **Non exécuté**, avec le commit et une capture en cas de problème. Un parcours fictif réussi ne valide pas une connexion Samba. Les lectures de fichiers choisis, les contrôles locaux et les essais réseau seront des étapes séparées ; le parcours détaillé ci-dessous prépare les deux premières.

## Préparer le dossier de travail

Depuis la racine du dépôt, conserver le commit examiné et préparer une copie fictive, sans lire `/etc/samba/smb.conf` :

```sh
git rev-parse HEAD
python3 --version
SAMBAPILOT_RECIPE_DIR="$(mktemp -d)"
python3 -B - "$SAMBAPILOT_RECIPE_DIR" <<'PY'
from pathlib import Path
import sys
from sambapilot.demo import demo_configuration
root = Path(sys.argv[1])
with (root / "smb.conf").open("xb") as stream:
    stream.write(demo_configuration().encode("utf-8"))
print("Dossier de recette :", root)
PY
```

Noter ce chemin pour choisir ensuite le fichier dans GTK. Utiliser uniquement cette copie pour les éditions extérieures et les essais d’export. Ne pas saisir de données personnelles pour cette première recette.

## Vérifications automatisées

Avec Python et make déjà disponibles :

```sh
make check test demo demo-backup
```

Les tests ordinaires ignorent les deux suites natives lorsqu’elles ne sont pas demandées. Ce résultat ne valide pas l’interface. Lorsque GTK4, PyGObject, une session graphique et `testparm` sont déjà disponibles, exécuter :

```sh
make test-native
```

Cette cible active les deux suites natives et échoue si une suite est absente, si un test est ignoré ou si une dépendance manque. Si les prérequis manquent, noter **Non exécuté** ; toute installation préalable demande une intervention séparée et autorisée.

## Parcours graphique

```sh
python3 -B -m sambapilot gui --demo
```

| Scénario | Résultat à observer |
| --- | --- |
| Diagnostic par partage | Depuis les exemples puis un fichier fictif, vérifier la source/date, les incertitudes, les adresses et le volume simulé réservé aux exemples. Modifier les champs puis recharger la source : aucun ancien constat ne doit revenir. Les sondes locales restent hors de cette recette sans demande explicite. |
| Volumes | Dans Maintenance, consulter les cinq scénarios fictifs et vérifier l’invalidation des retours après changement de chemin/source. Les essais locaux sur un vrai disque seront demandés séparément, sans montage ou démontage implicite. |
| Profils de partage | En création, préremplir les trois profils ; vérifier la conservation des saisies, l’absence d’identité ajoutée, les cases modifiables et l’aperçu demandé séparément. En modification/retrait, vérifier le menu désactivé. |
| Fiche de connexion | Sur un exemple puis un fichier fictif : préparer les adresses, copier dans un éditeur sans ouvrir de connexion, modifier le serveur pour effacer l’aperçu, puis changer de source pour fermer la fiche. |
| Diagnostic local et dépannage | Demander le constat local, vérifier la distribution et son service Samba attendu, essayer les trois symptômes puis revenir aux exemples ; aucune matrice fictive ne devient réelle. |
| Démarrage | Fenêtre lisible dans la session Wayland ou X11 de la cible, bandeau fictif, navigation latérale, absence de demande de privilèges. |
| Exemples et accès | Cartes de partages, filtres des accès et conflit expliqué ; la réinitialisation rétablit les exemples. |
| Fichier fictif | Choisir le `smb.conf` du dossier de recette ; la page Partages affiche son chemin, son empreinte et ses déclarations, avec des droits effectifs inconnus. |
| Recherche et catégories | Recherche par nom/chemin, filtre combiné, état sans résultat, réinitialisation et retour aux exemples sans mélange des sources. |
| Préparation | Modifier les réglages d’un partage de la copie ; la comparaison est en mémoire et la copie n’est pas écrite. Une saisie invalide abandonne l’ancien aperçu. |
| Changement extérieur | Éditer seulement la copie avec un éditeur. L’aperçu devient caduc ; « Recharger sans perdre ma saisie » montre les différences avant adoption. Les textes et cases restent saisis ; un nouvel aperçu est requis. |
| Seconde modification | Changer à nouveau la copie entre relecture et adoption ; la reprise est refusée et la saisie conservée. |
| Export Markdown | Examiner l’aperçu et exporter vers un nouveau `.md` dans le dossier de recette. Les identifiants/chemins sont signalés, les options inconnues restent sans valeur brute. Un nom existant est refusé. |
| Annulation et fermeture | Annuler une sélection et changer de source pendant une opération ; aucun résultat ancien ne remplace la source courante, aucun export tardif n’est créé. Fermer avec `Ctrl+Q`. |
| Lisibilité et clavier | Tester une petite fenêtre, les libellés longs, la navigation par Tab et les contrastes du thème. Consigner les problèmes sans les déduire d’un succès des tests. |

Le contrôle « Contrôler avec Samba » reste explicite et nécessite `testparm` déjà disponible. L’utiliser seulement sur la configuration fictive pour cette recette. Une acceptation ne certifie pas les comptes ni les accès réseau.

La démonstration `make demo-backup` utilise son propre laboratoire temporaire. Elle ne valide pas des sauvegardes utilisateur durables ou une restauration de configuration active.

## Compte rendu à conserver

Noter : date, commit, version de Python, versions GTK/PyGObject/Samba disponibles, session Wayland ou X11, thème, résultats de commandes et statut de chaque scénario (**Réussi**, **Échec**, **Non exécuté**). Pour une anomalie, conserver les étapes et, si utile, une capture sans données personnelles.

Les essais du paquet installé et de sa désinstallation doivent être planifiés séparément dans un environnement autorisé, après téléchargement et vérification des artefacts CI. L’activation de `master-archrepo` n’est pas incluse dans cette recette.

Voir le [bilan actuel](validation-socle.md) et le [guide de CI](verification-automatisee.md) pour les preuves encore attendues.
