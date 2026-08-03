#!/usr/bin/env python
"""Coverage for pyworkflow/utils/path.py - previously untested despite
being pure, heavily-used logic (joinExt in particular is core to how the
mapper builds attribute names)."""
import os

import pytest

import pyworkflow.utils.path as pwpath


@pytest.mark.parametrize(
    "filename, newExt, expected",
    [
        ("image.mrc", "spi", "image.spi"),
        ("/a/b/image.mrc", "spi", "/a/b/image.spi"),
        ("noext", "spi", "noext.spi"),
    ],
)
def test_replaceExt(filename, newExt, expected):
    assert pwpath.replaceExt(filename, newExt) == expected


def test_replaceBaseExt():
    assert pwpath.replaceBaseExt("/a/b/image.mrc", "spi") == "image.spi"


def test_removeBaseExt():
    assert pwpath.removeBaseExt("/a/b/image.mrc") == "image"


def test_removeExt():
    assert pwpath.removeExt("/a/b/image.mrc") == "/a/b/image"


def test_joinExt():
    assert pwpath.joinExt("1", "real") == "1.real"
    assert pwpath.joinExt("a", "b", "c") == "a.b.c"


def test_getExt():
    assert pwpath.getExt("/a/b/image.mrc") == ".mrc"
    assert pwpath.getExt("noext") == ""


def test_getParentFolder(tmp_path):
    child = tmp_path / "sub"
    assert pwpath.getParentFolder(str(child)) == str(tmp_path)


def test_commonPath():
    assert pwpath.commonPath(["/a/b/c.txt", "/a/b/d.txt"]) == "/a/b"


def test_makePath_and_cleanPath(tmp_path):
    target = tmp_path / "one" / "two" / "three"
    pwpath.makePath(str(target))
    assert target.is_dir()

    # makePath should be a no-op if the path already exists
    pwpath.makePath(str(target))
    assert target.is_dir()

    pwpath.cleanPath(str(tmp_path / "one"))
    assert not (tmp_path / "one").exists()


def test_copyFile_and_moveFile(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("hello")
    dest = tmp_path / "dest.txt"

    pwpath.copyFile(str(source), str(dest))
    assert dest.read_text() == "hello"
    assert source.exists()  # copy keeps the source

    moved = tmp_path / "moved.txt"
    pwpath.moveFile(str(dest), str(moved))
    assert moved.read_text() == "hello"
    assert not dest.exists()  # move removes the source


def test_createLink_and_createAbsLink(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("hello")

    relLink = tmp_path / "rel_link.txt"
    pwpath.createLink(str(source), str(relLink))
    assert relLink.is_symlink()
    assert relLink.read_text() == "hello"

    absLink = tmp_path / "abs_link.txt"
    pwpath.createAbsLink(str(source), str(absLink))
    assert absLink.is_symlink()
    assert os.path.isabs(os.readlink(str(absLink)))
    assert absLink.read_text() == "hello"

    # createLink refuses to overwrite a real (non-link) file
    plainFile = tmp_path / "plain.txt"
    plainFile.write_text("already here")
    with pytest.raises(Exception):
        pwpath.createLink(str(source), str(plainFile))


def test_missingPaths(tmp_path):
    existing = tmp_path / "exists.txt"
    existing.write_text("x")
    missing = tmp_path / "missing.txt"

    assert pwpath.missingPaths(str(existing)) == []
    assert pwpath.missingPaths(str(existing), str(missing)) == [str(missing)]


def test_createUniqueFileName(tmp_path):
    fn = tmp_path / "file.txt"
    # Non-existing path is returned unchanged
    assert pwpath.createUniqueFileName(str(fn)) == str(fn)

    fn.write_text("x")
    unique = pwpath.createUniqueFileName(str(fn))
    assert unique != str(fn)
    assert not os.path.exists(unique)


def test_getFiles(tmp_path):
    (tmp_path / "a.txt").write_text("a")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.txt").write_text("b")

    files = pwpath.getFiles(str(tmp_path))
    assert str(tmp_path / "a.txt") in files
    assert str(sub / "b.txt") in files


def test_getFileSize(tmp_path):
    assert pwpath.getFileSize(str(tmp_path / "missing.txt")) == 0

    f = tmp_path / "file.txt"
    f.write_text("hello")
    assert pwpath.getFileSize(str(f)) == 5


def test_backup(tmp_path):
    target = tmp_path / "sub" / "file.txt"
    target.parent.mkdir()
    target.write_text("original")

    pwpath.backup(str(target))

    # backup() renames the original file into a backup/ subfolder
    assert not target.exists()
    backupDir = target.parent / "backup"
    assert backupDir.is_dir()
    backedUpFiles = list(backupDir.iterdir())
    assert len(backedUpFiles) == 1
    assert backedUpFiles[0].read_text() == "original"
