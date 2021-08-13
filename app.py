import datetime
import glob
import os
import random
import re
import shutil
from multiprocessing import Process
import time

import ffmpeg_streaming
from colorama import Fore
from flask import Flask, jsonify, render_template, url_for, send_from_directory
from tinydb import TinyDB, Query
from whoosh.index import open_dir
from whoosh.qparser import QueryParser
from ffmpeg_streaming import Formats, Bitrate, Representation, Size

from constants import Constants
from utils import Utils

app = Flask(__name__)


def search_from_text_search_engine(token):
    ix = open_dir(Constants.WHOOSH_INDEX_PATH)
    with ix.searcher() as searcher:
        query = QueryParser("video_name", ix.schema).parse(token)
        results = searcher.search(query)
        return [dict(i) for i in results]


def get_random_video_suggestion(count=20):
    db = TinyDB(Constants.DATABASE_FILE_PATH)
    return random.choices(db.all(), k=count)


def process_video(video_entity):
    db = TinyDB(Constants.DATABASE_FILE_PATH)
    Video = Query()
    db.update({'hls_processing': True
               }, Video.id == video_entity['id'])

    def monitor(ffmpeg, duration, time_, time_left, process):
        # if glob.glob(os.path.join(Constants.HLS_OUTPUT_PATH, f'{video_entity["id"]}_???p.m3u8')):
        #     db.update({'hls_processing': False
        #                }, Video.id == video_entity['id'])
        per = round(time_ / duration * 100)
        print(
            f"[[HLS CONVERSION - {video_entity['id']}]]\n Transcoding...({per}%) {datetime.timedelta(seconds=int(time_left))} left [{'#' * per}{'-' * (100 - per)}]"
        )

    _repr = None
    if video_entity['width'] and video_entity['height'] and video_entity['v_bitrate'] and video_entity['a_bitrate']:
        # _repr = Representation(Size(video_entity['width'], video_entity['height']),
        #                        Bitrate(video_entity['v_bitrate'], video_entity['a_bitrate']))
        _repr = Representation(Size(640, 360), Bitrate(276 * 1024, 128 * 1024))
    else:
        _repr = Representation(Size(640, 360), Bitrate(276 * 1024, 128 * 1024))

    video = ffmpeg_streaming.input(video_entity['abs_path'])
    hls = video.hls(Formats.h264())
    hls.representations(_repr)
    hls.output(os.path.join(Constants.HLS_OUTPUT_PATH, f'{video_entity["id"]}.m3u8'), monitor=monitor)

    db.update({'hls_already_processed': True,
               'hls_process_location': f'{video_entity["id"]}.m3u8'
               }, Video.id == video_entity['id'])


@app.route('/api/suggestion/<search_string>')
def search(search_string):
    result = search_from_text_search_engine(search_string)
    return jsonify({
        'count': len(result),
        'results': result})


@app.route('/api/content')
def get_content():
    return jsonify(get_random_video_suggestion(5))


@app.after_request
def add_header(response):
    response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/video_content/<string:file_name>')
def serve_video(file_name):
    if file_name.endswith('.ts'):
        return send_from_directory(directory=Constants.HLS_OUTPUT_PATH,
                                   path=file_name)

    video_id = re.findall(r'([^_.]+)', file_name)[0]
    print(file_name, video_id)
    db = TinyDB(Constants.DATABASE_FILE_PATH)
    video_entity = db.search(Query().id == video_id)[0]

    if video_entity['hls_already_processed']:
        print(Fore.GREEN + f'{video_entity["id"]} has been already processed, serving...' + Fore.GREEN)
        return send_from_directory(directory=Constants.HLS_OUTPUT_PATH,
                                   path=file_name)
    else:
        if not os.path.exists(Constants.HLS_OUTPUT_PATH):
            os.mkdir(Constants.HLS_OUTPUT_PATH)
        # starting a thread to process
        if video_entity['hls_processing']:
            if glob.glob(os.path.join(Constants.HLS_OUTPUT_PATH, f'{video_id}_???p.m3u8')):
                return send_from_directory(directory=Constants.HLS_OUTPUT_PATH,
                                           path=file_name)
            while not glob.glob(os.path.join(Constants.HLS_OUTPUT_PATH, f'{video_id}_???p.m3u8')):
                time.sleep(0)
            return send_from_directory(directory=Constants.HLS_OUTPUT_PATH,
                                       path=file_name)

        Process(target=process_video, args=(video_entity,)).start()

        while not glob.glob(os.path.join(Constants.HLS_OUTPUT_PATH, f'{video_id}_???p.m3u8')):
            time.sleep(0)
        return send_from_directory(directory=Constants.HLS_OUTPUT_PATH,
                                   path=file_name)


@app.route('/video/<video_id>')
def serve_video_page(video_id):
    db = TinyDB(Constants.DATABASE_FILE_PATH)
    video_entity = db.search(Query().id == video_id)[0]
    return render_template('video.html', video_entity=video_entity, data=get_random_video_suggestion(10))


@app.route('/api/get_more/<int:count>')
def get_more_video(count):
    return jsonify(get_random_video_suggestion(count))


@app.route('/thumbnail/<file_id>')
def thumbnail(file_id):
    return send_from_directory(Constants.THUMBNAIL_FOLDER_PATH, path=f'{file_id}/{file_id}_{random.randint(1, 3)}.png',
                               as_attachment=True)


@app.route('/')
def index():
    return render_template('index.html', data=get_random_video_suggestion(5))


if __name__ == '__main__':
    print(Fore.GREEN + 'Preparing the indexes' + Fore.RESET)
    # Utils.parse_config_file()
    app.run(host='0.0.0.0', threaded=True)
