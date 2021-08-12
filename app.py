from flask import Flask, jsonify
from whoosh.index import open_dir
from whoosh.qparser import QueryParser

from constants import Constants

app = Flask(__name__)
ix = open_dir(Constants.WHOOSH_INDEX_PATH)
writer = ix.writer()


def search_from_text_search_engine(token):
    with ix.searcher() as searcher:
        query = QueryParser("video_name", ix.schema).parse(token)
        results = searcher.search(query)
        return [dict(i) for i in results]


@app.route('/api/suggestion/<search_string>')
def search(search_string):
    return jsonify({search_string: search_from_text_search_engine(search_string)})


if __name__ == '__main__':
    app.run(threaded=True)
