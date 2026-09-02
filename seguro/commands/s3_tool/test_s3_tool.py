# SPDX-FileCopyrightText: 2026 Henrik Hörter
# SPDX-License-Identifier: Apache-2.0

import pytest
import argparse
import shutil

from pathlib import Path
from main import pull, push, remove
from seguro.common.store import Client

BASE_DIR = "tmp_test"
REMOTE_DIR = "__tmp_test"
FILES = {
    BASE_DIR + "/test": "hello s3 store\n",
    BASE_DIR + "/test1": "hello test1\n",
    BASE_DIR + "/testdir/a.txt": "A\n",
    BASE_DIR + "/testdir/b.txt": "B\n",
    BASE_DIR + "/testdir/nested/test1.txt": "test\n",
    BASE_DIR + "/testdir/nestedprefix/test2.txt": "test2\n",
    BASE_DIR + "/testdir/nestedprefix/dir/foo.txt": "bar\n",
    BASE_DIR + "/testdir/nestedfile": "This is a prefix nested file\n",
    BASE_DIR + "/testdir/test2.txt": "test2\n",
    BASE_DIR + "/testdirprefix/a.txt": "A\n",
}


@pytest.fixture()
def test_tree(base: str = BASE_DIR):
    setup_test_environment()
    yield
    clean_up_test_environment()


def setup_test_environment():
    for string, content in FILES.items():
        path = Path(string)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def clean_up_test_environment():
    s = Client()

    objects = list(
        s.client.list_objects(
            bucket_name=s.bucket,
            prefix=REMOTE_DIR + "/",
            recursive=True,
        )
    )

    for obj in objects:
        s.remove_file(obj.object_name)

    try:
        shutil.rmtree(Path(BASE_DIR))
    except FileNotFoundError:
        pass


@pytest.fixture
def persistent_test_tree():
    setup_test_environment()


@pytest.mark.s3_tool_debug
def test_debug_environment(persistent_test_tree):
    assert Path(BASE_DIR).exists()

    s = Client()

    args = argparse.Namespace(localfile=[BASE_DIR], remotefile=REMOTE_DIR)

    push(s, args)

    objects = list(
        s.client.list_objects(
            bucket_name=s.bucket,
            prefix=REMOTE_DIR,
            recursive=True,
        )
    )

    assert objects


@pytest.mark.s3_tool_debug_cleanup
def test_cleanup_debug_environment():
    clean_up_test_environment()


@pytest.mark.s3_tool
def test_push_single_file(test_tree):
    s = Client()

    args = argparse.Namespace(localfile=[BASE_DIR + "/test"], remotefile=REMOTE_DIR + "/test")

    push(s, args)

    objects = list(
        s.client.list_objects(
            bucket_name=s.bucket,
            prefix=REMOTE_DIR + "/test",
            recursive=True,
        )
    )
    object_names = []
    for object in objects:
        object_names.append(object.object_name)

    assert REMOTE_DIR + "/test" in object_names


@pytest.mark.s3_tool
def test_push_directory(test_tree):
    s = Client()

    args = argparse.Namespace(localfile=[BASE_DIR + "/testdir"], remotefile=REMOTE_DIR + "/testdir")

    push(s, args)

    objects = list(
        s.client.list_objects(
            bucket_name=s.bucket,
            prefix=REMOTE_DIR + "/testdir",
            recursive=True,
        )
    )
    object_names = []
    for object in objects:
        object_names.append(object.object_name)

    for path, _ in FILES.items():
        if path.startswith(BASE_DIR + "/testdir/"):
            file = REMOTE_DIR + str(path).removeprefix(BASE_DIR)
            assert file in object_names
            continue
        elif path.startswith(BASE_DIR + "/testdir"):
            file = REMOTE_DIR + str(path).removeprefix(BASE_DIR)
            assert file not in object_names


@pytest.mark.s3_tool
def test_push_multiple_objects_nested_prefix(test_tree):  # push multiple files/directories with globbing
    s = Client()

    paths = Path(BASE_DIR).glob("testdir/nested*")
    nestedprefix = [str(x) for x in list(paths)]

    args = argparse.Namespace(localfile=nestedprefix, remotefile=REMOTE_DIR + "/testdir")

    push(s, args)

    objects = list(
        s.client.list_objects(
            bucket_name=s.bucket,
            prefix=REMOTE_DIR + "/testdir",
            recursive=True,
        )
    )
    object_names = []
    for object in objects:
        object_names.append(object.object_name)

    for path in nestedprefix:
        for element in Path(path).rglob("*"):
            if element.is_file():
                file = REMOTE_DIR + str(element).removeprefix(BASE_DIR)
                assert file in object_names


@pytest.mark.s3_tool
def test_push_multiple_files(test_tree):  # push multiple localfiles with globbing
    s = Client()

    paths = Path(BASE_DIR).glob("test*")
    nestedprefix = [str(x) for x in list(paths)]

    args = argparse.Namespace(localfile=nestedprefix, remotefile=REMOTE_DIR)

    push(s, args)

    objects = list(
        s.client.list_objects(
            bucket_name=s.bucket,
            prefix=REMOTE_DIR,
            recursive=True,
        )
    )
    object_names = []
    for object in objects:
        object_names.append(object.object_name)

    for path in nestedprefix:
        for element in Path(path).rglob("*"):
            if element.is_file():
                file = REMOTE_DIR + str(element).removeprefix(BASE_DIR)
                assert file in object_names


@pytest.mark.s3_tool
def test_pull_single_object(test_tree):
    s = Client()

    args = argparse.Namespace(localfile=[BASE_DIR + "/test", BASE_DIR + "/test1"], remotefile=REMOTE_DIR)

    push(s, args)

    Path(BASE_DIR + "/test").unlink()
    Path(BASE_DIR + "/test1").unlink()

    assert not Path(BASE_DIR + "/test").is_file()  # local files removed
    assert not Path(BASE_DIR + "/test1").is_file()  # local files removed

    args = argparse.Namespace(localfile=BASE_DIR + "/test", remotefile=REMOTE_DIR + "/test", globbing=False)

    pull(s, args)

    assert Path(BASE_DIR + "/test").is_file()
    assert not Path(BASE_DIR + "/test1").is_file()


@pytest.mark.s3_tool
def test_pull_directory(test_tree):
    s = Client()

    args = argparse.Namespace(localfile=[BASE_DIR], remotefile=REMOTE_DIR)

    push(s, args)

    shutil.rmtree(Path(BASE_DIR))

    assert not Path(BASE_DIR + "/testdir").is_dir()  # local dir removed

    args = argparse.Namespace(localfile=BASE_DIR, remotefile=REMOTE_DIR + "/testdir", globbing=False)

    pull(s, args)

    assert Path(BASE_DIR + "/testdir").is_dir()

    for path, _ in FILES.items():
        if path.startswith(BASE_DIR + "/testdir/"):
            assert Path(path).is_file()
            continue
        elif path.startswith(BASE_DIR + "/testdir"):
            assert not Path(path).is_file()


@pytest.mark.s3_tool
def test_pull_globbing(test_tree):
    s = Client()
    args = argparse.Namespace(localfile=[BASE_DIR], remotefile=REMOTE_DIR)

    push(s, args)

    shutil.rmtree(Path(BASE_DIR))

    assert not Path(BASE_DIR + "/testdir").is_dir()
    assert not Path(BASE_DIR + "/testdirprefix").is_dir()

    args = argparse.Namespace(localfile=BASE_DIR, remotefile=REMOTE_DIR + "/testdir", globbing=True)

    pull(s, args)

    assert Path(BASE_DIR + "/testdir").is_dir()
    assert Path(BASE_DIR + "/testdirprefix").is_dir()

    for path, _ in FILES.items():
        if path.startswith(BASE_DIR + "/testdir"):
            assert Path(path).is_file()
            continue
        elif not path.startswith(BASE_DIR + "/testdir"):
            assert not Path(path).is_file()


@pytest.mark.s3_tool
def test_remove_single_file(test_tree):  # check if "__tmp_test/test" will be removed and nothing else
    s = Client()

    args = argparse.Namespace(localfile=[BASE_DIR], remotefile=REMOTE_DIR)

    push(s, args)

    args = argparse.Namespace(file=REMOTE_DIR + "/test", globbing=False)

    remove(s, args)

    objects = list(
        s.client.list_objects(
            bucket_name=s.bucket,
            prefix=REMOTE_DIR + "/test",
            recursive=True,
        )
    )

    object_names = []
    for object in objects:
        object_names.append(object.object_name)

    for path, _ in FILES.items():
        if path != BASE_DIR + "/test":
            file = REMOTE_DIR + str(path).removeprefix(BASE_DIR)
            assert file in object_names
            continue
        else:
            file = REMOTE_DIR + str(path).removeprefix(BASE_DIR)
            assert file not in object_names


@pytest.mark.s3_tool
def test_remove_directory(test_tree):
    s = Client()

    args = argparse.Namespace(localfile=[BASE_DIR], remotefile=REMOTE_DIR)

    assert Path(BASE_DIR + "/test").is_file()

    push(s, args)

    args = argparse.Namespace(file=REMOTE_DIR + "/testdir", globbing=False)

    remove(s, args)

    objects = list(
        s.client.list_objects(
            bucket_name=s.bucket,
            prefix=REMOTE_DIR,
            recursive=True,
        )
    )

    object_names = []
    for object in objects:
        object_names.append(object.object_name)

    for path, _ in FILES.items():
        if not path.startswith(BASE_DIR + "/testdir/"):
            file = REMOTE_DIR + str(path).removeprefix(BASE_DIR)
            assert file in object_names
        elif path.startswith(BASE_DIR + "/testdir/"):
            file = REMOTE_DIR + str(path).removeprefix(BASE_DIR)
            assert file not in object_names


@pytest.mark.s3_tools
def test_remove_globbing(test_tree):
    s = Client()

    args = argparse.Namespace(localfile=[BASE_DIR], remotefile=REMOTE_DIR)

    assert Path(BASE_DIR + "/test").is_file()

    push(s, args)

    args = argparse.Namespace(file=REMOTE_DIR + "/testdir", globbing=True)

    remove(s, args)

    objects = list(
        s.client.list_objects(
            bucket_name=s.bucket,
            prefix=REMOTE_DIR,
            recursive=True,
        )
    )

    object_names = []
    for object in objects:
        object_names.append(object.object_name)

    for path, _ in FILES.items():
        if not path.startswith(BASE_DIR + "/testdir"):
            file = REMOTE_DIR + str(path).removeprefix(BASE_DIR)
            assert file in object_names
        elif path.startswith(BASE_DIR + "/testdir"):
            file = REMOTE_DIR + str(path).removeprefix(BASE_DIR)
            assert file not in object_names
