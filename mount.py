import codecs
import math
import os
from typing import Iterator, Dict, List, cast
from uuid import uuid4

from utils.argparser import args
from utils.encrypt import encrypt

EXCLUDED_FILES: list[str] = []

# change here, example : png, jpg, ...
ALLOWED_SUFFIX: tuple[str, ...] = ()

# Define a type alias for the files type
FILE_INFOS = List[Dict[str, str | bool]]


def get_files(
    dir_path: str,
    order_by_timestamp: bool = False,
    recursive: bool = False,
) -> FILE_INFOS:
    """
    Get a list of files and directories in the given directory path.

    Args:
        dir_path (str): The directory path to scan.
        order_by_timestamp (bool): Order files by timestamp if True.
        recursive (bool): Recursively scan subdirectories if True.

    Returns:
        List[Dict[str, str | bool]]: A list of file information.

    """
    # Get the list of files and directories in the given directory path
    dirs: Iterator[os.DirEntry[str]] = os.scandir(dir_path)

    # Sort the files by modification time in descending order
    if order_by_timestamp:
        dirs = sorted(dirs, key=lambda entry: entry.stat().st_mtime, reverse=True)

    files: FILE_INFOS = []

    for file in dirs:
        is_directory: bool = file.is_dir()

        # Skip excluded directories
        if is_directory and file.name in EXCLUDED_FILES:
            continue

        # If it's a directory and recursive is True, scan the subdirectory
        if is_directory and recursive:
            # Add encoded file into the array (used for renaming)
            encoded_file = encode_file(file)
            files.append(encoded_file)

            # Recursive call to scan the subdirectory
            files += get_files(
                dir_path=file.path,
                order_by_timestamp=order_by_timestamp,
                recursive=recursive,
            )

        # Check if the file has an allowed suffix
        if not file.name.endswith(ALLOWED_SUFFIX):
            continue

        # Add encoded file information to the list
        encoded_file = encode_file(file)
        files.append(encoded_file)

    return separate_file_and_directory(files)


def sort_by_filename(file: os.DirEntry[str]) -> str:
    if file.is_dir():
        return file.name

    # get the filename without their extension
    return file.name.split(".")[0]


def separate_file_and_directory(files: FILE_INFOS) -> FILE_INFOS:
    """
    Separate files and directories from a list of file information.

    Args:
        files (FILE_INFOS): A list of file information.

    Returns:
        FILE_INFOS: A list of files followed by directories.

    """
    files_list = []
    dirs_list = []

    # Separate files and directories
    for file_info in files:
        if file_info.get("is_dir"):
            dirs_list.append(file_info)
        else:
            files_list.append(file_info)

    # Sort directories by length of 'root' (if it exists)
    dirs_list.sort(key=lambda d: len(d.get("root", "")), reverse=True)

    # Return files followed by directories
    return files_list + dirs_list


def encode_file(file: os.DirEntry[str]) -> Dict[str, str | bool]:
    """
    Encode file information.

    Args:
        file_entry (os.DirEntry[str]): A directory entry representing a file.

    Returns:
        Dict[str, str | bool]: Encoded file information.

    """
    file_info: Dict[str, str | bool] = {}

    # the date need to be rounded since it will be used as part
    # for the naming file (modified date)
    mdate: int = math.ceil(file.stat().st_mtime)
    # encode the modified date to hexadecimal
    encoded_mdate = codecs.encode(str(mdate)).hex()

    file_info["root"] = file.path
    file_info["name"] = file.name
    file_info["mtime"] = encoded_mdate
    file_info["is_dir"] = file.is_dir()

    return file_info


def change_file_names(
    files: List[Dict[str, str | bool]],
    hash_directory_name: bool = False,
    use_index_filename: bool = False,
) -> None:
    for file in files:
        is_file_dir = file.get("is_dir")

        mtime = str(file.get("mtime", ""))  # modified time
        fname = str(file.get("name", ""))  # file or folder name

        # if the file is directory set the extension to "folder"
        extension: str = fname.split(".").pop().lower() if not is_file_dir else "folder"

        key: list[str] = str(uuid4()).split("-")
        # extracts the second, third, and fourth segments
        # (the segments that correspond to the version number and the variant bits, which are fixed)
        key_segment: str = "-".join(key[1:4])

        hashed_extension: str = encrypt(key_segment, extension)
        # the key are hashed so it need more work to decrypt the extension name,
        # it need to get the decrypted (unhashed) key.
        hashed_key: str = encrypt(mtime, key_segment)
        hashed_mtime: str = encrypt(hashed_extension, mtime)

        # the additional name can be the "original root name" or "file number"
        additional_name: str = ""

        if not is_file_dir and use_index_filename:
            _nm = fname.split(".")[0]  # get the filename without the extension

            additional_name = "-" + encrypt(key_segment, _nm)

        if is_file_dir and hash_directory_name:
            additional_name = "-" + encrypt(key_segment, fname)

        filename = "{modified_time}-{extension}-{key}{additional_name}".format(
            modified_time=hashed_mtime,
            extension=hashed_extension,
            key=hashed_key,
            additional_name=additional_name,
        )

        # get root directory name without the file
        # example: c:\aa\bb\cc\dd.extension => c:\aa\bb\cc\
        directory: list[str] = str(file.get("root", "")).split("\\")[:-1]
        directory_root: str = "\\".join(directory)

        old_filename: str = str(file.get("root", ""))
        new_filename: str = f"{directory_root}\\{filename}"

        os.rename(old_filename, new_filename)


def setup() -> List[str | bool | Dict[str, str | bool]]:
    global EXCLUDED_FILES, ALLOWED_SUFFIX

    if args.exclude:
        EXCLUDED_FILES = args.exclude

    if args.include:
        ALLOWED_SUFFIX = tuple(list(ALLOWED_SUFFIX) + args.include)

    root_directory: str = args.directory

    hash_directory_name: bool = args.hash
    sort_by_timestamp: bool = args.sort
    use_index_filename: bool = args.use_index
    recursive_directory: bool = args.recursive

    # get the root parent directory to be hashed

    mdate: int = math.ceil(os.stat(root_directory).st_mtime)
    # encode the modified date to hexadecimal
    encoded_mdate = codecs.encode(str(mdate)).hex()

    root_dir: Dict[str, str | bool] = {
        "root": root_directory,
        "name": root_directory.split("\\")[-1],
        "mtime": encoded_mdate,
        "is_dir": True,
    }

    return [
        root_directory,
        hash_directory_name,
        sort_by_timestamp,
        use_index_filename,
        recursive_directory,
        root_dir,
    ]


if __name__ == "__main__":
    """
    USAGE : py mount.py --hash --sort --recursive --directory x:\\path\\
          : py mount.py -hh -s -r -d x:\\path\\

          : py mount.py -hh -i -d x:\\path\\
    """
    (
        root_directory,
        hash_directory_name,
        order_by_timestamp,
        use_index_filename,
        recursive_directory,
        root_dir,
    ) = setup()

    files: FILE_INFOS = get_files(
        cast(str, root_directory),
        cast(bool, order_by_timestamp),
        cast(bool, recursive_directory),
    )

    files.append(cast(Dict[str, str | bool], root_dir))

    change_file_names(
        files, cast(bool, hash_directory_name), cast(bool, use_index_filename)
    )
