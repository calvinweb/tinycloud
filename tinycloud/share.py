import random
import hashlib
import os
import json
import io
from quart import Blueprint, request, send_file

import utils
import dav

TINYCLOUD = None


class Sharefs:
    def __init__(self, share):
        self.share = share
        self.file = ["add", "list"]

    def list(self, path):
        if path == "":
            res = []
            for i in self.file:
                res.append(
                    {
                        "type": "file",
                        "name": i,
                        "path": "/" + i,
                        "size": 4,
                        "time": 0,
                    }
                )
            return res
        if path in self.file:
            return [
                {
                    "type": "file",
                    "name": path,
                    "path": "/" + path,
                    "size": 4000,
                    "time": 0,
                }
            ]
        raise FileNotFoundError()

    def read(self, path):
        if path == "add":
            res = ""
        elif path == "list":
            res = json.dumps(self.share.shares)
        else:
            raise FileNotFoundError()

        def reader():
            print(res)
            yield res

        res = io.BytesIO(bytes(res + "\n", encoding="UTF8"))
        return res, -1

    def write(self, path, reader):
        data = reader.read().decode().replace("\n", "").split(" ")
        self.share.do_make_share(data[0], utils.fs_context.username, "r")

    def isdir(self, path):
        if path == "":
            return True
        return False


class Share:
    def __init__(self, fs=None, auth=None, secret=None):
        if bool(fs) | bool(auth) | bool(secret):
            self.fs = fs
            self.auth = auth
            self.secret = secret
        elif "TINYCLOUD" in globals():
            self.fs = TINYCLOUD.vfs
            self.auth = TINYCLOUD.auth
            self.secret = TINYCLOUD.secret
            self.fs.mount(Sharefs, ".share", {"share": self})
        else:
            raise TypeError()
        self.shares = {}
        if "TINYCLOUD" in globals():
            TINYCLOUD.on_exit(self.on_exit)
            if os.path.exists(TINYCLOUD.confdir + "/shares.json"):
                with open(TINYCLOUD.confdir + "/shares.json", "r") as dump:
                    self.shares = json.load(dump)
        self.api = Blueprint("share", __name__, url_prefix="/")
        self.dav = dav.Dav(self.fs, blueprint=False)
        self.api.add_url_rule(
            "/api/shares/new", view_func=self.make_share_view, methods=["POST"]
        )
        self.api.add_url_rule(
            "/api/shares/del", view_func=self.del_share_view, methods=["POST"]
        )
        self.api.add_url_rule(
            "/api/shares/dav/<path:path>",
            methods=["GET", "PUT", "PROPFIND", "DELETE", "MKCOL", "OPTIONS"],
            view_func=self.share_dav,
        )
        self.api.add_url_rule(
            "/api/shares/info/<idt>",
            view_func=self.share_info,
        )
        self.api.add_url_rule(
            "/api/shares/",
            view_func=self.all_shares,
        )
        self.api.add_url_rule(
            "/shares/<path:path>",
            view_func=self.view_share,
        )

    def do_make_share(self, path, username=None, mode="r"):
        type = ["file", "dir"][self.fs.isdir(path)]
        data = {"path": path, "username": username, "mode": mode, "type": type}
        idt = hashlib.sha512(
            (json.dumps(data) + str(random.random())).encode()
        ).hexdigest()[:10]
        self.shares[idt] = data
        return idt

    def do_del_share(self, idt):
        del self.shares[idt]

    async def del_share_view(self):
        if not utils.chk_auth(request,self.auth, TINYCLOUD.secret):
            return {"error": 403}, 403
        id = json.loads((await request.data()).decode())["id"]
        try:
            self.do_del_share(id)
            return {"res": "ok"}, 200
        except KeyError:
            return {"res": "err", "error": 404}, 404

    async def make_share_view(self):
        if not utils.chk_auth(self.auth, self.secret):
            return {"error": 403}, 403
        req = json.loads((await request.data()).decode())
        path = req["path"]
        args = {"path": path, "username": utils.get_passwd()[0]}

        if "mode" in req:
            args["mode"] = req["mode"]
        try:
            res = {"res": "ok", "id": self.do_make_share(**args)}
        except FileNotFoundError:
            return {"error": "404"}, 404
        return res

    def share_dav(self, path):
        p = list(filter("".__ne__, path.split("/")))
        info = self.shares[p[0]]
        path = os.path.join(info["path"])
        if info["type"] == "dir":
            path = os.path.join(path, "/".join(p[1:]))
        utils.fs_context.username = info["username"]

        # return self.dav(os.path.join(self.shares[str(p[0])], "/".join(p[1:])))
        if info["mode"] == "r" and request.method in ["PUT", "DELETE", "MKCOL"]:
            return "", 403
        return self.dav(path, url_prefix_override="/api/shares/dav/" + p[0])

    async def share_info(self, idt):
        return self.shares[idt]

    async def view_share(self, path):
        if path.split("/")[0] in self.shares:
            return await send_file("static/share.html")
        return "Not such share", 404

    def on_exit(self):
        with open(TINYCLOUD.confdir + "/shares.json", "w") as dump:
            json.dump(self.shares, dump)

    async def all_shares(self):
        if not utils.chk_auth(request,self.auth, self.secret):
            return {"err": 403}, 403
        return self.shares


PROVIDE = {"api": lambda: Share().api}
