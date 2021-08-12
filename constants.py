class Constants:
    """All the program constants kept here"""
    ACCEPT_FILE_FORMATS = ('.webm', '.mkv', '.flv', '.flv',
                           '.vob', '.ogv', '.ogg', '.drc',
                           '.gif', '.gifv', '.mng', '.avi',
                           '.MTS', '.M2TS', '.TS', '.mov',
                           '.qt', '.wmv', '.yuv', '.rm',
                           '.rmvb', '.viv', '.asf', '.amv',
                           '.mp4', '.m4p (with DRM)', '.m4v', '.mpg',
                           '.mp2', '.mpeg', '.mpe', '.mpv',
                           '.mpg', '.mpeg', '.m2v', '.m4v',
                           '.svi', '.3gp', '.3g2', '.mxf',
                           '.roq', '.nsv', '.flv', '.f4v',
                           '.f4p', '.f4a', '.f4b',
                           )
    CONFIG_FILE_PATH = './config.json'
    CONFIG_LOCK_FILE_PATH = './config-lock.json'
    HASH_INDEX_FILE_PATH = './hash_index.pkl'
    DATABASE_FILE_PATH = './db.json'
    WHOOSH_INDEX_PATH = './index'
    THUMBNAIL_FOLDER_PATH = './thumbnails'
    HLS_OUTPUT_PATH = './HLS'
