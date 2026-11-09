"""Sauvegarde/restauration dans un espace temporaire privé, sans chemin système en entrée.

Ce laboratoire ne restaure que son propre fichier fictif. Il ne constitue pas un
moteur d'application sur Samba et ne fournit pas de verrouillage interprocessus.
"""

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
from threading import RLock
from typing import Optional, Tuple
from uuid import uuid4

from .inspection import MAX_CONFIG_BYTES


class SimulationError(ValueError):
    pass


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_content(data: bytes) -> None:
    if not isinstance(data, bytes) or len(data) > MAX_CONFIG_BYTES:
        raise SimulationError("La configuration fictive doit être un contenu binaire UTF-8 de 1 Mio maximum.")
    try:
        data.decode("utf-8")
    except UnicodeError as error:
        raise SimulationError("La configuration fictive doit être encodée en UTF-8.") from error


def _identity(info) -> Tuple[int, ...]:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


@dataclass(frozen=True)
class BackupRecord:
    name: str
    created_at: str
    sha256: str
    size: int
    mode: str = "simulation"


@dataclass(frozen=True)
class FileState:
    data: bytes
    sha256: str
    identity: Tuple[int, ...]


@dataclass(frozen=True)
class RestorePreview:
    backup: BackupRecord
    baseline: FileState
    diff: str
    can_apply: bool = False
    mode: str = "simulation"


@dataclass(frozen=True)
class RestoreResult:
    restored_sha256: str
    recovery_backup: BackupRecord
    mode: str = "simulation"


class BackupSandbox:
    """Possède un dossier jetable et ses seules sources ; les sauvegardes disparaissent à la fermeture."""

    def __init__(self, initial_content: bytes):
        _validate_content(initial_content)
        self._temporary = tempfile.TemporaryDirectory(prefix="sambapilot-backup-simulation-")
        self._root = Path(self._temporary.name).resolve()
        self._closed = False
        self._lock = RLock()
        self._records = {}
        self._preview: Optional[RestorePreview] = None
        self._configuration_path = self._root / "smb.conf"
        self._backups = self._root / "backups"
        try:
            self._backups.mkdir(mode=0o700)
            self._write_new(self.configuration_path, initial_content)
        except (OSError, SimulationError):
            self.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()

    def close(self):
        with self._lock:
            self._closed = True
            self._preview = None
            self._temporary.cleanup()

    @property
    def configuration_path(self) -> Path:
        return self._configuration_path

    @property
    def backups(self) -> Tuple[BackupRecord, ...]:
        return tuple(self._records.values())

    def _guard(self, path: Path) -> None:
        if self._closed:
            raise SimulationError("La simulation est fermée.")
        try:
            relative = path.relative_to(self._root)
        except ValueError as error:
            raise SimulationError("Chemin extérieur à la simulation refusé.") from error
        if not relative.parts or ".." in relative.parts:
            raise SimulationError("Chemin de simulation invalide.")
        parent = self._root
        for part in (None, *relative.parts[:-1]):
            if part is not None:
                parent /= part
            if not stat.S_ISDIR(parent.lstat().st_mode):
                raise SimulationError("Un dossier de simulation a été remplacé ou est devenu inaccessible.")

    def _read(self, path: Path) -> FileState:
        self._guard(path)
        initial = path.lstat()
        if not stat.S_ISREG(initial.st_mode) or initial.st_nlink != 1:
            raise SimulationError("Seuls les fichiers réguliers propres à la simulation sont acceptés, sans lien.")
        flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            if _identity(initial) != _identity(before) or before.st_size > MAX_CONFIG_BYTES:
                raise SimulationError("Fichier modifié ou trop volumineux avant la lecture.")
            data = stream.read(MAX_CONFIG_BYTES + 1)
            after = os.fstat(stream.fileno())
        if _identity(before) != _identity(after) or _identity(after) != _identity(path.lstat()):
            raise SimulationError("Le fichier a changé pendant la lecture.")
        _validate_content(data)
        return FileState(data, _digest(data), _identity(after))

    def _write_new(self, path: Path, data: bytes) -> None:
        self._guard(path)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        owned = _identity(os.fstat(descriptor))[:2]
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError:
            if path.exists() and _identity(path.lstat())[:2] == owned:
                path.unlink()
            raise

    def _record_directory(self, record: BackupRecord) -> Path:
        if not isinstance(record, BackupRecord) or self._records.get(record.name) is not record:
            raise SimulationError("Sauvegarde inconnue de cette simulation.")
        directory = self._backups / record.name
        self._guard(directory / "smb.conf")
        return directory

    def backup_path(self, record: BackupRecord) -> Path:
        return self._record_directory(record) / "smb.conf"

    @staticmethod
    def _metadata(record: BackupRecord) -> bytes:
        return (json.dumps(asdict(record), ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode("utf-8")

    def _create_backup(self, state: FileState) -> BackupRecord:
        self._guard(self._backups / "placeholder")
        now = datetime.now(timezone.utc)
        record = BackupRecord(now.strftime("%Y%m%dT%H%M%S%fZ-") + uuid4().hex,
                              now.isoformat(timespec="microseconds"), state.sha256, len(state.data))
        directory = self._backups / record.name
        directory.mkdir(mode=0o700)
        created = []
        try:
            for path, data in ((directory / "smb.conf", state.data),
                               (directory / "metadata.json", self._metadata(record))):
                self._write_new(path, data)
                created.append((path, _identity(path.lstat())[:2]))
        except (OSError, SimulationError):
            for path, owned in reversed(created):
                if _identity(path.lstat())[:2] == owned:
                    path.unlink()
            directory.rmdir()
            raise
        self._records[record.name] = record
        return record

    def _verified_backup(self, record: BackupRecord) -> bytes:
        directory = self._record_directory(record)
        metadata = self._read(directory / "metadata.json").data
        data = self._read(directory / "smb.conf").data
        if metadata != self._metadata(record) or len(data) != record.size or _digest(data) != record.sha256:
            raise SimulationError("Sauvegarde ou métadonnées altérées : restauration refusée.")
        return data

    def create_backup(self) -> BackupRecord:
        with self._lock:
            return self._create_backup(self._read(self.configuration_path))

    def _replace_configuration(self, data: bytes, baseline: FileState) -> None:
        stage = self._root / (".restore-" + uuid4().hex + ".tmp")
        self._write_new(stage, data)
        try:
            latest = self._read(self.configuration_path)
            if latest.sha256 != baseline.sha256 or latest.identity != baseline.identity:
                raise SimulationError("Le fichier fictif a changé : nouvelle comparaison nécessaire.")
            self._guard(self.configuration_path)
            os.replace(stage, self.configuration_path)
        finally:
            if stage.exists():
                stage.unlink()

    def edit_fictional_configuration(self, content: bytes) -> None:
        _validate_content(content)
        with self._lock:
            baseline = self._read(self.configuration_path)
            self._replace_configuration(content, baseline)

    def prepare_restore(self, record: BackupRecord) -> RestorePreview:
        with self._lock:
            self._preview = None
            backup = self._verified_backup(record)
            baseline = self._read(self.configuration_path)
            diff = "".join(difflib.unified_diff(baseline.data.decode("utf-8").splitlines(keepends=True),
                                             backup.decode("utf-8").splitlines(keepends=True),
                                             fromfile="Fichier fictif actuel", tofile="Sauvegarde fictive"))
            self._preview = RestorePreview(record, baseline, diff)
            return self._preview

    def restore(self, preview: RestorePreview, *, confirmed: bool) -> RestoreResult:
        with self._lock:
            if confirmed is not True:
                raise SimulationError("La restauration fictive doit être confirmée explicitement.")
            if preview is None or preview is not self._preview:
                raise SimulationError("Aperçu inconnu ou devenu caduc ; préparer une nouvelle comparaison.")
            self._preview = None  # Une tentative confirmée consomme l'aperçu, même en cas de refus.
            data = self._verified_backup(preview.backup)
            current = self._read(self.configuration_path)
            if current.sha256 != preview.baseline.sha256 or current.identity != preview.baseline.identity:
                raise SimulationError("Le fichier fictif a changé depuis l’aperçu ; restauration refusée.")
            recovery = self._create_backup(current)
            self._replace_configuration(data, current)
            restored = self._read(self.configuration_path)
            if restored.sha256 != preview.backup.sha256:
                raise SimulationError("Le résultat a changé après restauration fictive ; examiner la simulation.")
            return RestoreResult(restored.sha256, recovery)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Tester sauvegarde et restauration dans un dossier temporaire privé.")
    parser.add_argument("--demo", required=True, action="store_true", help="Données fictives uniquement.")
    parser.parse_args(argv)
    from .demo import demo_configuration
    original = demo_configuration().encode("utf-8")
    try:
        with BackupSandbox(original) as sandbox:
            backup = sandbox.create_backup()
            sandbox.edit_fictional_configuration(original + b"\n# Modification fictive\n")
            preview = sandbox.prepare_restore(backup)
            print("SambaPilot — SIMULATION de sauvegarde/restauration")
            print("Données fictives dans un dossier temporaire ; aucune configuration système consultée.")
            print("Sauvegarde UTC : " + backup.created_at + "\nSHA-256 : " + backup.sha256)
            print("\nComparaison avant restauration fictive :\n" + preview.diff)
            result = sandbox.restore(preview, confirmed=True)
            print("Contenu initial restauré : " + str(result.restored_sha256 == backup.sha256))
            print("État remplacé également sauvegardé : " + result.recovery_backup.sha256)
        print("Simulation terminée ; dossier temporaire supprimé.")
    except (OSError, SimulationError) as error:
        print("Simulation interrompue : " + str(error))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
