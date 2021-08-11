import os
import datetime
import random
import shutil

from tinydb import TinyDB, Query
from colorama import Fore
import ffmpeg

from constants import Constants


class VideoHandler:
    @staticmethod
    def update_video_data():
        """method to create thumbnail and update video meta data"""
        if not os.path.exists(Constants.THUMBNAIL_FOLDER_PATH):
            os.mkdir(Constants.THUMBNAIL_FOLDER_PATH)
        # get all the videos for which thumbnail_abs_path == None
        db = TinyDB(Constants.DATABASE_FILE_PATH)
        Video = Query()
        for each_file in db.search(Video.thumbnail_path == None):
            try:
                probe = ffmpeg.probe(each_file['abs_path'])
                video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
                audio_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'audio'), None)
                width = int(video_stream.get('width', 0))
                height = int(video_stream.get('height', 0))
                duration = datetime.timedelta(seconds=float(video_stream.get('duration', 0)))
                v_bitrate = int(video_stream.get('bit_rate', 0))
                a_bitrate = int(audio_stream.get('bit_rate', 0))

                # making folder for each of the video
                if os.path.exists(os.path.join(Constants.THUMBNAIL_FOLDER_PATH, str(each_file["id"]))):
                    shutil.rmtree(os.path.join(Constants.THUMBNAIL_FOLDER_PATH, str(each_file["id"])))
                os.mkdir(os.path.join(Constants.THUMBNAIL_FOLDER_PATH, str(each_file["id"])))

                for i in range(1, 4):
                    (
                        ffmpeg
                            .input(each_file['abs_path'],
                                   ss=str(datetime.timedelta(
                                       seconds=random.randint(0,
                                                              int(float(video_stream.get('duration', 0)))))).split(
                            ',')[-1].strip())
                            .output(f'./{Constants.THUMBNAIL_FOLDER_PATH}/{each_file["id"]}/{each_file["id"]}_{i}.png', vframes=1)
                            .run()
                    )
                db.update({
                    'thumbnail_path': f'./{Constants.THUMBNAIL_FOLDER_PATH}/{each_file["id"]}',
                    'duration': duration,
                    'width': width,
                    'height': height,
                    'v_bitrate': v_bitrate,
                    'a_bitrate': a_bitrate,
                }, Video.id == each_file['id'])
            except Exception as e:
                print(Fore.RED + f'[[ERROR]] while processing {each_file["file_name"]}...' + Fore.RESET)
                print(Fore.RED + str(e) + Fore.RESET)
