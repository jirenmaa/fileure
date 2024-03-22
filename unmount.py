import os
from datetime import datetime
from typing import Iterator, List, Tuple, cast
from uuid import uuid4

import filedate

from utils.decrypt import decrypt
from utils.argparser import args

EXCLUDED_FILES: list[str] = []

# change here, example : png, jpg, ...
ALLOWED_SUFFIX: tuple[str, ...] = ()

# Define a type alias for the files type
FILE_INFOS = List[os.DirEntry[str]]


def get_files(dir_path: str, recursive: bool = False) -> FILE_INFOS:
    """
    Get a list of files and directories in the given directory path.

    Args:
        dir_path (str): The directory path to scan.
        recursive (bool): Recursively scan subdirectories if True.

    Returns:
        List[os.DirEntry[str]]: A list of file.

    """
    # Get the list of files and directories in the given directory path
    dirs: Iterator[os.DirEntry[str]] = os.scandir(dir_path)

    files: FILE_INFOS = []

    for file in dirs:
        is_directory: bool = file.is_dir()

        # Skip excluded directories
        if is_directory and file.name in EXCLUDED_FILES:
            continue

        # If it's a directory and recursive is True, scan the subdirectory
        if is_directory and recursive:
            # Recursive call to scan the subdirectory
            files += get_files(dir_path=file.path, recursive=recursive)

        files.append(file)

    return files


def separate_file_and_directory(files: FILE_INFOS) -> FILE_INFOS:
    """
    Separate files and directories from a list of file information.

    Args:
        files (FILE_INFOS): A list of file information.

    Returns:
        FILE_INFOS: A list of files followed by directories.

    """
    files_list: os.DirEntry[str] = []
    dirs_list: os.DirEntry[str] = []

    # Separate files and directories
    for file_info in files:
        if file_info.is_dir():
            dirs_list.append(file_info)
        else:
            files_list.append(file_info)

    # Sort directories by length of 'root' (if it exists)
    dirs_list.sort(key=lambda d: len(d.path), reverse=True)

    # Return files followed by directories
    return files_list + dirs_list


def decode_file(
    filename: str, use_index_filename: bool = False
) -> Tuple[str, str, str]:
    (
        hashed_modified_time,
        hashed_extension,
        hashed_key,
        *hashed_filename,
    ) = filename.split("-")

    """
    # the format when mounted (hashed)
    filename : hashed_modified_time-hashed_extension-hashed_key

    modified_time : encrypted with `hashed_extension` as the key
    key           : encrypted with `modified_time` as the key
    extension     : encrypted with `key_segment` as the key
    filename      : encrypted with `key_segment` as the key

    # if it is a folder or using indexed name then
    filename : hashed_modified_time-hashed_extension-hashed_key-additional_name
    """

    decrypted_modified_time: str = decrypt(hashed_extension, hashed_modified_time)
    decrypted_key: str = decrypt(decrypted_modified_time, hashed_key)
    decrypted_extension: str = decrypt(decrypted_key, hashed_extension)

    og_filename: str = ""  # original filename before encoded

    # if hashed_filename is not empty then the
    # current given filename are a directory
    if hashed_filename or use_index_filename:
        directory_name: str = "".join(hashed_filename)
        og_filename = decrypt(decrypted_key, directory_name)

    return (decrypted_modified_time, decrypted_extension, og_filename)


def change_file_names(
    files: FILE_INFOS,
    decrypt_directory_name: bool = False,
    use_index_filename: bool = False,
) -> None:
    for file in files:
        file_root = file.path.split("\\")[:-1]
        file_root_dir = "\\".join(file_root)

        is_file_dir = file.is_dir()

        modified_time, extension, filename = decode_file(file.name, use_index_filename)

        # since the modified_time encoded with utf-8,
        # it need to be decoded first
        modified_time = bytes.fromhex(modified_time).decode("utf8")

        # https://stackoverflow.com/a/27549388/14182545
        # change into windows modified time readable string
        formatted_modified_time = datetime.fromtimestamp(int(modified_time)).strftime(
            "%A, %B %d, %Y, %H:%M:%S"
        )

        """
        Sometimes when changing the modified date of a file (filedate.File) the process
        are preceded by os.rename and will print error :

            FileNotFoundError: [WinError 2] The system cannot find the file specified:

        because the file already renamed before the filedate modify the file property (modified date)
        """
        try:
            # change the current file modifed date to the new formatted modified date
            filedate.File(file.path).set(modified=formatted_modified_time)
            try:
                file_extension: str = ""

                if not is_file_dir:
                    file_extension = "." + extension

                if not filename and not use_index_filename:
                    filename = str(uuid4())

                new_filename = "{dir_path}\\{filename}{extension}".format(
                    dir_path=file_root_dir, filename=filename, extension=file_extension
                )

                os.rename(file.path, new_filename)
            except Exception as ex:
                print(ex)
        except:
            break


def change_root_directory_name(root_dir: str) -> None:
    root_folder_path = "\\".join(root_dir.split("\\")[:-1])
    root_folder_name = root_dir.split("\\")[-1]

    _, _, dir_name = decode_file(root_folder_name)

    new_root_directory_name = "{dir_path}\\{dir_name}".format(
        dir_path=root_folder_path,
        dir_name=dir_name,
    )

    os.rename(root_dir, new_root_directory_name)


def setup() -> List[str | bool]:
    global EXCLUDED_FILES, ALLOWED_SUFFIX

    if args.exclude:
        EXCLUDED_FILES = args.exclude

    if args.include:
        ALLOWED_SUFFIX = tuple(list(ALLOWED_SUFFIX) + args.include)

    root_directory: str = args.directory

    use_index_filename: bool = args.use_index
    hash_directory_name: bool = args.hash
    recursive_directory: bool = args.recursive

    return [
        root_directory,
        hash_directory_name,
        recursive_directory,
        use_index_filename,
    ]


if __name__ == "__main__":
    """
    USAGE : py unmount.py --hash --use_index --recursive --directory x:\\path\\
          : py unmount.py -hh -r -d x:\\path\\

          : py unmount.py -hh -i -d x:\\path\\
    """
    (
        root_directory,
        decrypt_directory_name,
        recursive_directory,
        use_index_filename,
    ) = setup()

    files: FILE_INFOS = get_files(
        cast(str, root_directory), cast(bool, recursive_directory)
    )

    separted_file_dir = separate_file_and_directory(files)

    change_file_names(
        files, cast(bool, decrypt_directory_name), cast(bool, use_index_filename)
    )

    if decrypt_directory_name:
        change_root_directory_name(root_directory)
