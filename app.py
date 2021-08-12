from colorama import Fore
from flask import Flask, jsonify
from tinydb import TinyDB, Query
from whoosh.index import open_dir
from whoosh.qparser import QueryParser

from constants import Constants
from utils import Utils

app = Flask(__name__)


print(Fore.GREEN + 'Preparing the indexes' + Fore.RESET)
Utils.parse_config_file()


def search_from_text_search_engine(token):
    ix = open_dir(Constants.WHOOSH_INDEX_PATH)
    with ix.searcher() as searcher:
        query = QueryParser("video_name", ix.schema).parse(token)
        results = searcher.search(query)
        return [dict(i) for i in results]


@app.route('/api/suggestion/<search_string>')
def search(search_string):
    result = search_from_text_search_engine(search_string)
    return jsonify({
        'count': len(result),
        search_string: result})


@app.route('/api/<video_id>')
def serve_video(video_id):
    db = TinyDB(Constants.DATABASE_FILE_PATH)
    return jsonify(db.search(Query().id == video_id)[0])


if __name__ == '__main__':
    app.run(threaded=True)
