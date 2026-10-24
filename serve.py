#!/usr/bin/env python3
"""ローカル確認用サーバー。ブラウザが古いページや画像を覚えないよう、キャッシュを無効にして docs/ を配信する。"""
import http.server, functools

class NoCache(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

http.server.ThreadingHTTPServer(("", 8765), functools.partial(NoCache, directory="docs")).serve_forever()
