# Profils de partage

## Périmètre

Les profils préremplissent les réglages d’un **nouveau partage**. Ils ne créent aucun dossier, compte ou groupe et n’attribuent aucune permission réelle. Les candidats passent par les validations et la comparaison habituelles ; `can_apply` reste faux.

| Profil | Clé terminal | Nom suggéré | Chemin suggéré | Accès proposé | Visible dans la liste |
| --- | --- | --- | --- | --- | --- |
| Personnel | `personal` | `Personnel` | `/srv/partages/personnel` | Lecture et écriture | Non |
| Familial | `family` | `Partage famille` | `/srv/partages/famille` | Lecture et écriture | Oui |
| Médias en lecture seule | `media` | `Mediatheque` | `/srv/partages/medias` | Lecture seule | Oui |

Ces noms et chemins sont des suggestions fixes ; aucun dossier personnel ou volume n’est inspecté. Le profil personnel recommande un compte choisi ; le familial recommande les comptes ou le groupe appropriés, sans inventer ces identités. Tous les profils exigent au moins un utilisateur ou un groupe avant de produire un aperçu. Les règles d’identité restent celles du moteur commun.

Les champs sont modifiables. Choisir un profil personnel ne garantit pas la confidentialité : masquer un partage ne bloque pas l’accès direct et ne remplace pas les restrictions Samba, les permissions Linux ou les ACL. L’accès invité reste désactivé dans les candidats.

## Terminal, y compris sans Linux

Les exemples suivants utilisent exclusivement une configuration fictive :

```sh
python3 -B -m sambapilot plan-partage --demo --action create --profile personal --user alex
python3 -B -m sambapilot plan-partage --demo --action create --profile family --group famille
python3 -B -m sambapilot plan-partage --demo --action create --profile media --group famille --json
```

Les identités `alex` et `famille` sont fictives ; aucune existence de compte ou de groupe n’est vérifiée. Aucune installation ni session Linux n’est nécessaire pour préparer ces exemples avec Python déjà disponible.

`--name` et `--path` remplacent les suggestions ; les comptes et groupes sont toujours fournis explicitement. Les choix de droits et de visibilité peuvent aussi être ajustés :

```sh
python3 -B -m sambapilot plan-partage --demo --action create --profile personal --name Travail --path /srv/travail --user alex --read-only --visible
```

`--writable` et `--read-only` s’excluent, de même que `--hidden` et `--visible`. Sans profil, les défauts habituels restent la lecture seule et la visibilité. Le nom reste obligatoire sans profil. La sortie JSON ajoute la clé `profile` seulement lorsqu’un profil est demandé ; le schéma du plan reste 1.

Avec `--config /chemin/vers/smb.conf` à la place de `--demo`, le fichier choisi est lu et relu comme pour toute préparation sur fichier. Un nom déjà présent est refusé sans écrasement. Les profils sont refusés pour `update` et `remove`, avant lecture du fichier ; ces actions exigent l’examen des réglages existants.

## GTK

Dans **Préparer un partage**, en création :

1. Choisir le profil dans le menu.
2. Sélectionner **Préremplir ce profil**. Les noms et chemins non vides restent saisis ; seuls les champs vides reçoivent une suggestion. Les cases de droits et de visibilité prennent les valeurs du profil. Les comptes et groupes déjà saisis restent identiques, même si une saisie doit encore être corrigée.
3. Vérifier tous les champs et choisir explicitement les identités autorisées.
4. Sélectionner **Générer l’aperçu** pour valider et examiner la comparaison.

Choisir un profil dans le menu invalide l’aperçu précédent, mais ne remplit pas les champs avant le clic sur le bouton. Le préremplissage invalide aussi les contrôles Samba et les reprises de source en attente ; il ne génère ni ne contrôle un candidat automatiquement. Les autres champs restent modifiables ensuite.

Le menu est désactivé pour la modification ou le retrait d’une déclaration. Ouvrir une autre préparation revient à **Saisie libre**. Aucun profil ne remplace la configuration source, ne modifie une déclaration existante ou ne contourne le refus d’une configuration complexe.

## Validation

Les tests ordinaires couvrent les défauts, les personnalisations, le refus d’identités absentes ou invalides, les noms en conflit et la conservation du BOM, des commentaires et des fins de ligne. Les tests GTK sont préparés pour le préremplissage, l’invalidation et le refus en modification/retrait. Le contrôle du paquet installé utilise également ces profils fictifs. Les tests natifs, le rendu et les permissions réelles restent à confirmer sur les cibles ; les processus simulés localement ne constituent pas une installation ou une preuve d’accès Samba.
