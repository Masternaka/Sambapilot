"""Fenêtre native GTK 4 : démonstration et lecture d'un fichier choisi."""

from gi.repository import Gio, GLib, Gtk
from threading import Thread

from .presentation import AccessFilters, DemoViewModel, decision_details, decision_status, right_text
from .demo import demo_configuration, demo_shares
from .planning import PlanError, PlanSession, ShareDraft, format_plan, parse_identities
from .inspection import InspectionError, format_inspection, inspect_content, read_configuration
from .file_planning import FilePlanSession
from .validation import format_validation, validate_plan
from .gtk_setup import InstallationPage
from .gtk_firewall import FirewallPage


def label(text, style=None, selectable=False):
    widget = Gtk.Label(label=text, xalign=0, wrap=True, selectable=selectable)
    if style:
        widget.add_css_class(style)
    return widget


def box(spacing=12, margin=0, horizontal=False):
    widget = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL if horizontal else Gtk.Orientation.VERTICAL,
                     spacing=spacing)
    for side in ("top", "bottom", "start", "end"):
        getattr(widget, "set_margin_" + side)(margin)
    return widget


def card(title, description):
    frame = Gtk.Frame()
    content = box(margin=16)
    content.append(label(title, "heading"))
    content.append(label(description, selectable=True))
    frame.set_child(content)
    return frame


def page(title, description):
    content = box(spacing=16, margin=24)
    content.append(label(title, "title-1"))
    content.append(label(description, "dim-label"))
    return content


def scroll(child):
    widget = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
    widget.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    widget.set_child(child)
    return widget


class SambaPilotWindow(Gtk.ApplicationWindow):
    def __init__(self, application, model):
        super().__init__(application=application, title="SambaPilot — Démonstration")
        self.model = model
        self.visible_decisions = ()
        self.updating_rows = False
        self.plan_session = PlanSession(demo_configuration(), mode="demo")
        self.share_action = "create"
        self.filling_form = False
        self.validation_generation = 0
        self.plan_validation = None
        self.inspection_generation = 0
        self.inspection_report = None
        self.inspection_snapshot = None
        self.config_share_names = ()
        self.connect("close-request", self.invalidate_inspection_on_close)
        self.set_default_size(1160, 820)
        self.set_size_request(800, 600)

        header = Gtk.HeaderBar()
        header.set_title_widget(label("SambaPilot", "heading"))
        self.mode_label = label("Démonstration", "dim-label")
        header.pack_end(self.mode_label)
        self.set_titlebar(header)

        self.stack = Gtk.Stack(hexpand=True, vexpand=True)
        sidebar = Gtk.StackSidebar()
        sidebar.set_stack(self.stack)
        sidebar.set_size_request(180, -1)

        self.stack.add_titled(scroll(self.dashboard_page()), "dashboard", "Tableau de bord")
        self.installation_page = InstallationPage(self.update_mode_banner)
        self.stack.add_titled(scroll(self.installation_page), "installation", "Installation")
        self.stack.add_titled(scroll(self.shares_page()), "shares", "Partages")
        self.stack.add_titled(scroll(self.access_page()), "access", "Utilisateurs et accès")
        self.stack.add_titled(scroll(self.share_plan_page()), "prepare", "Préparer un partage")
        self.stack.add_titled(scroll(self.configuration_page()), "configuration", "Examiner une configuration")
        self.stack.add_titled(scroll(self.firewall_page()), "firewall", "Pare-feu")
        self.stack.add_titled(scroll(self.maintenance_page()), "maintenance", "Maintenance")

        main = box(spacing=0, horizontal=True)
        main.append(sidebar)
        main.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        main.append(self.stack)
        main.set_vexpand(True)
        root = box(spacing=0)
        banner = box(spacing=4, margin=12)
        self.banner_title = label("", "heading")
        self.banner_description = label("", "dim-label")
        banner.append(self.banner_title)
        banner.append(self.banner_description)
        root.append(banner)
        root.append(Gtk.Separator())
        root.append(main)
        self.set_child(root)
        self.stack.connect("notify::visible-child-name", self.update_mode_banner)
        self.update_mode_banner()
        self.update_accesses()

    def update_mode_banner(self, *_args):
        if self.stack.get_visible_child_name() == "installation" and self.installation_page.source == "live":
            self.set_title("SambaPilot — Préparation de l’installation")
            self.mode_label.set_text("Lecture seule")
            self.banner_title.set_text("CONSTAT LOCAL · Aucune installation")
            self.banner_description.set_text("Seules des informations locales sont consultées ; aucune intervention n’est exécutée.")
        elif self.stack.get_visible_child_name() == "prepare" and self.plan_session.mode == "file":
            self.set_title("SambaPilot — Aperçu de fichier")
            self.mode_label.set_text("Aperçu fichier")
            self.banner_title.set_text("FICHIER CHOISI · Aucun enregistrement")
            self.banner_description.set_text("Le fichier est relu pour vérifier son état. Le résultat proposé reste en mémoire.")
        elif self.stack.get_visible_child_name() == "configuration":
            self.set_title("SambaPilot — Lecture seule")
            self.mode_label.set_text("Lecture seule")
            self.banner_title.set_text("EXAMEN DE FICHIER · Lecture seule")
            self.banner_description.set_text("Seul un fichier choisi explicitement est lu. Les autres pages restent en démonstration.")
        elif self.stack.get_visible_child_name() == "firewall":
            self.set_title("SambaPilot — Périmètre réseau déclaré")
            self.mode_label.set_text("Aperçu réseau")
            self.banner_title.set_text("PÉRIMÈTRE DÉCLARÉ · Aucun port ouvert")
            self.banner_description.set_text("Intentions de règles uniquement ; aucune lecture ou modification du pare-feu système.")
        else:
            self.set_title("SambaPilot — Démonstration")
            self.mode_label.set_text("Démonstration")
            self.banner_title.set_text("MODE DÉMONSTRATION · Données fictives")
            self.banner_description.set_text("Ces pages utilisent des exemples. L’examen d’un fichier choisi est disponible dans sa rubrique dédiée.")

    def configuration_page(self):
        content = page("Examiner une configuration",
                       "Choisissez un fichier Samba pour lire ses déclarations locales. "
                       "Le fichier ne sera pas modifié et aucun fichier inclus ne sera ouvert.")
        actions = box(horizontal=True)
        choose = Gtk.Button(label="Choisir un fichier…")
        choose.add_css_class("suggested-action")
        choose.connect("clicked", self.choose_configuration)
        example = Gtk.Button(label="Examiner l’exemple fictif")
        example.connect("clicked", self.inspect_configuration_example)
        clear = Gtk.Button(label="Effacer le rapport")
        clear.connect("clicked", self.clear_inspection)
        actions.append(choose)
        actions.append(example)
        actions.append(clear)
        content.append(actions)
        self.inspection_status = label("Aucun fichier sélectionné. Aucune lecture automatique au démarrage.")
        content.append(self.inspection_status)
        self.config_share = Gtk.DropDown.new_from_strings(["Aucun partage chargé"])
        self.config_share.set_tooltip_text("Partage du fichier choisi pour préparer une modification ou un retrait")
        content.append(self.config_share)
        plan_actions = box(horizontal=True)
        self.config_create = Gtk.Button(label="Préparer un ajout")
        self.config_update = Gtk.Button(label="Préparer une modification")
        self.config_remove = Gtk.Button(label="Préparer le retrait")
        for action, button in (("create", self.config_create), ("update", self.config_update), ("remove", self.config_remove)):
            button.set_sensitive(False)
            button.connect("clicked", lambda _button, mode=action: self.open_file_share_plan(mode))
            plan_actions.append(button)
        content.append(plan_actions)
        self.inspection_output = Gtk.TextView(editable=False, cursor_visible=False, monospace=True,
                                              wrap_mode=Gtk.WrapMode.WORD_CHAR)
        output_scroll = scroll(self.inspection_output)
        output_scroll.set_min_content_height(350)
        content.append(output_scroll)
        content.append(label("Ce rapport ne remplace pas testparm et ne calcule pas les droits effectifs. "
                             "Les aperçus du fichier choisi n’enregistrent aucun changement.", "dim-label"))
        return content

    def clear_inspection(self, *_args):
        self.inspection_generation += 1
        self.inspection_report = None
        self.inspection_snapshot = None
        self.reset_config_plan_controls()
        if self.plan_session.mode == "file":
            self.populate_share_plan("create", "", None, PlanSession(demo_configuration(), "demo"))
        self.inspection_output.get_buffer().set_text("")
        self.inspection_status.set_text("Aucun rapport conservé en mémoire. Aucun fichier modifié.")

    def choose_configuration(self, _button):
        self.clear_inspection()
        generation = self.inspection_generation
        dialog = Gtk.FileDialog(title="Choisir une configuration Samba à examiner", modal=True)
        dialog.open(self, None, lambda chooser, result: self.configuration_selected(chooser, result, generation))

    def configuration_selected(self, dialog, result, generation):
        try:
            selected = dialog.open_finish(result)
        except GLib.Error:
            if generation == self.inspection_generation:
                self.inspection_status.set_text("Sélection annulée ou indisponible. Aucun fichier chargé.")
            return
        if generation != self.inspection_generation:
            return
        filename = selected.get_path() if selected else None
        if not filename:
            self.inspection_status.set_text("Choisir un fichier local régulier. Aucun fichier chargé.")
            return
        self.inspection_status.set_text("Lecture du fichier choisi…")
        Thread(target=self.read_chosen_configuration, args=(filename, generation), daemon=True).start()

    def read_chosen_configuration(self, filename, generation):
        try:
            snapshot = read_configuration(filename)
            report, error = snapshot.inspect(), None
        except InspectionError as failure:
            report, error, snapshot = None, str(failure), None
        GLib.idle_add(self.receive_inspection, generation, report, error, snapshot)

    def receive_inspection(self, generation, report, error=None, snapshot=None):
        if generation != self.inspection_generation:
            return False
        if error:
            self.inspection_report = None
            self.inspection_snapshot = None
            self.reset_config_plan_controls()
            self.inspection_output.get_buffer().set_text("")
            self.inspection_status.set_text("Lecture refusée : " + error)
        else:
            self.inspection_report = report
            self.inspection_snapshot = snapshot
            self.reset_config_plan_controls()
            if snapshot is not None and report.status == "inspected":
                self.config_share_names = tuple(share.name for share in report.shares)
                self.config_share.set_model(Gtk.StringList.new(list(self.config_share_names) or ["Aucun partage local"]))
                self.config_share.set_selected(0)
                self.config_create.set_sensitive(True)
                self.config_update.set_sensitive(bool(self.config_share_names))
                self.config_remove.set_sensitive(bool(self.config_share_names))
            self.inspection_output.get_buffer().set_text(format_inspection(report))
            origin = "Exemple fictif" if report.mode == "demo" else "Fichier choisi"
            self.inspection_status.set_text(origin + " · " + ("analyse bloquée, voir les explications."
                                            if report.status == "blocked" else "déclarations locales lues ; aucun droit effectif certifié."))
        return False

    def reset_config_plan_controls(self):
        self.config_share_names = ()
        self.config_share.set_model(Gtk.StringList.new(["Aucun partage chargé"]))
        for button in (self.config_create, self.config_update, self.config_remove):
            button.set_sensitive(False)

    def open_file_share_plan(self, action):
        self.invalidate_plan()
        try:
            if self.inspection_snapshot is None:
                raise PlanError("Choisissez d’abord un fichier de configuration.")
            session = FilePlanSession(self.inspection_snapshot)
            index = self.config_share.get_selected()
            if action != "create" and not 0 <= index < len(self.config_share_names):
                raise PlanError("Sélectionnez un partage déclaré dans le fichier choisi.")
            name = "" if action == "create" else self.config_share_names[index]
            draft = session.draft_for(name) if action == "update" else None
        except (PlanError, IndexError) as error:
            self.inspection_status.set_text("Préparation refusée : " + str(error))
            return
        self.populate_share_plan(action, name, draft, session)
        self.stack.set_visible_child_name("prepare")

    def inspect_configuration_example(self, _button):
        self.clear_inspection()
        self.receive_inspection(self.inspection_generation,
                                inspect_content(demo_configuration(), "Exemple fictif en mémoire", "demo"))

    def invalidate_inspection_on_close(self, *_args):
        self.inspection_generation += 1
        self.validation_generation += 1
        self.installation_page.close()
        return False

    def dashboard_page(self):
        content = page("Vos partages, en un coup d’œil",
                       "Exemple d’un environnement domestique. Tous les indicateurs ci-dessous sont fictifs.")
        counters = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE,
                               column_spacing=12, row_spacing=12,
                               min_children_per_line=2, max_children_per_line=4)
        for value, title in ((len(self.model.shares), "Partages exemples"),
                             (len(self.model.users), "Comptes exemples"),
                             (self.model.conflict_count, "Accès en conflit"),
                             (self.model.unknown_count, "Accès à vérifier")):
            counters.insert(card(str(value), title), -1)
        content.append(counters)
        diagnostic = self.model.diagnostic
        smb = next((service for service in diagnostic.services if service.name == "smb.service"), None)
        content.append(card("Service Samba · exemple", "Activité : " + (smb.active_state if smb else "inconnue")
                            + ". L’état de votre ordinateur n’est pas consulté."))
        content.append(card("Un conflit à comprendre",
                            "Dans l’exemple, alex peut lire le partage Famille, mais les permissions Linux "
                            "refusent l’écriture autorisée par les règles Samba."))
        actions = box(horizontal=True)
        view = Gtk.Button(label="Voir les accès")
        view.add_css_class("suggested-action")
        view.connect("clicked", lambda _button: self.stack.set_visible_child_name("access"))
        conflicts = Gtk.Button(label="Examiner les conflits")
        conflicts.connect("clicked", self.show_conflicts)
        actions.append(view)
        actions.append(conflicts)
        installation = Gtk.Button(label="Préparer l’installation")
        installation.connect("clicked", lambda _button: self.stack.set_visible_child_name("installation"))
        actions.append(installation)
        content.append(actions)
        content.append(card("À venir", "Installation guidée, modification des partages, comptes, "
                            "permissions et règles de pare-feu avec aperçu et confirmation."))
        return content

    def shares_page(self):
        content = page("Partages", "Dossiers de démonstration. Leur existence sur cet ordinateur n’est pas vérifiée.")
        create = Gtk.Button(label="Préparer un nouveau partage", halign=Gtk.Align.START)
        create.add_css_class("suggested-action")
        create.connect("clicked", lambda _button: self.open_share_plan("create"))
        content.append(create)
        for share in self.model.shares:
            rows = tuple(row for row in self.model.accesses.decisions if row.share == share)
            frame = Gtk.Frame()
            item = box(margin=16)
            item.append(label(share, "heading"))
            item.append(label(rows[0].path, selectable=True))
            item.append(label(str(len(rows)) + " comptes dans la matrice d’exemple", "dim-label"))
            button = Gtk.Button(label="Voir les accès de ce partage", halign=Gtk.Align.START)
            button.connect("clicked", lambda _button, name=share: self.show_share(name))
            item.append(button)
            actions = box(horizontal=True)
            edit = Gtk.Button(label="Préparer une modification")
            edit.connect("clicked", lambda _button, name=share: self.open_share_plan("update", name))
            remove = Gtk.Button(label="Préparer le retrait")
            remove.connect("clicked", lambda _button, name=share: self.open_share_plan("remove", name))
            actions.append(edit)
            actions.append(remove)
            item.append(actions)
            frame.set_child(item)
            content.append(frame)
        return content

    def share_plan_page(self):
        content = page("Préparer un partage",
                       "Vérifiez les réglages proposés et leur comparaison avec la source. "
                       "Aucun aperçu n’est enregistré ou appliqué.")
        self.plan_origin = label("Source : configuration fictive", "dim-label", selectable=True)
        content.append(self.plan_origin)
        self.plan_heading = label("Créer un partage", "heading")
        content.append(self.plan_heading)
        self.plan_name = Gtk.Entry()
        self.plan_path = Gtk.Entry(placeholder_text="/srv/partages/documents")
        self.plan_users = Gtk.Entry(placeholder_text="alex, lea")
        self.plan_groups = Gtk.Entry(placeholder_text="famille")
        for title, entry in (("Nom du partage", self.plan_name), ("Chemin Linux du dossier", self.plan_path),
                             ("Utilisateurs autorisés, séparés par des virgules", self.plan_users),
                             ("Groupes autorisés, séparés par des virgules (sans @)", self.plan_groups)):
            field_label = label(title)
            field_label.set_mnemonic_widget(entry)
            content.append(field_label)
            content.append(entry)
            entry.connect("changed", self.invalidate_plan)
        self.plan_writable = Gtk.CheckButton(label="Autoriser la lecture et l’écriture")
        self.plan_browseable = Gtk.CheckButton(label="Afficher le partage dans la liste")
        self.plan_browseable.set_active(True)
        self.plan_writable.connect("toggled", self.invalidate_plan)
        self.plan_browseable.connect("toggled", self.invalidate_plan)
        content.append(self.plan_writable)
        content.append(self.plan_browseable)
        content.append(label("L’accès invité reste désactivé. Au moins un utilisateur ou un groupe est requis. "
                             "Masquer un partage ne bloque pas les accès directs.", "dim-label"))
        actions = box(horizontal=True)
        preview = Gtk.Button(label="Générer l’aperçu")
        preview.add_css_class("suggested-action")
        preview.connect("clicked", self.preview_share_plan)
        self.validation_button = Gtk.Button(label="Contrôler avec Samba")
        self.validation_button.set_sensitive(False)
        self.validation_button.connect("clicked", self.validate_current_plan)
        cancel = Gtk.Button(label="Annuler la préparation")
        cancel.connect("clicked", self.cancel_share_plan)
        actions.append(preview)
        actions.append(self.validation_button)
        actions.append(cancel)
        content.append(actions)
        self.plan_status = label("Renseignez le formulaire pour préparer un aperçu.")
        self.plan_status.set_selectable(True)
        content.append(self.plan_status)
        self.validation_status = label("Contrôle Samba non demandé.", selectable=True)
        content.append(self.validation_status)
        self.plan_output = Gtk.TextView(editable=False, cursor_visible=False, monospace=True,
                                        wrap_mode=Gtk.WrapMode.NONE)
        preview_scroll = scroll(self.plan_output)
        preview_scroll.set_min_content_height(260)
        content.append(preview_scroll)
        return content

    def invalidate_plan(self, *_args):
        if self.filling_form:
            return
        self.validation_generation += 1
        self.plan_validation = None
        self.plan_session.discard()
        if hasattr(self, "validation_status"):
            self.validation_status.set_text("Contrôle Samba non demandé ou devenu caduc.")
            self.validation_button.set_sensitive(False)
        if hasattr(self, "plan_output"):
            self.plan_output.get_buffer().set_text("")
            self.plan_status.set_text("Aperçu à générer : le formulaire n’a pas été validé.")

    def open_share_plan(self, action, name=None):
        share = next((item for item in demo_shares() if item.name == name), None)
        draft = ShareDraft(share.name, share.path, share.allowed_users, share.allowed_groups,
                           share.read_only) if share else None
        self.populate_share_plan(action, share.name if share else "", draft,
                                 PlanSession(demo_configuration(), "demo"))
        self.stack.set_visible_child_name("prepare")

    def populate_share_plan(self, action, name, draft, session):
        self.plan_session.discard()
        self.filling_form = True
        self.plan_session = session
        self.share_action = action
        self.plan_origin.set_text("Source : " + (session.snapshot.source if session.mode == "file" else "configuration fictive"))
        self.plan_name.set_text(draft.name if draft else name)
        self.plan_name.set_editable(action == "create")
        self.plan_path.set_text(draft.path if draft else "")
        self.plan_users.set_text(", ".join(draft.users) if draft else "")
        self.plan_groups.set_text(", ".join(draft.groups) if draft else "")
        self.plan_writable.set_active(not draft.read_only if draft else False)
        self.plan_browseable.set_active(draft.browseable if draft else True)
        for widget in (self.plan_path, self.plan_users, self.plan_groups,
                       self.plan_writable, self.plan_browseable):
            widget.set_sensitive(action != "remove")
        titles = {"create": "Créer un partage", "update": "Modifier un partage", "remove": "Retirer une déclaration de partage"}
        self.plan_heading.set_text(titles[action])
        self.filling_form = False
        self.invalidate_plan()
        if action == "remove":
            self.plan_status.set_text("Seule la déclaration sera retirée dans l’aperçu. "
                                      "Le dossier et ses fichiers seront conservés.")
        self.update_mode_banner()

    def preview_share_plan(self, _button):
        self.invalidate_plan()
        try:
            name = self.plan_name.get_text()
            draft = None if self.share_action == "remove" else ShareDraft(
                name, self.plan_path.get_text(), parse_identities(self.plan_users.get_text()),
                parse_identities(self.plan_groups.get_text()), not self.plan_writable.get_active(),
                self.plan_browseable.get_active(),
            )
            plan = self.plan_session.preview(self.share_action, name, draft)
        except (PlanError, InspectionError) as error:
            self.plan_status.set_text("Aperçu refusé : " + str(error))
            return
        self.plan_output.get_buffer().set_text(format_plan(plan))
        self.plan_status.set_text("Aperçu généré en mémoire. Aucune modification appliquée.")
        self.validation_button.set_sensitive(True)

    def validate_current_plan(self, _button):
        plan = self.plan_session.current
        if plan is None:
            return
        self.validation_generation += 1
        generation = self.validation_generation
        self.plan_validation = None
        self.validation_status.set_text("Contrôle demandé sur une copie temporaire privée du candidat…")
        self.validation_button.set_sensitive(False)
        Thread(target=self.run_plan_validation, args=(generation, plan), daemon=True).start()

    def run_plan_validation(self, generation, plan):
        validation = validate_plan(plan)
        GLib.idle_add(self.receive_validation, generation, plan, validation)

    def receive_validation(self, generation, plan, validation):
        if generation != self.validation_generation or self.plan_session.current is not plan:
            return False
        if validation.status == "stale":
            self.invalidate_plan()
            self.plan_status.set_text("Source modifiée ou inaccessible : rechargez-la pour préparer un nouvel aperçu.")
        else:
            self.validation_button.set_sensitive(True)
        self.plan_validation = validation
        self.validation_status.set_text(format_validation(validation))
        return False

    def cancel_share_plan(self, _button):
        target = "configuration" if self.plan_session.mode == "file" else "shares"
        self.open_share_plan("create")
        self.stack.set_visible_child_name(target)

    def access_page(self):
        content = page("Qui peut accéder à quoi ?",
                       "Lecture et écriture estimées à partir des données fictives. "
                       "Sélectionnez une ligne pour comprendre le résultat.")
        filters = box(horizontal=True)
        user_box = box(spacing=4)
        share_box = box(spacing=4)
        user_box.append(label("Utilisateur"))
        share_box.append(label("Partage"))
        self.user_filter = Gtk.DropDown.new_from_strings(["Tous les comptes", *self.model.users])
        self.share_filter = Gtk.DropDown.new_from_strings(["Tous les partages", *self.model.shares])
        self.user_filter.set_tooltip_text("Filtrer les accès par utilisateur")
        self.share_filter.set_tooltip_text("Filtrer les accès par partage")
        user_box.append(self.user_filter)
        share_box.append(self.share_filter)
        filters.append(user_box)
        filters.append(share_box)
        content.append(filters)
        search_row = box(horizontal=True)
        self.search = Gtk.SearchEntry(hexpand=True)
        self.search.set_placeholder_text("Rechercher un compte, un partage ou un chemin")
        self.search.set_tooltip_text("Recherche dans les comptes, partages et chemins fictifs")
        self.conflict_filter = Gtk.CheckButton(label="Conflits seulement")
        reset = Gtk.Button(label="Réinitialiser")
        reset.connect("clicked", lambda _button: self.reset_filters())
        search_row.append(self.search)
        search_row.append(self.conflict_filter)
        search_row.append(reset)
        content.append(search_row)
        self.result_count = label("")
        content.append(self.result_count)
        titles = Gtk.Grid(column_homogeneous=True, column_spacing=12)
        for column, text in enumerate(("Utilisateur", "Partage", "Lecture estimée", "Écriture estimée", "État")):
            titles.attach(label(text, "heading"), column, 0, 1, 1)
        content.append(titles)
        self.access_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.access_list.add_css_class("boxed-list")
        self.access_list.set_placeholder(label("Aucun accès ne correspond aux filtres. Réinitialisez-les pour tout afficher."))
        self.access_list.connect("row-selected", self.select_access)
        content.append(self.access_list)
        self.details = Gtk.Frame()
        content.append(self.details)
        content.append(label("Ces estimations ne vérifient ni l’authentification, ni le réseau, "
                             "ni les droits de chaque fichier enfant.", "dim-label"))
        self.user_filter.connect("notify::selected", self.update_accesses)
        self.share_filter.connect("notify::selected", self.update_accesses)
        self.search.connect("search-changed", self.update_accesses)
        self.conflict_filter.connect("toggled", self.update_accesses)
        return content

    def update_accesses(self, *_args):
        user_index = self.user_filter.get_selected()
        share_index = self.share_filter.get_selected()
        filters = AccessFilters(
            user=self.model.users[user_index - 1] if 0 < user_index <= len(self.model.users) else None,
            share=self.model.shares[share_index - 1] if 0 < share_index <= len(self.model.shares) else None,
            query=self.search.get_text(), conflicts_only=self.conflict_filter.get_active(),
        )
        self.visible_decisions = self.model.filtered(filters)
        self.updating_rows = True
        while (child := self.access_list.get_row_at_index(0)) is not None:
            self.access_list.remove(child)
        for item in self.visible_decisions:
            row = Gtk.ListBoxRow()
            cells = Gtk.Grid(column_homogeneous=True, column_spacing=12)
            cells.set_margin_top(10)
            cells.set_margin_bottom(10)
            for column, text in enumerate((item.user, item.share, right_text(item.read),
                                           right_text(item.write), decision_status(item))):
                cells.attach(label(text), column, 0, 1, 1)
            row.set_child(cells)
            self.access_list.append(row)
        self.updating_rows = False
        self.result_count.set_text(str(len(self.visible_decisions)) + " accès affichés sur "
                                   + str(len(self.model.accesses.decisions)))
        self.details.set_child(card("Détail de l’accès", "Aucune ligne sélectionnée."))
        if self.visible_decisions:
            self.access_list.select_row(self.access_list.get_row_at_index(0))

    def select_access(self, _listbox, row):
        if self.updating_rows:
            return
        if row is None:
            self.details.set_child(card("Détail de l’accès", "Aucune ligne sélectionnée."))
            return
        item = self.visible_decisions[row.get_index()]
        self.details.set_child(card(item.user + " · " + item.share, decision_details(item)))

    def reset_filters(self):
        self.user_filter.set_selected(0)
        self.share_filter.set_selected(0)
        self.search.set_text("")
        self.conflict_filter.set_active(False)
        self.update_accesses()

    def show_conflicts(self, _button):
        self.reset_filters()
        self.conflict_filter.set_active(True)
        self.stack.set_visible_child_name("access")

    def show_share(self, name):
        self.reset_filters()
        self.share_filter.set_selected(self.model.shares.index(name) + 1)
        self.stack.set_visible_child_name("access")

    def firewall_page(self):
        self.firewall_editor = FirewallPage()
        return self.firewall_editor

    def maintenance_page(self):
        content = page("Maintenance", "Diagnostic d’exemple et périmètre de cette première interface.")
        for service in self.model.diagnostic.services:
            content.append(card(service.name + " · exemple",
                                "Chargement : " + service.load_state + " · Activité : " + service.active_state
                                + " · Activation au démarrage : " + service.unit_file_state))
        content.append(card("Sauvegarde et restauration · à venir",
                            "Aucune sauvegarde de votre ordinateur n’a été créée par cette démonstration. "
                            "Les futures interventions présenteront les changements avant confirmation."))
        for note in self.model.diagnostic.notes:
            content.append(label(note, "dim-label"))
        return content


class SambaPilotApplication(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.github.sambapilot.SambaPilot",
                         flags=Gio.ApplicationFlags.NON_UNIQUE)
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_args: self.quit())
        self.add_action(quit_action)
        self.set_accels_for_action("app.quit", ["<Primary>q"])

    def do_activate(self):
        window = self.get_active_window()
        if window is None:
            window = SambaPilotWindow(self, DemoViewModel.create())
        window.present()
