import os
import random
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
    hls.output(os.path.join(Constants.HLS_OUTPUT_PATH, f'{video_entity["id"]}.m3u8'))


@app.route('/api/suggestion/<search_string>')
def search(search_string):
    result = search_from_text_search_engine(search_string)
    return jsonify({
        'count': len(result),
        search_string: result})


@app.after_request
def add_header(response):
    response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/video_content/<string:file_name>')
def serve_video(file_name):
    print(file_name)
    return send_from_directory(directory=Constants.HLS_OUTPUT_PATH,
                               path=file_name)


@app.route('/video/<video_id>')
def serve_video_page(video_id):
    db = TinyDB(Constants.DATABASE_FILE_PATH)
    video_entity = db.search(Query().id == video_id)[0]
    if video_entity['hls_already_processed']:
        pass
    else:
        if not os.path.exists(Constants.HLS_OUTPUT_PATH):
            os.mkdir(Constants.HLS_OUTPUT_PATH)
        # starting a thread to process
        Process(target=process_video, args=(video_entity,)).start()
        while not os.path.exists(os.path.join(Constants.HLS_OUTPUT_PATH, f'{video_entity["id"]}.m3u8')):
            time.sleep(0)
        # actual_file_name = None
        # with open(os.path.join(Constants.HLS_OUTPUT_PATH, f'{video_entity["id"]}.m3u8')) as f:
        #     actual_file_name = [i for i in f.readlines() if not i.startswith('#')][0]
        # print(actual_file_name)
        # while not os.path.exists(os.path.join(Constants.HLS_OUTPUT_PATH, actual_file_name)):
        #     time.sleep(0)
    return render_template('video.html',
                           file_name=f'{video_entity["id"]}.m3u8', video_entity=video_entity)


@app.route('/api/get_more/<int:count>')
def get_more_video(count):
    return jsonify(get_random_video_suggestion(count))


@app.route('/thumbnail/<file_id>')
def thumbnail(file_id):
    return send_from_directory(Constants.THUMBNAIL_FOLDER_PATH, path=f'{file_id}/{file_id}_{random.randint(1, 3)}.png',
                               as_attachment=True)


@app.route('/')
def index():
    return render_template('index.html', data=get_random_video_suggestion(20))


if __name__ == '__main__':
    print(Fore.GREEN + 'Preparing the indexes' + Fore.RESET)
    # Utils.parse_config_file()
    app.run(host='0.0.0.0', threaded=True)
