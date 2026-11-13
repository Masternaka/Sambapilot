# Icône de SambaPilot

L’option 1, choisie le 13 novembre 2026, représente un dossier bleu portant trois nœuds réseau turquoise. L’image a été créée avec l’outil intégré de génération d’images, puis conservée sans retouche visuelle.

![Icône SambaPilot](../../sambapilot/assets/icons/hicolor/128x128/apps/io.github.sambapilot.SambaPilot.png)

## Fichiers fournis

- [Original transparent](../../sambapilot/assets/icons/sambapilot-original.png) : PNG de 1254 × 1254 pixels, conservé comme référence.
- Déclinaisons PNG transparentes de 16, 24, 32, 48, 64, 128, 256 et 512 pixels, sous `sambapilot/assets/icons/hicolor/<taille>x<taille>/apps/`.
- Identifiant d’icône : `io.github.sambapilot.SambaPilot`, identique à celui de l’application GTK.

Les tailles sont dérivées avec l’outil macOS `sips`, sans dépendance ajoutée au projet. L’original est une image matricielle : aucune source SVG vectorielle ni variante symbolique monochrome n’est fournie. Ces adaptations restent possibles ultérieurement ; elles ne sont pas nécessaires au lanceur actuel.

## Intégration

Le wheel et l’archive source incluent les PNG. GTK ajoute les ressources du paquet à ses chemins de recherche en mémoire et utilise cet identifiant comme icône des fenêtres. Les API employées sont décrites dans la documentation GTK : [chemin de recherche](https://docs.gtk.org/gtk4/method.IconTheme.add_search_path.html) et [icône par défaut](https://docs.gtk.org/gtk4/type_func.Window.set_default_icon_name.html).

La recette Arch prévoit les PNG sous `/usr/share/icons/hicolor/` et le lanceur sous `/usr/share/applications/io.github.sambapilot.SambaPilot.desktop`. Le fichier modèle reste [sambapilot.desktop](../../packaging/arch/sambapilot.desktop). Son nom installé correspond à l’identifiant GTK pour l’association avec la fenêtre dans le bureau.

Ces chemins sont des destinations de conditionnement. Cette modification du dépôt n’installe rien sur l’ordinateur. Le lancement depuis les sources peut charger l’icône dans GTK, mais l’icône du lanceur et son association sous Linux doivent être vérifiées avec le paquet installé dans un environnement autorisé.

La CI des trois distributions prépare un contrôle du wheel installé : présence et dimensions des huit PNG, décodage par GDK et résolution du nom d’icône par GTK. Ce contrôle reste à exécuter ; il ne remplace pas la vérification du lanceur dans une session de bureau réelle. Voir le [guide CI](../validation/verification-automatisee.md).

## Reproduction de la direction visuelle

Consigne utilisée avec l’outil intégré, résumée en français : créer une seule icône originale pour SambaPilot, utilitaire GTK de diagnostic des partages Samba sur Linux ; dossier bleu cobalt, réseau à trois nœuds blanc chaud et turquoise, style GNOME avec relief discret, silhouette lisible en petit, fond transparent, sans texte ni filigrane.
