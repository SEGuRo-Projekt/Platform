# SPDX-FileCopyrightText: 2026 Henrik Hörter
# SPDX-License-Identifier: Apache-2.0
import argparse
import pandas as pd
import logging
from pathlib import Path

from seguro.common import store
from seguro.common import config


# push file/directory to S3 store
def push(s: store.Client, args):
    remotepath = Path(args.remotefile)
    for localfile in args.localfile:
        localpath = Path(localfile).resolve()
        if len(args.localfile) > 1:
            new_remote = str(remotepath.joinpath(localpath.relative_to(localpath.parents[0])))
        else:
            new_remote = args.remotefile
        push_one(s, localfile, new_remote)


def push_one(s: store.Client, localfile: str, remotefile: str):

    localpath = Path(localfile).resolve()
    remotepath = Path(remotefile)

    if localpath.is_file():
        s.put_file(remotefile, localfile)  # pushing a file
    elif localpath.is_dir():
        for element in localpath.iterdir():
            if element.is_dir():
                new_remote = str(remotepath.joinpath(element.relative_to(localpath))) + "/"
            else:
                new_remote = str(remotepath.joinpath(element.relative_to(localpath)))

            push_one(s, str(element), new_remote)
    return


# pull file/directory from S3 store
def pull(s: store.Client, args):
    if args.remotefile.endswith("*"):
        remotebase = args.remotefile.split("*", 1)[0]
    else:
        remotebase = args.remotefile
    objects = list(s.client.list_objects(bucket_name=s.bucket, prefix=remotebase, recursive=True))

    if not objects:
        raise FileNotFoundError(f"Remote object not found: {args.remotefile}, nothing was found to be pulled")

    pulled = False
    exact_match_pulled = False

    localbase = Path(args.localfile).absolute()
    remotebase = Path(args.remotefile)

    for obj in objects:

        # pull with globbing
        if args.globbing or args.remotefile.endswith("*"):
            new_remotebase = remotebase.parents[0]

            # set up localpath
            relative_remotepath = Path(obj.object_name).relative_to(new_remotebase)
            new_localpath = localbase.joinpath(relative_remotepath)
            localfile = str(new_localpath)
            remotefile = obj.object_name

            s.get_file(localfile, obj.object_name)
            pulled = True
            continue

        # pull exactly one object
        if obj.object_name == args.remotefile and not exact_match_pulled:
            if localbase.is_dir():  # also covers the "." case
                localfile = str(localbase.joinpath(remotebase.name))
            else:
                localfile = str(localbase)
            s.get_file(localfile, args.remotefile)
            pulled = True
            exact_match_pulled = True
            return 0

        # pull entire directory

        # check if user inteded to pull dir but forgot /
        if not args.remotefile.endswith("/"):
            remotepath_as_dir = args.remotefile + "/"
        else:
            remotepath_as_dir = args.remotefile

        if obj.object_name.startswith(remotepath_as_dir):

            # set up localpath
            relative_remotepath = Path(obj.object_name).relative_to(remotebase)
            new_localpath = localbase.joinpath(remotebase.name).joinpath(relative_remotepath)
            localfile = str(new_localpath)
            remotefile = obj.object_name

            s.get_file(localfile, remotefile)
            pulled = True

    if not pulled:
        print(f"Remote object not found: {args.remotefile}, nothing was pulled")

    return 0


# remove file/directory from S3 store
def remove(s: store.Client, args):
    objects = list(s.client.list_objects(bucket_name=s.bucket, prefix=args.file, recursive=True))

    if not objects:
        raise FileNotFoundError(f"Remote object not found: {args.file}, nothing was removed")

    removed = False
    exact_match_removed = False

    for obj in objects:
        # remove with globbing
        if args.globbing:
            s.remove_file(obj.object_name)
            removed = True
            continue

        # remove exactly one object
        if obj.object_name == args.file and not exact_match_removed:
            s.remove_file(args.file)
            removed = True
            exact_match_removed = True
            return 0

        # remove directory
        # check if user intended to remove dir but forgot /
        if not args.file.endswith("/"):
            path_as_dir = args.file + "/"
        else:
            path_as_dir = args.file

        if obj.object_name.startswith(path_as_dir):
            s.remove_file(obj.object_name)
            removed = True

    if not removed:
        print(f"Remote object not found: {args.file}, nothing was removed")

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

    for object in objects:  # get all objects from Store
        element_in_dir = str(Path(object.object_name).relative_to(remotebase))
        if object.object_name.endswith("/"):
            element_in_dir += "/"
        print(element_in_dir)


def main():
    parser = argparse.ArgumentParser(prog="s3_tool", description="Tool to interact with S3 storage")

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

    push_parser = subparsers.add_parser("push", help="Push a local file/dir to store")
    push_parser.add_argument(
        "-lf",
        "--localfile",
        type=str,
        help="Local file(s)/dir to be pushed",
        nargs="*",
    )
    push_parser.add_argument("-rf", "--remotefile", type=str, help="Path of file/dir in store")
    push_parser.set_defaults(func=push)

    pull_parser = subparsers.add_parser("pull", help="Pull file/dir from store")

    pull_parser.add_argument(
        "-g",
        "--globbing",
        action="store_true",
        help="Pull all objects that have remotepath as prefix",
    )

    pull_parser.add_argument(
        "-rf",
        "--remotefile",
        type=str,
        help="Path of file/dir to be pulled from store",
    )
    pull_parser.add_argument(
        "-lf",
        "--localfile",
        type=str,
        help="Local path where file(s)/dir will be stored",
    )

    pull_parser.set_defaults(func=pull)

    remove_parser = subparsers.add_parser("remove", help="Remove a file/dir from  store")
    remove_parser.add_argument("-f", "--file", type=str, help="Path of file/dir in store")
    remove_parser.add_argument(
        "-g",
        "--globbing",
        action="store_true",
        help="Remove all objects that have remotepath as prefix",
    )
    remove_parser.set_defaults(func=remove)

    list_parser = subparsers.add_parser(
        "ls",
        help="List file of selected directory in store",
    )

    list_parser.add_argument(
        "-p",
        "--path",
        type=str,
        help="Path of directory in store to list",
        default=".",
    )

    list_parser.set_defaults(func=list_elements)

    get_file_parser = subparsers.add_parser("get-file", help="Get a file from the storage")

    get_file_parser.add_argument(
        "-rf",
        "--remotefile",
        type=str,
        help="Path in the storage",
    )

    get_file_parser.add_argument("-lf", "--localfile", type=str, help="Path to the local file")

    get_file_parser.set_defaults(func=get_file)

    get_file_content_parser = subparsers.add_parser("get-file-content", help="Get file content into terminal")

    get_file_content_parser.add_argument("-f", "--file", type=str, help="Path of file in storage")

    get_file_content_parser.set_defaults(func=get_file_content)

    put_file_content_parser = subparsers.add_parser(
        "put-file-content", help="Add filecontent as bytes into file in store"
    )

    put_file_content_parser.add_argument("-f", "--file", type=str, help="Path to file in store")

    put_file_content_parser.add_argument(
        "-c",
        "--content",
        type=str,
        help="Content that is written to file in store",
    )

    put_file_content_parser.set_defaults(func=put_file_content)

    get_file_url_parser = subparsers.add_parser("get-file-url", help="Get File URL")

    get_file_url_parser.add_argument("-f", "--file", type=str, help="Path of file in storage")

    get_file_url_parser.set_defaults(func=get_file_url)

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

    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s.%(msecs)03d %(levelname)s %(name)s %(message)s",
        datefmt="%H:%M:%S",
    )

    s = store.Client(bucket=args.bucket)

    return args.func(s, args)
