# SPDX-FileCopyrightText: 2026 Henrik Hörter
# SPDX-License-Identifier: Apache-2.0
import argparse
import pandas as pd
import logging
from pathlib import Path

from seguro.common import store
from seguro.common import config


def checkPath(path: str):
    if Path(path).exists():
        return
    else:
        raise FileNotFoundError(f"Local path not found: {path}")


# push file/directory to S3 store
def push(s: store.Client, args):

    localpath = Path(args.localfile).resolve()
    remotepath = Path(args.remotefile)

    if localpath.is_file():
        print("pushing a file")
        print(f"remote: {args.remotefile} local: {args.localfile}")
        s.put_file(args.remotefile, args.localfile)  # pushing a file

    elif localpath.is_dir():
        for element in localpath.iterdir():
            if element.is_dir():
                args.remotefile = (
                    str(remotepath.joinpath(element.relative_to(localpath)))
                    + "/"
                )
                print(f"remote file: {args.remotefile}")
            else:
                args.remotefile = str(
                    remotepath.joinpath(element.relative_to(localpath))
                )
            args.localfile = str(element)
            print(f"this is before calling push on file: {args.localfile}")
            push(s, args)

    else:
        raise FileNotFoundError(f"Local object not found: {args.localfile}")
    return 0


# pull file/directory from S3 store
def pull(s: store.Client, args):
    # TODO fix directory pull & check file suffix of local file
    objects = list(  # get length of objects here? (objects is iterator)
        s.client.list_objects(  # get all objects in bucket with this prefix
            bucket_name=s.bucket, prefix=args.remotefile, recursive=True
        )
    )

    if len(objects) == 0:
        raise FileNotFoundError(f"Remote object not found: {args.remotefile}")
    elif len(objects) == 1:  # pull single file
        localpath = Path(args.localfile).absolute()
        remotepath = Path(args.remotefile)
        if localpath.is_dir():  # also covers the "." case
            args.localfile = str(localpath.joinpath(remotepath.name))
        print(f"store objectname: {objects[0].object_name}")
        print(f"local path: {args.localfile}")
        s.get_file(args.localfile, objects[0].object_name)

    else:  # pull directory

        localbase = Path(args.localfile).absolute()
        remotebase = Path(args.remotefile)  # base of "directory" in store

        print(f"local path: {args.localfile}")
        print(f"remote base path: {args.remotefile}")

        for object in objects:  # get all objects

            relativepath = Path(object.object_name).relative_to(remotebase)
            new_localpath = localbase.joinpath(remotebase).joinpath(
                relativepath
            )

            localfile = str(new_localpath)
            remotefile = object.object_name

            try:
                s.get_file(localfile, remotefile)
            except Exception as e:
                print(f"Failed to pull {remotefile}: {e}")

    return 0


# remove file/directory from S3 store
def remove(s: store.Client, args):
    objects = list(
        s.client.list_objects(
            bucket_name=s.bucket, prefix=args.file, recursive=True
        )
    )

    if len(objects) == 0:
        raise FileNotFoundError(
            f"Remote object not found: {args.file}, nothing was removed"
        )

    for object in objects:
        s.remove_file(object.object_name)
    return 0


# get file from S3 store
def get_file(s: store.Client, args):
    try:
        s.get_file(args.localfile, args.remotefile)
    except Exception as e:
        print(f"Failed to get {args.remotefile}: {e}")
    return 0


# Get URL of file stored in S3 store
def get_file_url(s: store.Client, args):
    print(s.get_file_url(args.file))
    return 0


def get_file_content(s: store.Client, args):
    response = s.get_file_contents(args.file)
    print(response.data)
    return 0


def put_frame(s: store.Client, args):
    print(type(args.dataframe))
    s.put_frame(args.remotefile, args.dataframe)
    return 0


def get_frame(s: store.Client, args):
    s.get_frame(args.file)
    return 0


def put_file_content(s: store.Client, args):
    content = bytes(args.content)
    s.put_file_contents(args.file, content)


def list_elements(s: store.Client, args):
    if args.path == ".":  # list entire bucket
        objects = s.client.list_objects(
            bucket_name=s.bucket,
            recursive=False,
        )
        for object in objects:
            print(object.object_name)
        return

    if not args.path.endswith("/"):
        args.path += "/"
    remotebase = Path(args.path)

    objects = s.client.list_objects(
        bucket_name=s.bucket,
        prefix=args.path,
        recursive=False,
    )

    for object in objects:  # get all objects
        element_in_dir = str(Path(object.object_name).relative_to(remotebase))
        if object.object_name.endswith("/"):
            element_in_dir += "/"
        print(element_in_dir)


def main():
    parser = argparse.ArgumentParser(
        prog="s3_tool", description="Tool to interact with S3 storage"
    )

    parser.add_argument(
        "-l",
        "--log-level",
        default="debug" if config.DEBUG else "info",
        help="Logging level",
        choices=["debug", "info", "warn", "error", "critical"],
    )

    # Select S3 store bucket
    parser.add_argument(
        "-b",
        "--bucket",
        type=str,
        default=config.S3_BUCKET,
        help="Choose S3 store bucket",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # push parser
    push_parser = subparsers.add_parser(
        "push", help="Push a local file to the storage"
    )
    push_parser.add_argument(
        "-lf", "--localfile", type=str, help="Path to the local file"
    )
    push_parser.add_argument(
        "-rf", "--remotefile", type=str, help="Path in the storage"
    )
    push_parser.set_defaults(func=push)

    # pull parser
    pull_parser = subparsers.add_parser(
        "pull", help="Pull a local file from the storage"
    )
    pull_parser.add_argument(
        "-rf",
        "--remotefile",
        type=str,
        help="Path in the storage",
    )
    pull_parser.add_argument(
        "-lf",
        "--localfile",
        type=str,
        help="Path to the local file",
    )
    pull_parser.set_defaults(func=pull)

    # get file
    get_file_parser = subparsers.add_parser(
        "get-file", help="Get a file from the storage"
    )

    get_file_parser.add_argument(
        "-rf",
        "--remotefile",
        type=str,
        help="Path in the storage",
    )

    get_file_parser.add_argument(
        "-lf", "--localfile", type=str, help="Path to the local file"
    )

    get_file_parser.set_defaults(func=get_file)

    # remove parser
    remove_parser = subparsers.add_parser(
        "remove", help="Remove a file/directory from the storage"
    )
    remove_parser.add_argument(
        "-f", "--file", type=str, help="Path of file in storage"
    )
    remove_parser.set_defaults(func=remove)

    # get file contents
    get_file_content_parser = subparsers.add_parser(
        "get-file-content", help="Get file content into terminal"
    )

    get_file_content_parser.add_argument(
        "-f", "--file", type=str, help="Path of file in storage"
    )

    get_file_content_parser.set_defaults(func=get_file_content)

    # put file contents
    put_file_content_parser = subparsers.add_parser(
        "put-file-content", help="Add filecontent as bytes into file in store"
    )

    put_file_content_parser.add_argument(
        "-f", "--file", type=str, help="Path to file in store"
    )

    put_file_content_parser.add_argument(
        "-c",
        "--content",
        type=str,
        help="Content that is written to file in store",
    )

    put_file_content_parser.set_defaults(func=put_file_content)

    # get file url
    get_file_url_parser = subparsers.add_parser(
        "get-file-url", help="Get File URL"
    )

    get_file_url_parser.add_argument(
        "-f", "--file", type=str, help="Path of file in storage"
    )

    get_file_url_parser.set_defaults(func=get_file_url)

    # put frame parser
    put_frame_parser = subparsers.add_parser(
        "put-frame",
        help="Upload a Pandas Dataframe as a Parquet file to the store",
    )

    put_frame_parser.add_argument(
        "-rf",
        "--remotefile",
        type=str,
        help="Path of file where data frame will be stored",
    )

    put_frame_parser.add_argument(
        "-df",
        "--dataframe",
        type=pd.DataFrame,
        help="Path of file where data frame will be stored",
    )

    put_frame_parser.set_defaults(func=put_frame)

    # get frame parser
    get_frame_parser = subparsers.add_parser(
        "get-frame",
        help="Download a Pandas Dataframe as a Parquet file from the store",
    )

    get_frame_parser.add_argument(
        "-f",
        "--file",
        type=str,
        help="Path of file where data frame is stored in store",
    )

    get_frame_parser.set_defaults(func=get_frame)

    list_parser = subparsers.add_parser(
        "ls",
        help="List file of selected directory of the store",
    )

    list_parser.add_argument(
        "-p",
        "--path",
        type=str,
        help="Path of directory in store to list",
        # default=".",
    )

    list_parser.set_defaults(func=list_elements)

    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s.%(msecs)03d %(levelname)s %(name)s %(message)s",
        datefmt="%H:%M:%S",
    )

    s = store.Client(bucket=args.bucket)

    return args.func(s, args)
