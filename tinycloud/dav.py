from flask import render_template, request, make_response, Response, Blueprint
import errno
import base64
import json
import utils
import mimetypes
import os
import traceback

import utils

class Dav:
    def __init__(
        self, fs, acl=None, auth=None, blueprint=True, secret=None, url_prefix="/dav"
    ):
        if blueprint:
            self.api = Blueprint("dav", __name__, url_prefix=url_prefix)
            for route in ["","/","/<path:path>"]:
                self.api.add_url_rule(
                    route,
                    methods=["GET", "PUT", "PROPFIND", "DELETE", "MKCOL", "OPTIONS"],
                    view_func=self,
                )
        self.url_prefix = url_prefix
        self.auth = auth
        self.acl = acl
        self.fs = fs
        self.secret = secret
        self.__name__ = ""

    def __call__(self, path="",url_prefix_override=None):
        path = os.path.normpath("/" + path)
        if ".." in path:
            return "", 400
        if self.auth:
            try:
                res = utils.chk_auth(self.auth, secret=self.secret)
                if not res:
                    return Response(
                        "", 401, {"WWW-Authenticate": 'Basic realm="Tinycloud"'}
                    )
            except KeyError:
                return "", 403
            utils.fs_context.username = utils.get_passwd()[0]
        else:
            if not utils.fs_context.username:
                utils.fs_context.username = None
        if self.acl:
            res = self.acl.check(path, utils.fs_context.username)
            if not res:
                return "", 403
        try:
            if request.method == "PROPFIND":  # 返回目录下的文件
                ret = self.fs.list(path)
                if type(ret) == int:
                    if ret == -1:
                        return "", 404
                if request.args.get("json_mode"):
                    return {"files": ret}
                if self.fs.isdir(path):
                    ret.append({"type": "dir", "path": path, "time":utils.time_as_rfc(0), "name": ""})
                return (
                    render_template(
                        "dav_respone",
                        **{
                            "files": ret,
                            "url_prefix": url_prefix_override or self.url_prefix,
                            "normpath": os.path.normpath,
                            "guess_type": mimetypes.guess_type
                        }
                    ),
                    207,
                )
            if request.method == "OPTIONS":  # 确定webdav支持
                resp = make_response()
                resp.headers["DAV"] = "1,2"
                return resp
            if request.method == "GET":
                resp, length = self.fs.read(path)
                if path == "":
                    return ""
                resp = Response(resp, mimetype=mimetypes.guess_type(path)[0])
                resp.content_length = length
                return resp
            if request.method == "PUT":
                ret = self.fs.write(path, request.stream)
                return ""
            if request.method == "DELETE":
                self.fs.delete(path)
                return ""
            if request.method == "MKCOL":
                self.fs.mkdir(path)
                return ""
        except Exception as e:
            e = type(e)
            if e == PermissionError:
                return "", 403
            if e == FileNotFoundError:
                return "", 404
            traceback.print_exc()
            return str(e), 500
