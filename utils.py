# system libraries
import os
import json
import hashlib
import pickle
import shutil

# 3rd party libraries
import magic

# custom libraries
from constants import Constants
from colorama import Fore


class Utils:
    """All the utility methods"""
    print_ = print

    @staticmethod
    def parse_config_file(verbose=True):
        """parsing config.json"""

        print = Utils.print_ if verbose else lambda *args, **kwargs: True

        if os.path.exists(Constants.CONFIG_FILE_PATH):
            config = json.loads(open(Constants.CONFIG_FILE_PATH).read())
            if config['version'] == '1.0.0':
                Utils.preprocess_vide_paths(config['vide_directory_absolute'])
            else:
                raise NotImplementedError(Fore.RED + 'version not understood!' + Fore.RED)
        else:
            with open('config.json', 'w') as f:
                f.write('{"version":"1.0.0","vide_directory_absolute":[],"max_HLS_folder_size_GB":1}')
            raise FileNotFoundError(Fore.RED + 'Unable to find config.json in the directory. Creating a new '
                                               'config.json,  please add the video folder absolute paths inside '
                                               '"vide_directory_absolute": []' + Fore.RED)

    @staticmethod
    def preprocess_vide_paths(list_of_absolute_paths, verbose=True):
        """method to `walk` through the absolute paths, determine which are video file and create initial index"""

        print = Utils.print_ if verbose else lambda *args, **kwargs: True

        print('files to be processed:', Fore.GREEN + ', '.join(list_of_absolute_paths) + Fore.RESET)
        hash_index = {}
        for each_path in list_of_absolute_paths:
            for (root, dirs, files) in os.walk(each_path):
                folder_name = os.path.basename(root)
                # now we will check the mimetype of each file to detect if it is a video file
                for file in files:
                    mime_type = magic.from_file(os.path.join(root, file), mime=True)
                    if mime_type.startswith('video') or mime_type.startswith('application'):
                        # now we will calculate Md5 hash for the file and store the signature to database
                        md5_hash = Utils.calculate_md5_hash(os.path.join(root, file))
                        hash_index[md5_hash] = os.path.join(root, file)
        # pickling the data for diff calculation
        pickle.dump(hash_index, open(Constants.HASH_INDEX_FILE_PATH, 'wb'))
        Utils.diff_calculate()

    @staticmethod
    def calculate_md5_hash(absolute_file_path):
        return hashlib.md5(open(absolute_file_path, 'rb').read()).hexdigest()

    @staticmethod
    def diff_calculate(verbose=True):
        """calculate the change in file content"""

        print = Utils.print_ if verbose else lambda *args, **kwargs: True

        if os.path.exists(Constants.CONFIG_LOCK_FILE_PATH):
            print(Fore.GREEN + 'config-loc.json found, processing...' + Fore.RESET)
            # lock type file
            config_lock = json.load(open(Constants.CONFIG_LOCK_FILE_PATH))
            # pickled index file each time this file run
            temp_pkl = pickle.load(open(Constants.HASH_INDEX_FILE_PATH, 'rb'))

            # now we have to calculate insertion, deletion
            # |<----temp_pkl(A)---->|<----config_lock(B)---->|
            intersection = set(temp_pkl.keys()).intersection(config_lock.keys())
            for each_hash in intersection:
                if temp_pkl[each_hash] != config_lock[each_hash]:
                    # that means content of file is same but file is moved, so rename file
                    Utils.db_rename_file(file_id=each_hash,
                                         file_old_absolute_path=config_lock[each_hash],
                                         file_new_absolute_path=temp_pkl[each_hash])

            difference_a = set(temp_pkl.keys()).difference(config_lock.keys())
            for each_hash in difference_a:
                # create new entry
                Utils.db_create_file(file_id=each_hash, file_absolute_path=temp_pkl[each_hash])

            difference_b = set(config_lock.keys()).difference(temp_pkl)
            for each_hash in difference_b:
                # delete this file since it no longer exists
                Utils.db_delete_file(file_id=each_hash,
                                     file_absolute_path=config_lock[each_hash])
        else:
            print(Fore.RED + 'no config-loc.json found, recalculating everything' + Fore.RESET)
            with open(Constants.CONFIG_LOCK_FILE_PATH, 'w') as f:
                f.write(json.dumps(pickle.load(open(Constants.HASH_INDEX_FILE_PATH, 'rb'))))

            Utils.clear_text_search_engine_and_database()
            for k, v in pickle.load(open(Constants.HASH_INDEX_FILE_PATH, 'rb')).items():
                Utils.db_create_file(file_id=k, file_absolute_path=v)

    @staticmethod
    def db_rename_file(file_id, file_old_absolute_path, file_new_absolute_path, verbose=True):
        """rename entry from text search engine and Tinydb"""

        print = Utils.print_ if verbose else lambda *args, **kwargs: True

        print(Fore.YELLOW + f'DB RENAME {file_id, file_old_absolute_path, file_new_absolute_path}' + Fore.RESET)
        pass

    @staticmethod
    def db_delete_file(file_id, file_absolute_path, verbose=True):
        """delete entry from text search engine and Tinydb"""

        print = Utils.print_ if verbose else lambda *args, **kwargs: True

        print(Fore.YELLOW + f'DB RENAME {file_id, file_absolute_path}' + Fore.RESET)
        pass

    @staticmethod
    def db_create_file(file_id, file_absolute_path, verbose=True):
        """create new entry in text search engine and Tinydb"""

        print = Utils.print_ if verbose else lambda *args, **kwargs: True

        print(Fore.YELLOW + f'DB RENAME {file_id, file_absolute_path}' + Fore.RESET)
        pass

    @staticmethod
    def clear_text_search_engine_and_database(verbose=True):
        """This method reset the text search engine index (Whoosh) and drop everything from Tinydb"""

        print = Utils.print_ if verbose else lambda *args, **kwargs: True

        print(Fore.RED + 'clearing Whoosh search engine and deleting old TinyDB database' + Fore.RESET)
        # handling Whoosh database folder
        if not os.path.exists("index"):
            os.mkdir('index')
        else:
            shutil.rmtree('index')
            os.mkdir('index')

        # handling Tinydb database folder
        if not os.path.exists('db.json'):
            with open('db.json', 'w') as f:
                pass
        else:
            os.remove('db.json')
            with open('db.json', 'w') as f:
                pass




if __name__ == '__main__':
    Utils.parse_config_file()
