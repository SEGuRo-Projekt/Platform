from minio import Minio
import os
import io

def connect_to_storage(SERVER, PORT, ACCESS_KEY, SECRET_KEY):
    client = Minio(endpoint=SERVER+":"+PORT,
                   access_key=ACCESS_KEY,
                   secret_key=SECRET_KEY,
                   secure=False)
    return client

def get_file(client, filename, file, bucket="seguro"):
    if not client.bucket_exists(bucket):
        print(f"Error: Bucket \"{bucket}\" does not exist...")
        return

    client.fget_object(
        bucket, file, filename
    )


def put_file(client, filename, file, bucket="seguro"):
    if not client.bucket_exists(bucket):
        print(f"Error: Bucket \"{bucket}\" does not exist...")
        return

    client.fput_object(
        bucket, filename, file
    )

def write_to_file(client, filename, message, bucket="seguro"):
    if not client.bucket_exists(bucket):
        print(f"Error: Bucket \"{bucket}\" does not exist...")
        return

    client.put_object(
        bucket, filename, io.BytesIO(b"%a" % message), len(message)
    )

def file_changed(client, filename, last_modified, bucket="seguro"):
    if not client.bucket_exists(bucket):
        print(f"Error: Bucket \"{bucket}\" does not exist...")
        return

    stats = client.stat_object(
        bucket, filename
    )

    if last_modified != stats._last_modified:
        return True
    else:
        return False


if __name__ == "__main__":
    client = connect_to_storage("localhost", "9000", os.environ["S3_ACCESS_KEY"], os.environ["S3_SECRET_KEY"])


    buckets = client.list_buckets()
    for bucket in buckets:
        print(bucket.name, bucket.creation_date)

    # put_file(client, "MyFile", "./helperFunctions.py")
    # get_file(client, "MyFile.py", "MyFile", bucket="auto")
    # stats1 = file_changed(client, "log.txt", bucket="testbucket")
    write_to_file(client, "log.txt", "Mys log message...\n", bucket="testbucket")
    # client.make_bucket("my-bucket")
