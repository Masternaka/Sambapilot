# Diagnostic et assistant de dépannage

## Examiner un constat

Le tableau de bord GTK démarre avec un exemple fictif. Les menus choisissent Arch, Debian ou Fedora et l’un des scénarios sans Samba, déjà installé ou accès restreint. Changer un menu retourne immédiatement aux données fictives.

Le bouton **Examiner cet ordinateur (lecture seule)** demande un constat local. Il consulte l’identité Linux, la présence des outils, les métadonnées de `/etc/samba/smb.conf` et les états systemd adaptés à la distribution. Il ne lit pas le contenu de la configuration, n’interroge pas les comptes et ne réalise aucun accès réseau. Les bases de paquets ne sont consultées que dans la rubrique distincte **Installation**, sur demande.

La consultation du tableau de bord a lieu dans un fil séparé. L’ancien résultat et les pistes de dépannage sont retirés pendant l’attente. Le bouton local est désactivé jusqu’au résultat ou au retour aux exemples. Les retours devenus obsolètes après un changement de source ou la fermeture sont ignorés. Le bandeau indique la source ; la date UTC affichée correspond à la production du rapport, pas à une surveillance continue.

Les autres pages conservent leurs sources propres. Un diagnostic local ne transforme pas la matrice des accès fictifs en inventaire réel et ne remplace pas un fichier choisi.

## Choisir un symptôme

| Symptôme | Pistes supplémentaires |
| --- | --- |
| Le partage n’apparaît pas | Connexion directe avec une adresse connue, nom du partage et visibilité déclarée. |
| L’accès est refusé | Identité utilisée, restrictions Samba et groupes autorisés. |
| Impossible d’écrire | Identité, réglages Samba, permissions Linux, ACL, traversée des parents et volume en lecture seule. |

Chaque résultat distingue un constat, un point à examiner et une information non vérifiée. Les pistes communes concernent le service, la configuration, le réseau et les protections SELinux/AppArmor. Elles n’affirment pas que ces contrôles ont été exécutés. Aucun mot de passe n’est demandé et aucune réparation n’est appliquée.

Changer le symptôme réutilise le même constat sans nouvelle sonde. Pour actualiser l’état local, demander un nouveau diagnostic.

## Terminal

```sh
python3 -B -m sambapilot diagnostic --demo --distribution debian
python3 -B -m sambapilot depannage --demo --distribution fedora --symptom invisible
python3 -B -m sambapilot depannage --demo restricted --symptom denied --json
```

Les commandes suivantes demandent explicitement une consultation de l’hôte :

```sh
python3 -B -m sambapilot diagnostic
python3 -B -m sambapilot depannage --local --symptom readonly
```

Pour `depannage`, `--demo` ou `--local` est obligatoire et les deux sont exclusifs. Les codes sont `0` pour un rapport Linux ou fictif produit, `2` pour une plateforme hors Linux ou des arguments invalides. Un code `0` ne signifie pas qu’une cause est trouvée ou qu’un accès fonctionne. Le JSON garde `can_apply: false`.

Les [profils Linux](compatibilite-linux.md) précisent les paquets, services et limites. Le rendu graphique et le parcours clavier restent à vérifier sur les trois cibles ; les tests locaux sans GTK ne les valident pas.
