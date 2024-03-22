import argparse


def split_string(values):
    return values.split(",") if values else []


parser = argparse.ArgumentParser(description="File name encryption and decryption")

parser.add_argument(
    "-d",
    "--directory",
    required=True,
    type=str,
    metavar="--directory",
    help="Target directory that will be encrypted or decrypted",
)

parser.add_argument(
    "-r",
    "--recursive",
    action="store_true",
    help="Recursively encrypt files in subdirectories",
)

parser.add_argument(
    "-s", "--sort", action="store_true", help="Order files by modified timestamp"
)

parser.add_argument(
    "-hh",
    "--hash",
    action="store_true",
    help="Encrypt or Decrypt the directory name",
)

parser.add_argument(
    "-i", "--use_index", action="store_true", help="Encrypt filename by index"
)

parser.add_argument(
    "-ii",
    "--include",
    type=split_string,
    help="Include specific file extension to be encrypted or decrypted",
)

parser.add_argument(
    "-ex",
    "--exclude",
    type=split_string,
    help="Exclude specific folder to not be encrypted or decrypted",
)

args = parser.parse_args()
