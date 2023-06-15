"""
SPDX-FileCopyrightText: 2023 Steffen Vogel, OPAL-RT Germany GmbH
SPDX-License-Identifier: Apache-2.0
"""

import os
import threading

from seguro.common.store import Client, Event, EventType


def test_store():
    store = Client("pytest-client")

    # Create new file and fill with content
    if not os.path.isfile("myfile.txt"):
        f = open("myfile.txt", "w")

    f = open("myfile.txt", "w")
    f.write("Hello S3Storage!")
    f.close()

    # Put file into storage
    store.put_file("myStorageFile.txt", "myfile.txt")

    # Write new content to file
    store.put_file_contents("myStorageFile.txt", "!egarotS3S olleH")

    store.get_file("myLocalStorageFile.txt", "myStorageFile.txt")

    f = open("myLocalStorageFile.txt", "r")
    content = f.read()

    assert content == "!egarotS3S olleH"
    print(content)


def test_watch():
    store = Client()

    filename = "some/prefix/test"

    store.remove_file(filename)

    def create_obj():
        store.put_file_contents(filename, "this is a test2")
        store.remove_file(filename)

    t = threading.Timer(0.1, create_obj)
    t.start()

    events = store.watch("some/prefix/")

    event = next(events)
    assert event.type == EventType.CREATED
    assert event.filename == filename

    event = next(events)
    assert event.type == EventType.REMOVED
    assert event.filename == filename


def test_watch_async():
    store = Client()

    i = 0

    def callback(event: Event):
        nonlocal i

        if i == 0:
            assert event.type == EventType.CREATED
            assert event.filename == filename
        elif i == 1:
            assert event.type == EventType.REMOVED
            assert event.filename == filename

            # Raise a StopIteration exception to stop processing events
            raise StopIteration()

        i += 1

    filename = "some/prefix/test"

    store.remove_file(filename)
    watcher = store.watch_async("some/prefix/", callback)

    store.put_file_contents(filename, "this is a test2")
    store.remove_file(filename)

    watcher.join()
