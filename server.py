import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from queue import Queue
import json

import gamestate
import payloadparser
import util

class GSIServer(HTTPServer):
    def __init__(self, server_address, auth_token):
        super(GSIServer, self).__init__(server_address, RequestHandler)

        self.auth_token = auth_token
        self.gamestate_q = Queue()
        self.parser = payloadparser.PayloadParser()
        
        self.payload_cnt = 0
        self.prev_payload = None

    def start_server(self):
        try:
            thread = Thread(target=self.serve_forever)
            thread.start()
            print("[GSI Server] Starting...")
        except:
            util.report_error("[GSI Server] Couldn't start...")
    
    def authenticate_payload(self, payload):
        if "auth" in payload and "token" in payload["auth"]:
            return payload["auth"]["token"] == self.auth_token
        else:
            return False

class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        time_post = time.perf_counter()
        
        length = int(self.headers["Content-Length"])
        body = self.rfile.read(length).decode("utf-8")
        
        self.server.gamestate_q.put([time_post, body])
        
        if self.server.gamestate_q.qsize() > 4:
            print("qsize:", self.server.gamestate_q.qsize())
        
