import os
import sys
  
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import os
import shutil
import argparse
import utils

src_dir = os.path.join(os.path.dirname(__file__), "conf/")

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--config")
args = parser.parse_args()
if args.config:
    dir = args.config
else:
    dir = "conf/"

# if not os.path.exists(dir):
#   os.mkdir(dir)
shutil.copytree(src_dir, dir, dirs_exist_ok=True)

secret = """
#Generated by system,do not edit
secret: {}
""".format(
    utils.random_string(100)
)

with open(os.path.join(dir, "config.yaml"), "a") as config_file:
    config_file.write(secret)
