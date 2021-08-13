# system libraries
import os
import json
import hashlib
import pickle
import shutil
import re

# 3rd party libraries
#import magic
from colorama import Fore
from tinydb import TinyDB, Query
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID, NGRAMWORDS
from whoosh.qparser import QueryParser

# custom libraries
from constants import Constants
from video_handler import VideoHandler


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
        temporary_files_list = []
        hash_index = {}
        for each_path in list_of_absolute_paths:
            for (root, dirs, files) in os.walk(each_path):
                folder_name = os.path.basename(root)
                # now we will check the mimetype of each file to detect if it is a video file
                for file in files:
                    print(f'\rProcessing {file}...', end='', flush=True)
                    # mime_type = magic.from_file(os.path.join(root, file), mime=True)
                    # if mime_type.startswith('video') or mime_type.startswith('application'):
                    if file.endswith(Constants.ACCEPT_FILE_FORMATS):
                        temporary_files_list.append(os.path.join(root, file))
        for index, absolute_file_name in enumerate(temporary_files_list, 1):
            # now we will calculate Md5 hash for the file and store the signature to database
            print(f'\r[{round((index / len(temporary_files_list)) * 100)}%] Calculating Md5 hash for '
                  f'{os.path.basename(absolute_file_name)}...', end='', flush=True)
            md5_hash = Utils.calculate_md5_hash(absolute_file_name)
            hash_index[md5_hash] = absolute_file_name
        print()
        del temporary_files_list
        # pickling the data for diff calculation
        pickle.dump(hash_index, open(Constants.HASH_INDEX_FILE_PATH, 'wb'))
        Utils.diff_calculate()
        # to create thumbnail, video metadata etc
        VideoHandler.update_video_data()

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
            # now that files are in sync, we want to lock the file
            with open(Constants.CONFIG_LOCK_FILE_PATH, 'w') as f:
                f.write(json.dumps(temp_pkl))
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

        print(Fore.BLUE + f'[[DB RENAME]] {file_id, file_old_absolute_path, file_new_absolute_path}' + Fore.RESET)
        db = TinyDB(Constants.DATABASE_FILE_PATH)
        Video = Query()
        db.update({'file_name': Utils.format_file_name(os.path.basename(file_new_absolute_path)),
                   'abs_path': file_new_absolute_path,
                   }, Video.id == file_id)
        # updating whoosh
        ix = open_dir(Constants.WHOOSH_INDEX_PATH)
        writer = ix.writer()
        writer.delete_by_term('video_id', file_id)
        writer.add_document(video_name=Utils.format_file_name(os.path.basename(file_new_absolute_path)),
                            video_id=file_id)
        writer.commit()

    @staticmethod
    def db_delete_file(file_id, file_absolute_path, verbose=True):
        """delete entry from text search engine and Tinydb"""

        print = Utils.print_ if verbose else lambda *args, **kwargs: True

        print(Fore.RED + f'[[DB DELETE]] {file_id, file_absolute_path}' + Fore.RESET)
        # delete a file
        db = TinyDB(Constants.DATABASE_FILE_PATH)
        Video = Query()
        # removing thumbnail
        thumbnail_path = db.search(Video.id == file_id)[0]['thumbnail_path']
        if thumbnail_path:
            shutil.rmtree(thumbnail_path)
        # finally dropping the data from database
        db.remove(Video.id == file_id)

        # deleting entry from whoosh
        ix = open_dir(Constants.WHOOSH_INDEX_PATH)
        writer = ix.writer()
        writer.delete_by_term('video_id', file_id)
        writer.commit()

    @staticmethod
    def db_create_file(file_id, file_absolute_path, verbose=True):
        """create new entry in text search engine and Tinydb"""

        print = Utils.print_ if verbose else lambda *args, **kwargs: True

        print(Fore.YELLOW + f'[[DB CREATE]] {file_id, file_absolute_path}' + Fore.RESET)
        # inserting data to database
        db = TinyDB(Constants.DATABASE_FILE_PATH)
        db.insert({'id': file_id,
                   'file_name': Utils.format_file_name(os.path.basename(file_absolute_path)),
                   'abs_path': file_absolute_path,
                   'thumbnail_path': None,
                   'duration': None,
                   'width': None,
                   'height': None,
                   'format_name': None,
                   'size': None,
                   'v_bitrate': None,
                   'a_bitrate': None,
                   'is_favourite': False,
                   'hls_processing': False,
                   'hls_already_processed': False,
                   'hls_process_location': '',
                   'cluster_id': None,
                   'views': 0
                   })
        # now we will insert into Whoosh text search
        ix = open_dir(Constants.WHOOSH_INDEX_PATH)
        writer = ix.writer()
        writer.add_document(video_name=Utils.format_file_name(os.path.basename(file_absolute_path)),
                            video_id=file_id)
        writer.commit()

    @staticmethod
    def clear_text_search_engine_and_database(verbose=True):
        """This method reset the text search engine index (Whoosh) and drop everything from Tinydb"""

        print = Utils.print_ if verbose else lambda *args, **kwargs: True

        print(Fore.RED + 'clearing Whoosh search engine and deleting old TinyDB database' + Fore.RESET)
        # handling Whoosh database folder
        if not os.path.exists(Constants.WHOOSH_INDEX_PATH):
            os.mkdir(Constants.WHOOSH_INDEX_PATH)
            create_in(Constants.WHOOSH_INDEX_PATH, Schema(video_name=NGRAMWORDS(stored=True), video_id=ID(stored=True)))
        else:
            shutil.rmtree(Constants.WHOOSH_INDEX_PATH)
            os.mkdir(Constants.WHOOSH_INDEX_PATH)
            create_in(Constants.WHOOSH_INDEX_PATH, Schema(video_name=NGRAMWORDS(stored=True), video_id=ID(stored=True)))

        # handling Tinydb database folder
        if not os.path.exists(Constants.DATABASE_FILE_PATH):
            with open(Constants.DATABASE_FILE_PATH, 'w') as f:
                pass
        else:
            os.remove(Constants.DATABASE_FILE_PATH)
            with open(Constants.DATABASE_FILE_PATH, 'w') as f:
                pass

        # removing HLS folder
        if os.path.exists(Constants.HLS_OUTPUT_PATH):
            shutil.rmtree(Constants.HLS_OUTPUT_PATH)

    @staticmethod
    def format_file_name(bad_file_name):
        """remove any special characters from file name"""
        return re.sub(r'\s+', ' ', re.sub(r'[^a-z\d\s]', ' ', bad_file_name.lower().split('.')[0])).strip()


if __name__ == '__main__':
    # remove config.json
    # os.remove('config-lock.json')

    # test database
    Utils.parse_config_file()

    # print all the data inside Tinydb
    # db = TinyDB(Constants.DATABASE_FILE_PATH)
    # print(db.all())

    # test Whoosh text search
    ix = open_dir(Constants.WHOOSH_INDEX_PATH)
    # print all the data inside Whoosh
    # print(list(ix.searcher().documents()))
    # with ix.searcher() as searcher:
    #     query = QueryParser("video_name", ix.schema).parse("ik va")
    #     results = searcher.search(query)
    #     print(list(results))
