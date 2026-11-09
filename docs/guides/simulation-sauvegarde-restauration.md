# Simuler une sauvegarde et une restauration

## Objectif et périmètre

Le module `sambapilot/backup_simulation.py` éprouve le mécanisme sur un fichier fictif, créé dans un dossier temporaire privé qu’il possède. Il reçoit un contenu UTF-8 en mémoire, jamais un chemin vers une configuration à sauvegarder ou à restaurer. Le scénario de démonstration utilise les exemples déjà fournis par SambaPilot.

Le laboratoire ne consulte pas `/etc/samba/smb.conf`, ne lance aucun programme externe, ne recharge aucun service et ne propose aucune restauration de fichier système. Il n’ajoute pas de bouton d’application dans GTK. Les sauvegardes de configurations réelles et leur restauration restent à développer et à valider séparément.

## Lancer la démonstration

Avec Python et make déjà disponibles, depuis la racine :

```sh
make demo-backup
```

Ou directement :

```sh
python3 -B -m sambapilot.backup_simulation --demo
```

`--demo` est obligatoire. Aucun argument `--config`, chemin source ou destination n’est accepté. La commande crée uniquement son propre dossier temporaire, affiche une comparaison fictive et le résultat, puis supprime ce dossier et ses sauvegardes à la fin. Elle n’installe aucune dépendance.

Codes de sortie : `0` si le scénario se termine ; `2` pour des arguments invalides ou un échec de simulation. Un code `0` ne valide pas une restauration sur Omarchy.

## Parcours vérifié

1. Créer un `smb.conf` fictif dans le laboratoire.
2. Créer une sauvegarde datée UTC, avec nom unique, copie exacte des octets, empreinte SHA-256, taille et métadonnées marquées `simulation`.
3. Modifier le fichier fictif, sans changer la sauvegarde.
4. Vérifier la sauvegarde et préparer un aperçu des différences entre le fichier fictif et les octets sauvegardés.
5. Confirmer explicitement la restauration fictive. L’aperçu reste marqué `can_apply: false` et ne peut pas être utilisé par un moteur d’application système.
6. Vérifier à nouveau l’intégrité de la sauvegarde et l’identité/contenu du fichier fictif courant.
7. Sauvegarder l’état qui va être remplacé, préparer un fichier complet, vérifier encore la cible puis effectuer le remplacement dans le laboratoire.
8. Vérifier l’empreinte du résultat. La sauvegarde de l’état remplacé permet de simuler un retour vers cet état.

La démonstration confirme elle-même son scénario prédéfini, parce qu’il porte exclusivement sur ses données fictives. Le moteur exige néanmoins une confirmation explicite et teste le refus lorsque celle-ci est absente. Aucun accord pour une future modification de Samba n’est déduit de ce scénario.

## Fichiers et protection

Chaque sauvegarde possède un dossier privé `0700`, une copie `smb.conf` et un fichier `metadata.json` privés `0600` sur les systèmes POSIX utilisés. La copie conserve exactement les octets UTF-8 d’origine, notamment le BOM et les fins de ligne CRLF lorsqu’ils sont présents. Les noms uniques et les créations exclusives empêchent de remplacer une sauvegarde existante.

L’aperçu ne modifie aucun fichier et ne crée pas de sauvegarde supplémentaire. Une tentative de restauration confirmée consomme son aperçu : après un succès ou un refus, il faut préparer une nouvelle comparaison avant de réessayer. Les sauvegardes déjà valides sont conservées jusqu’à la fermeture du laboratoire, y compris après un échec de restauration.

Les fichiers ordinaires appartenant au laboratoire sont les seules entrées autorisées. Les liens symboliques, liens physiques multiples, dossiers utilisés à la place de fichiers et parents remplacés par des liens sont refusés. Le contenu est limité à 1 Mio et doit être UTF-8. Les métadonnées de sauvegarde sont contrôlées contre l’enregistrement en mémoire ; le laboratoire ne propose pas d’import de sauvegardes externes.

Les sauvegardes et les comparaisons contiennent le contenu fictif complet. Ne pas confondre ce laboratoire avec l’export Markdown de diagnostic, qui exclut le fichier brut et les valeurs d’options non interprétées.

## Erreurs simulées

| Situation | Résultat attendu |
| --- | --- |
| Sauvegarde ou métadonnées altérées | Refus avant restauration ; fichier fictif courant préservé. |
| Fichier modifié après l’aperçu | Refus et nouvelle comparaison nécessaire. Un remplacement avec les mêmes octets reste détecté par l’identité du fichier. |
| Sauvegarde ou aperçu d’un autre laboratoire | Refus avant utilisation. |
| Cible ou sauvegarde remplacée par un lien | Refus sans lire la cible du lien. |
| Échec de création de sauvegarde | Nettoyage des éléments incomplets créés par l’opération ; conservation des sauvegardes antérieures. |
| Échec d’écriture du fichier préparé | Fichier courant préservé, élément temporaire nettoyé. |
| Échec du remplacement avant réalisation | Fichier courant et sauvegardes conservés ; nouvelle tentative possible après un nouvel aperçu. |
| Changement externe pendant la préparation | Détection lors de la dernière vérification ; état extérieur conservé. |

Le remplacement final est limité au fichier fictif et utilise un fichier préparé dans le même dossier. Un verrou interne sérialise les opérations du laboratoire. **Ce n’est pas un verrouillage contre d’autres programmes** : la fenêtre entre la dernière vérification et le remplacement, les arrêts brutaux et la durabilité après panne ne sont pas validés pour un usage système.

## Limites pour une future restauration réelle

Les sauvegardes de ce laboratoire sont jetables et leur catalogue reste en mémoire : elles disparaissent quand le laboratoire est fermé. Ce mécanisme ne permet pas une récupération après redémarrage de l’application. Il ne sauvegarde pas les propriétaires, groupes, ACL ou paramètres des services et ne garantit pas la validité Samba du contenu restauré.

Une future intégration devra définir le stockage durable protégé, la validation Samba, les confirmations, les métadonnées à préserver, la coordination des écritures et les résultats des échecs après modification. Ces étapes nécessiteront des essais sur un environnement autorisé avant de proposer une restauration de configuration active.

## Validation locale

Les tests utilisent seulement des contenus fictifs et des dossiers temporaires. Ils couvrent la fidélité des octets, les permissions des fichiers privés, les dates, la comparaison sans écriture, la confirmation, la restauration et le retour vers l’état remplacé, les altérations, les conflits de fichiers, les erreurs, les liens et le nettoyage.

Les refus de lecture sont simulés pour rester déterministes sans changer les permissions système. Les échecs d’écriture et de remplacement sont injectés dans les opérations du laboratoire. Ces tests ne prouvent ni le comportement des droits administrateur ni celui de Samba ou d’un système de fichiers distant.
