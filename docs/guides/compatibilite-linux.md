# Compatibilité Arch Linux, Debian et Fedora

## Cibles du projet

Le moteur et le terminal utilisent Python 3.9 ou ultérieur, sans dépendance Python d’exécution. GTK est optionnel et exige GTK **4.10 ou ultérieur**, PyGObject et une session graphique. Une distribution disposant d’une version plus ancienne de GTK peut utiliser le terminal, mais ne satisfait pas les prérequis graphiques. La première cible Debian de la CI est Debian 13.

Les profils suivants sont implémentés. Les tests locaux simulent leurs réponses ; une exécution réussie de la CI et des essais graphiques sur les cibles restent nécessaires avant de déclarer la compatibilité native validée.

| Profil | Gestionnaire / requête locale | Paquets examinés | Unités Samba |
| --- | --- | --- | --- |
| Arch Linux | pacman / `pacman --query` | `samba`, `smbclient` | `smb.service`, `nmb.service` |
| Debian | apt / `dpkg-query --show` | `samba`, `samba-common-bin`, `smbclient` | `smbd.service`, `nmbd.service` |
| Fedora | dnf / `rpm --query` | `samba`, `samba-common-tools`, `samba-client` | `smb.service`, `nmb.service` |

Les noms proviennent des listes officielles de fichiers : [Arch Samba](https://archlinux.org/packages/extra/x86_64/samba/files/), [Arch smbclient](https://archlinux.org/packages/extra/x86_64/smbclient/files/), [Debian Samba](https://packages.debian.org/trixie/amd64/samba/filelist), [Debian outils communs](https://packages.debian.org/trixie/amd64/samba-common-bin/filelist), [Fedora Samba](https://packages.fedoraproject.org/pkgs/samba/samba/fedora-43.html) et [Fedora outils communs](https://packages.fedoraproject.org/pkgs/samba/samba-common-tools/fedora-43.html). Ces références servent à définir les profils, sans figer une version de Samba.

## Détection et limites

`/etc/os-release` fournit `ID`, puis `ID_LIKE` si l’identité exacte n’est pas reconnue. Une seule famille connue est acceptée ; des familles contradictoires restent inconnues. Une filiation ne certifie pas le fonctionnement d’une distribution dérivée. Sur un Linux inconnu, les outils et services de pare-feu peuvent être repérés, mais aucune unité Samba propre à une distribution n’est supposée et aucun paquet n’est interrogé. Le plan d’installation reste bloqué.

Les sondes ne recherchent aucun marqueur de bureau ou de configuration personnelle. Elles utilisent uniquement les chemins système `/usr/bin` et `/usr/sbin`, des arguments fermés, un délai de trois secondes, aucun shell, aucune élévation de droits et aucune saisie interactive. La consultation de paquets utilise la base locale uniquement : ni apt ni dnf ne sont exécutés et aucun dépôt n’est synchronisé. Les états incomplets ou les erreurs restent inconnus. Les formats sont documentés par [dpkg-query](https://manpages.debian.org/trixie/dpkg/dpkg-query.1.en.html) et [RPM](https://rpm.org/docs/4.20.x/man/rpm.8.html).

Les requêtes systemd peuvent être indisponibles, notamment dans un conteneur : l’état reste alors inconnu. Un service actif ne prouve ni l’authentification, ni les permissions, ni l’accès réseau. SELinux, AppArmor, les ACL et les règles effectives de pare-feu ne sont pas inspectés par ce lot. Aucune protection n’est désactivée.

## Démonstrations sans accès hôte

Depuis la racine du dépôt :

```sh
python3 -B -m sambapilot diagnostic --demo --distribution arch
python3 -B -m sambapilot diagnostic --demo --distribution debian
python3 -B -m sambapilot preparer-installation --demo --distribution fedora
python3 -B -m sambapilot depannage --demo --distribution fedora --symptom readonly
```

L’option `--distribution` exige `--demo`. Elle ne permet jamais de forcer un profil sur l’hôte réel. GTK propose les trois distributions pour les exemples du tableau de bord et des plans d’installation.

## JSON et distribution de l’application

Les rapports `diagnostic` et `preparer-installation` passent au schéma **2** : l’environnement contient `distribution_family`, `package_manager` et `samba_service`. Le précédent booléen réservé à Arch et le marqueur de bureau sont retirés. Les consommateurs doivent vérifier `schema_version`. Les autres schémas existants restent inchangés ; `depannage` introduit son propre schéma 1 avec un diagnostic de schéma 2 imbriqué.

Les sources et le wheel Python sont communs aux trois cibles. La seule recette de paquet natif actuellement préparée est celle d’Arch ; **aucun paquet `.deb` ou `.rpm` de SambaPilot n’est encore fourni**. Le [guide de distribution](distribution-linux.md) distingue les archives communes, la recette Arch et le futur dépôt personnel Arch. Aucune installation locale n’est réalisée par cette préparation.
