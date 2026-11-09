PYTHON ?= python3

.PHONY: test check demo demo-backup test-gtk test-samba test-native check-dist

test:
	$(PYTHON) -B scripts/run_tests.py

check:
	$(PYTHON) -B scripts/check.py

demo:
	$(PYTHON) -B -m sambapilot diagnostic --demo

# Dépendances déjà installées ; ces cibles n’installent rien.
test-gtk:
	SAMBAPILOT_GTK_TESTS=1 $(PYTHON) -B -m unittest discover -s tests -p 'test_gtk_integration.py' -v

test-samba:
	SAMBAPILOT_SAMBA_TESTS=1 $(PYTHON) -B -m unittest discover -s tests -p 'test_samba_integration.py' -v

check-dist:
	$(PYTHON) -B scripts/check_distribution.py dist

# Laboratoire jetable : aucun chemin de configuration réelle en entrée.
demo-backup:
	$(PYTHON) -B -m sambapilot.backup_simulation --demo

# Échec si GTK/Samba sont absents ou si un test natif est ignoré.
test-native:
	$(PYTHON) -B scripts/run_tests.py --require-native
