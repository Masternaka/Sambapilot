"""Lancement optionnel de GTK ; les autres commandes n'importent jamais gi."""

import sys


class GtkUnavailable(RuntimeError):
    pass


def load_gtk():
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk
        if Gtk.check_version(4, 10, 0) is not None:
            raise ValueError("GTK 4.10 ou ultérieur est requis.")
    except (ImportError, ValueError, OSError) as error:
        raise GtkUnavailable(
            "Interface graphique indisponible : GTK 4.10 ou ultérieur et PyGObject doivent déjà être installés "
            "pour l’interpréteur Python utilisé. Aucune installation n’a été effectuée. "
            "Consultez docs/interface-graphique.md ; le terminal et les démonstrations restent utilisables."
        ) from error
    return Gtk


def launch_demo() -> int:
    try:
        Gtk = load_gtk()
    except GtkUnavailable as error:
        print(str(error), file=sys.stderr)
        return 3
    if not Gtk.init_check():
        print("Impossible d’ouvrir une session graphique GTK. Aucune modification système effectuée.",
              file=sys.stderr)
        return 3
    # Import tardif : le terminal reste indépendant de GTK, même si gi est absent.
    from .gtk_app import SambaPilotApplication
    return SambaPilotApplication().run(["sambapilot"])
