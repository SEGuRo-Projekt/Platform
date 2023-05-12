from minio import Minio
import io
class S3Storage:
    def __init__(self, server, port, access_key, secret_key):
        self.tracked_files = {}
        self.client = self.__connect(server, port, access_key, secret_key)


    def __connect(self, SERVER, PORT, ACCESS_KEY, SECRET_KEY):
        client = Minio(endpoint=SERVER+":"+str(PORT),
                    access_key=ACCESS_KEY,
                    secret_key=SECRET_KEY,
                    secure=False)
        return client

    def get_file(self, filename, file, bucket="seguro"):
        if not self.client.bucket_exists(bucket):
            print(f"Error: Bucket \"{bucket}\" does not exist...")
            return

        self.client.fget_object(
            bucket, file, filename
        )


    def put_file(self, filename, file, bucket="seguro"):
        if not self.client.bucket_exists(bucket):
            print(f"Error: Bucket \"{bucket}\" does not exist...")
            return

        self.client.fput_object(
            bucket, filename, file
        )

    def write_to_file(self, filename, message, bucket="seguro"):
        if not self.client.bucket_exists(bucket):
            print(f"Error: Bucket \"{bucket}\" does not exist...")
            return

        self.client.put_object(
            bucket, filename, io.BytesIO(b'%b' % message.encode('utf8')), len(message)
        )

    def file_changed(self, filename, bucket="seguro"):
        if not self.client.bucket_exists(bucket):
            print(f"Error: Bucket \"{bucket}\" does not exist...")
            return

        stats = self.client.stat_object(
            bucket, filename
        )

        if filename not in self.tracked_files.keys():
            self.tracked_files[filename] = stats._last_modified
            # if file is not tracked yet, assume it has changed
            return True
        else:
            if self.tracked_files[filename] != stats._last_modified:
                print(self.tracked_files[filename])
                print(stats._last_modified)
                self.tracked_files[filename] = stats._last_modified
                return True
            else:
                print(self.tracked_files[filename])
                print(stats._last_modified)
                return False