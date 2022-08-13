from flask import render_template, request, make_response, Response, Blueprint
import errno
import base64
import json
import utils
import mimetypes
import os


class dav:
    def __init__(self,parent):
        self.api=Blueprint('api', __name__, url_prefix='/dav')
        self.auth = parent.auth
        self.acl = parent.acl
        self.fs = parent.vfs
        self.__name__ = ""
        self.api.add_url_rule(
            "/<path:path>",
            methods=["GET", "PUT", "PROPFIND", "DELETE", "MKCOL"],
            view_func=self,
        )
        self.api.add_url_rule(
            "/",
            methods=["GET", "PUT", "PROPFIND", "DELETE", "MKCOL"],
            view_func=self,
        )
    def __call__(self, path=""):
        path = os.path.normpath("/" + path)
        if ".." in path:
            return "", 400
        res=utils.chk_auth(self.auth)
        print(res)
        if res:
            return res
        utils.fs_context.username=utils.get_http_passwd()[0]
        if self.acl:
            res = self.acl.check(path, utils.fs_context.username)
            if not res:
                return "", 403
        if request.method == "PROPFIND":  # 返回目录下的文件
            ret = self.fs.list(path)
            if type(ret) == int:
                if ret == -1:
                    return "", 404
            if request.args.get("json_mode"):
                return {"files": ret}
            return render_template("dav_respone", **{"files": ret}), 207

        if request.method == "OPTIONS":  # 确定webdav支持
            resp = make_response()
            resp.headers["DAV"] = "1,2"
            return resp
        if request.method == "GET":
            resp,length = self.fs.read(path)
            if path == "":
                return ""
            if resp == -1:
                return "", 404
            resp=Response(resp, mimetype=mimetypes.guess_type(path)[0])
            resp.content_length=length
            return resp
        if request.method == "PUT":
            print(1)
            ret = self.fs.write(path, request.stream)
            print(ret)
            if type(ret) == int:
                return "", 404
            return ""
        if request.method == "DELETE":
            self.fs.delete(path)
            return ""
        if request.method == "MKCOL":
            self.fs.mkdir(path)
            return ""
