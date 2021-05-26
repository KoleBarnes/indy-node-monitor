import argparse
import asyncio
# import base58
# import base64
import json
import os
import sys
# import datetime
import urllib.request
# from typing import Tuple
from collections import namedtuple
# import nacl.signing

import indy_vdr
from indy_vdr.ledger import (
    build_get_validator_info_request,
    build_get_txn_request,
    # Request,
)
from indy_vdr.pool import open_pool
from plugin_collection import PluginCollection
# import time
from DidKey import DidKey

from flask import Flask, request, jsonify, make_response

verbose = False


def log(*args):
    if verbose:
        print(*args, "\n", file=sys.stderr)


async def fetch_status(genesis_path: str, nodes: str = None, ident: DidKey = None, network_name: str = None):
   
    # Start Of Engine
    attempt = 3
    while attempt:
        try:
            log("Connecting to Pool ...")
            pool = await open_pool(transactions_path=genesis_path)
        except:
            log("Pool Timed Out! Trying again...")
            if not attempt:
                print("Unable to get pool Response! 3 attempts where made. Exiting...")
                exit()
            attempt -= 1
            continue
        else:
            log("Connected to Pool ...")
        break

    result = []
    verifiers = {}

    if ident:
        request = build_get_validator_info_request(ident.did)
        ident.sign_request(request)
    else:
        request = build_get_txn_request(None, 1, 1)

    from_nodes = []
    if nodes:
        from_nodes = nodes.split(",")
    response = await pool.submit_action(request, node_aliases = from_nodes)
    try:
        # Introduced in https://github.com/hyperledger/indy-vdr/commit/ce0e7c42491904e0d563f104eddc2386a52282f7
        verifiers = await pool.get_verifiers()
    except AttributeError:
        pass
    # End Of Engine

    result = await monitor_plugins.apply_all_plugins_on_value(result, network_name, response, verifiers)
    print(json.dumps(result, indent=2))
    return result

def get_script_dir():
    return os.path.dirname(os.path.realpath(__file__))

def download_genesis_file(url: str, target_local_path: str):
    log("Fetching genesis file ...")
    target_local_path = f"{get_script_dir()}/genesis.txn"
    urllib.request.urlretrieve(url, target_local_path)

def load_network_list():
    with open(f"{get_script_dir()}/networks.json") as json_file:
        networks = json.load(json_file)
    return networks

def list_networks():
    networks = load_network_list()
    return networks.keys()

def init_network_args(network: str = None, genesis_url: str = None, genesis_path: str = None):
    genesis_path = args.genesis_path

    if network:
        log("Loading known network list ...")
        networks = load_network_list()
        if network in networks:
            log("Connecting to '{0}' ...".format(networks[network]["name"]))
            genesis_url = networks[network]["genesisUrl"]
            network_name = networks[network]["name"]

    if genesis_url:
        download_genesis_file(genesis_url, genesis_path)
        if not network_name:
            network_name = genesis_url
            log(f"Setting network name  = {network_name} ...")
    if not os.path.exists(genesis_path):
        print("Set the GENESIS_URL or GENESIS_PATH environment variable or argument.\n", file=sys.stderr)
        parser.print_help()
        exit()

    Network_Info = namedtuple('Network_Info', ['network_name', 'genesis_url', 'genesis_path']) 
    network_info = Network_Info(network_name, genesis_url, genesis_path)

    return network_info

# ==========================================================
# REST API
# ----------------------------------------------------------
app = Flask(__name__)

@app.route("/helloworld", methods=['GET'])
async def HelloWorld():
    to_echo = request.args.get("echo", "")
    response = "{}".format(to_echo)
    to_test = request.args.get("test", "")
    response2 = "{}".format(to_test)
    return {'response': response, 'response2': response2}
    # return make_response(jsonify({'success': True}), 404)
    # return {"data": "Hello World"}

@app.route("/networks", methods=['GET'])
async def networks():
    data = load_network_list()
    return data

@app.route("/networks/<network>", methods=['GET'])
async def network(network):
    network_info = init_network_args(network=network)

    if "seed" in request.headers:
        ident = DidKey(request.headers.get("seed"))
        log("DID:", ident.did, " Verkey:", ident.verkey)
    else:
        ident = None

    result = await fetch_status(genesis_path=network_info.genesis_path, ident=ident, network_name=network_info.network_name)
    return jsonify(result)

@app.route('/networks/<network>/<node>', methods=['GET'])
async def node(network, node):
    network_info = init_network_args(network=network)

    if "seed" in request.headers:
        ident = DidKey(request.headers.get("seed"))
        log("DID:", ident.did, " Verkey:", ident.verkey)
    else:
        ident = None

    # pre_result_check = {"genesis_path": network_info.genesis_path, "genesis_url": network_info.genesis_url, "nodes": node, "ident": ident, "network_name": network_info.network_name, "network": network}
    # print(pre_result_check)

    result = await fetch_status(network_info.genesis_path, node, ident, network_info.network_name)
    return jsonify(result)

# ==========================================================

if __name__ == "__main__":
    monitor_plugins = PluginCollection('plugins')

    parser = argparse.ArgumentParser(description="Fetch the status of all the indy-nodes within a given pool.")
    parser.add_argument("--net", choices=list_networks(), help="Connect to a known network using an ID.")
    parser.add_argument("--list-nets", action="store_true", help="List known networks.")
    parser.add_argument("--genesis-url", default=os.environ.get('GENESIS_URL') , help="The url to the genesis file describing the ledger pool.  Can be specified using the 'GENESIS_URL' environment variable.")
    parser.add_argument("--genesis-path", default=os.getenv("GENESIS_PATH") or f"{get_script_dir()}/genesis.txn" , help="The path to the genesis file describing the ledger pool.  Can be specified using the 'GENESIS_PATH' environment variable.")
    parser.add_argument("-s", "--seed", default=os.environ.get('SEED') , help="The privileged DID seed to use for the ledger requests.  Can be specified using the 'SEED' environment variable. If DID seed is not given the request will run anonymously.")
    parser.add_argument("--nodes", help="The comma delimited list of the nodes from which to collect the status.  The default is all of the nodes in the pool.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging.")
    parser.add_argument("--web", action="store_true", help="Start API server.")

    monitor_plugins.get_parse_args(parser)
    args, unknown = parser.parse_known_args()

    verbose = args.verbose

    monitor_plugins.load_all_parse_args(args)

    if args.list_nets:
        print(json.dumps(load_network_list(), indent=2))
        exit()

    did_seed = None if not args.seed else args.seed

    log("indy-vdr version:", indy_vdr.version())
    if did_seed:
        ident = DidKey(did_seed)
        log("DID:", ident.did, " Verkey:", ident.verkey)
    else:
        ident = None

    if args.web:
        log("Starting web server ...")
        app.run(host="0.0.0.0", port=8080, debug=True)
    else:
        network_info = init_network_args(network=args.net)
        log("Starting from the command line ...")
        asyncio.get_event_loop().run_until_complete(fetch_status(network_info.genesis_path, args.nodes, ident, network_info.network_name))