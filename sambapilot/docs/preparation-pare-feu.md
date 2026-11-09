# Préparer le périmètre du pare-feu

## Fonction disponible

Le terminal et la fenêtre GTK peuvent préparer les intentions de règles pour les accès SMB à partir d’un périmètre choisi explicitement. Le formulaire demande le gestionnaire, l’interface d’entrée et les réseaux ou appareils sources.

Ce plan **n’interroge ni ne modifie le pare-feu**. Il ne génère pas de commandes natives UFW, firewalld ou nftables et ne garantit pas l’effet d’un futur ajout de règles. Les champs `existing_rules_checked` et `can_apply` restent faux dans le JSON.

## Terminal

Depuis le dossier `sambapilot`, exemple de périmètre IPv4 déclaré :

```sh
python3 -B -m sambapilot plan-pare-feu --manager ufw --interface enp3s0 --source 192.168.1.0/24
```

Adapter l’interface et les réseaux à l’environnement souhaité : ces valeurs d’exemple ne sont pas détectées ni validées sur l’ordinateur.

Pour déclarer IPv4 et IPv6, répéter `--source` :

```sh
python3 -B -m sambapilot plan-pare-feu --manager ufw --interface enp3s0 --source 192.168.1.0/24 --source fd12:3456:789a::/64 --json
```

Pour firewalld, la zone doit aussi être choisie :

```sh
python3 -B -m sambapilot plan-pare-feu --manager firewalld --zone home --interface enp3s0 --source 192.168.1.0/24
```

Les gestionnaires déclarables sont `ufw`, `firewalld` et `nftables`. Leur présence et leur état effectif ne sont pas vérifiés par cette commande. Une zone est obligatoire pour firewalld et refusée pour les autres gestionnaires.

Le code `0` signifie que les intentions sont produites, pas que des ports sont ouverts ou que le gestionnaire les accepte. Le code `2` indique une demande invalide ou incomplète.

## Fenêtre GTK

Ouvrir **Pare-feu**, puis choisir :

1. Le gestionnaire envisagé.
2. Le nom de l’interface d’entrée.
3. Les sources en notation CIDR, séparées par des virgules.
4. La zone pour firewalld, si ce gestionnaire est choisi.
5. L’option NetBIOS uniquement si nécessaire.

Cliquer sur **Générer l’aperçu réseau**. Aucun gestionnaire, réseau ou nom d’interface n’est présélectionné. Le bandeau affiche **Périmètre déclaré · Aucun port ouvert**.

Modifier un champ efface le plan précédent. Une erreur ne conserve pas un ancien plan valide. **Annuler le périmètre** vide le formulaire et le résultat. Il n’existe aucun bouton d’application.

## Règles proposées et familles d’adresses

Par défaut, une intention d’autorisation entrante pour **TCP 445** est produite pour chaque source, sur l’interface choisie. Le port correspond au transport SMB direct standard ; les ports réellement configurés du serveur devront être vérifiés avant une application.

L’option `--legacy-netbios` ou la case NetBIOS ajoute **TCP 139 et UDP 137/138** aux seules sources IPv4 dans cette version. Une demande NetBIOS avec uniquement des sources IPv6 est refusée. Aucun port historique n’est ajouté implicitement.

IPv4 et IPv6 sont traités séparément. Pour un appareil unique, utiliser un préfixe `/32` en IPv4 ou `/128` en IPv6. Un plan sans IPv6 ne permet pas de conclure que les accès IPv6 existants sont bloqués.

Les mécanismes de découverte réseau et les transports non standard ne sont pas configurés par cet aperçu.

## Validation du périmètre déclaré

- Entre un et seize réseaux sources, avec une longueur de préfixe numérique explicite.
- Les bits d’hôte dans un réseau sont refusés : `192.168.1.5/24` n’est pas élargi automatiquement à `192.168.1.0/24`.
- Les sources en double ou qui se chevauchent sont refusées, y compris après normalisation de l’écriture IPv6.
- Les noms DNS, les masques textuels, les portées IPv6 `%interface` et les valeurs à interpréter par un shell sont hors périmètre.
- Les ouvertures `/0`, les plages recouvrant les adresses non spécifiées, la boucle locale, le lien local, le multicast et certaines adresses spéciales sont refusées. Les adresses IPv4 mappées en IPv6 sont hors périmètre.
- Le nom d’interface suit un format simple de 1 à 15 caractères, sans joker. La zone firewalld suit un format simple de 1 à 17 caractères.

Ces validations contrôlent le format et certains cas ambigus. Elles ne prouvent pas que les réseaux sont privés, locaux ou associés à l’interface choisie. L’existence de l’interface, du gestionnaire et de la zone reste à vérifier.

Les réseaux sont normalisés sans élargir leur plage. Une empreinte identifie le périmètre et chaque intention porte un identifiant stable. Cet identifiant n’est pas la preuve qu’une règle est déjà installée ou appartient à SambaPilot.

## Vérifications nécessaires avant toute application

Ajouter une autorisation ne retire aucune règle plus large déjà présente. Le plan ne garantit donc pas un accès limité exclusivement aux sources choisies.

Il faudra notamment :

- lire les règles effectives et leur ordre, puis repérer les autorisations plus larges et les conflits ;
- confirmer le gestionnaire, l’interface, les réseaux et les ports Samba ;
- pour firewalld, examiner les interfaces et les sources associées à la zone avant de traduire les intentions ;
- pour nftables, identifier les tables, les chaînes, les hooks et les priorités existants ;
- choisir la persistance et la méthode de retrait des seules règles ajoutées ;
- présenter les changements natifs, sauvegarder les réglages et obtenir une autorisation explicite.

Aucun pare-feu ne sera désactivé et aucune politique globale ne sera remplacée implicitement.

## Vérification réalisée

Les tests automatiques couvrent les périmètres IPv4/IPv6, les appareils uniques, les doublons et chevauchements, les noms invalides, les zones, les règles NetBIOS optionnelles et la stabilité des identifiants. Ils vérifient que la commande ne lit aucun fichier, ne lance aucun programme et ne crée aucune connexion réseau.

Les essais natifs GTK restent à effectuer. Aucun gestionnaire réel, ordre de règles ou accès Samba n’est validé par ces tests. La lecture des règles existantes, la traduction native et l’application sont des étapes ultérieures.

Références : [transports et ports Samba](https://www.samba.org/samba/docs/current/man-html/smb.conf.5.html), [ports NetBIOS historiques dans le guide Samba](https://www.samba.org/samba/docs/Samba-HOWTO-Collection.pdf), [zones firewalld](https://firewalld.org/documentation/man-pages/firewalld.zone.html), [syntaxe des règles UFW](https://manpages.ubuntu.com/manpages/noble/man8/ufw.8.html).
