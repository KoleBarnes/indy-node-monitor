import argparse
import asyncio
import base58
import base64
import json
import os
import sys
import datetime
import urllib.request
from typing import Tuple

import nacl.signing

import indy_vdr
from indy_vdr.ledger import (
    build_get_validator_info_request,
    build_get_txn_request,
    Request,
)
from indy_vdr.pool import open_pool
from plugin_collection import PluginCollection
import time

verbose = False


def log(*args):
    if verbose:
        print(*args, "\n", file=sys.stderr)

class DidKey:
    def __init__(self, seed):
        seed = seed_as_bytes(seed)
        self.sk = nacl.signing.SigningKey(seed)
        self.vk = bytes(self.sk.verify_key)
        self.did = base58.b58encode(self.vk[:16]).decode("ascii")
        self.verkey = base58.b58encode(self.vk).decode("ascii")

    def sign_request(self, req: Request):
        signed = self.sk.sign(req.signature_input)
        req.set_signature(signed.signature)


def seed_as_bytes(seed):
    if not seed or isinstance(seed, bytes):
        return seed
    if len(seed) != 32:
        return base64.b64decode(seed)
    return seed.encode("ascii")


async def fetch_status(genesis_path: str, nodes: str = None, ident: DidKey = None, network_name: str = None):

    # result = [{'name': 'Medici', 'client-address': 'tcp://35.225.188.183:9702', 'node-address': 'tcp://34.66.79.136:9701', 'status': {'ok': False, 'timestamp': '1612731833', 'errors': 1}, 'errors': ['timeout']},{'name': 'mitrecorp', 'client-address': 'tcp://52.207.178.56:9779', 'node-address': 'tcp://54.144.209.223:9797', 'status': {'ok': False, 'timestamp': '1612731833', 'errors': 1}, 'errors': ['timeout']}]
    result = [{'name': 'OgNode', 'client-address': 'tcp://62.150.68.20:9702', 'node-address': 'tcp://62.150.68.20:9701', 'status': {'ok': False, 'uptime': '1 day, 23:46:13', 'timestamp': 1614231353, 'software': {'indy-node': '1.12.4', 'sovrin': '1.1.89'}, 'warnings': 1, 'errors': 2}, 'warnings': [{'unreachable_nodes': {'count': 2, 'nodes': 'Trinsic, mitrecorp'}}], 'response': {'result': {'type': '119', 'data': {'response-version': '0.0.1', 'Pool_info': {'Unreachable_nodes': [['Trinsic', None], ['mitrecorp', None]], 'Reachable_nodes': [['Axuall', None], ['CERTIZEN_SSI_VALIDATOR', None], ['DHIWAY', None], ['Dynenode1', None], ['FoundationBuilder', 1], ['MainIncubator', 0], ['Node1289', None], ['OgNode', None], ['cpqd',None], ['danube', 3], ['fetch-ai', None], ['ifis', None], ['makolab01', 5], ['ovvalidator', None], ['riddleandcode', None], ['validatedid', 4], ['xsvalidatorec2irl', 2]], 'Read_only': False, 'Blacklisted_nodes': [], 'Suspicious_nodes': '', 'Reachable_nodes_count': 17, 'f_value': 6, 'Unreachable_nodes_count': 2, 'Quorums': "{'observer_data': Quorum(7), 'f': 6, 'same_consistency_proof': Quorum(7), 'n': 19, 'view_change': Quorum(13), 'strong': Quorum(13), 'view_change_done': Quorum(13), 'timestamp': Quorum(7), 'view_change_ack': Quorum(12), 'election': Quorum(13), 'bls_signatures': Quorum(13), 'ledger_status_last_3PC': Quorum(7), 'consistency_proof': Quorum(7), 'weak': Quorum(7), 'checkpoint': Quorum(12), 'backup_instance_faulty': Quorum(7), 'commit': Quorum(13), 'reply': Quorum(7), 'prepare': Quorum(12), 'ledger_status': Quorum(12), 'propagate': Quorum(7)}", 'Total_nodes_count': 19}, 'timestamp': 1614231353, 'Protocol': {}, 'Extractions': {'journalctl_exceptions': [''], 'stops_stat': None, 'indy-node_status': ['● indy-node.service - Indy Node', '   Loaded: loaded (/etc/systemd/system/indy-node.service; enabled; vendor preset: enabled)', '   Active: active (running) since ث2021-02-23 05:49:33 UTC; 1 day 23h ago', ' Main PID: 21513 (python3)', '   CGroup: /system.slice/indy-node.service', '           ├─12095 /bin/sh -c systemctl status indy-node', '           ├─12096 systemctl status indy-node', '└─21513 python3 -O /usr/local/bin/start_indy_node OgNode 192.168.225.45 9701 192.168.225.45 9702', ''], 'node-control status': ['● indy-node-control.service - Service for upgrade of existing Indy Node and other operations', '   Loaded: loaded (/etc/systemd/system/indy-node-control.service; disabled; vendor preset: enabled)', '   Active: active (running) since ث 2021-02-23 05:49:32 UTC; 1 day 23h ago', ' Main PID: 21509 (python3)', '   CGroup: /system.slice/indy-node-control.service', '           └─21509 python3 -O /usr/local/bin/start_node_control_tool --hold-ext sovtoken sovtokenfees sovrin', ''], 'upgrade_log': ['2020-06-02 17:34:56.096360\tscheduled\t2020-06-02 15:40:00.555000-06:00\t1.1.81\t1591119295119693000268\tsovrin\n', '2020-06-02 21:40:00.572321\tstarted\t2020-06-02 15:40:00.555000-06:00\t1.1.81\t1591119295119693000268\tsovrin\n', '2020-06-02 21:41:46.462436\tsucceeded\t2020-06-02 15:40:00.555000-06:00\t1.1.81\t1591119295119693000268\tsovrin\n', '2020-08-19 01:27:09.239597\tscheduled\t2020-08-19 16:40:00+00:00\t1.1.89\t1597840189675754810316\tsovrin\n', '2020-08-19 07:26:37.089473\tcancelled\t2020-08-19 16:40:00+00:00\t1.1.89\t1597840189675754810316\tsovrin\n', '2020-08-19 07:26:37.089956\tscheduled\t2020-08-19 07:40:00+00:00\t1.1.89\t1597861757781016189\tsovrin\n', '2020-08-19 07:27:37.307754\tcancelled\t2020-08-19 07:40:00+00:00\t1.1.89\t1597861757781016189\tsovrin\n', '2020-08-19 07:27:37.308225\tscheduled\t2020-08-19 07:40:00+00:00\t1.1.89\t1597861819054803637\tsovrin\n', '2020-08-19 07:40:00.009671\tstarted\t2020-08-19 07:40:00+00:00\t1.1.89\t1597861819054803637\tsovrin\n', '2020-08-19 07:41:58.154941\tsucceeded\t2020-08-19 07:40:00+00:00\t1.1.89\t1597861819054803637\tsovrin\n']}, 'Update_time': 'Thursday, February 25, 2021 5:35:53 AM +0000', 'Software': {'indy-node': '1.12.4', 'OS_version': 'Linux-4.15.0-129-generic-x86_64-with-Ubuntu-16.04-xenial', 'sovrin': '1.1.89', 'Installed_packages': ['python-rocksdb 0.6.9', 'portalocker 0.5.7', 'sovtokenfees 1.0.9', 'intervaltree 2.1.0', 'jsonpickle 0.9.6', 'ioflo 1.5.4', 'rlp 0.5.1', 'indy-crypto 0.4.5-23', 'sortedcontainers 1.5.7', 'indy-node 1.12.4', 'indy-plenum 1.12.4', 'timeout-decorator 0.4.0', 'distro 1.3.0', 'sha3 0.2.1', 'psutil 5.4.3', 'python-dateutil 2.6.1', 'Pygments 2.2.0', 'semver 2.7.9', 'pyzmq 18.1.0', 'sovtoken 1.0.9', 'orderedset 2.0', 'libnacl 1.6.1', 'sovrin1.1.89', 'Pympler 0.5', 'six 1.11.0', 'packaging 19.0', 'base58 1.0.0', 'setuptools 38.5.2'], 'Indy_packages': ['hi  indy-node                                  1.12.4                                          amd64        Indy node', 'hiindy-plenum                                1.12.4                                          amd64        Plenum Byzantine Fault Tolerant Protocol', 'hi  libindy-crypto                             0.4.5     amd64        This is the shared crypto libirary for Hyperledger Indy components.', 'hi  python3-indy-crypto                        0.4.5                                           amd64        This is the official wrapper for Hyperledger Indy Crypto library (https://www.hyperledger.org/projects).', '']}, 'Memory_profiler': [], 'Node_info': {'Node_protocol': 'tcp', 'Name': 'OgNode', 'Replicas_status': {'OgNode:4': {'Last_ordered_3PC': [94, 67], 'Stashed_txns': {'Stashed_checkpoints': 0, 'Stashed_PrePrepare': 0}, 'Primary': 'validatedid:4', 'Watermarks': '53:353'}, 'OgNode:3': {'Last_ordered_3PC': [94, 67], 'Stashed_txns': {'Stashed_checkpoints': 0, 'Stashed_PrePrepare': 0}, 'Primary': 'danube:3', 'Watermarks': '53:353'}, 'OgNode:2': {'Last_ordered_3PC': [94, 67], 'Stashed_txns': {'Stashed_checkpoints': 0, 'Stashed_PrePrepare': 0}, 'Primary': 'xsvalidatorec2irl:2', 'Watermarks': '53:353'}, 'OgNode:5': {'Last_ordered_3PC': [94, 67], 'Stashed_txns': {'Stashed_checkpoints': 0, 'Stashed_PrePrepare': 0}, 'Primary': 'makolab01:5', 'Watermarks': '53:353'}, 'OgNode:0': {'Last_ordered_3PC': [94, 601077], 'Stashed_txns': {'Stashed_checkpoints': 0, 'Stashed_PrePrepare': 0}, 'Primary': 'MainIncubator:0', 'Watermarks': '601000:601300'}, 'OgNode:1': {'Last_ordered_3PC': [94, 67], 'Stashed_txns': {'Stashed_checkpoints': 0, 'Stashed_PrePrepare': 0}, 'Primary': 'FoundationBuilder:1', 'Watermarks': '53:353'}}, 'BLS_key': '3bcg83S97wRdGB3Tb8hwgMUzjKuncEWpYUN3LMjKBtzT8AaaV7Z4ciQowvgSfetrUpMy3zxaos1czPnYGcRbntYGcBHsnxEm1iiRizKiCkus4FQChKDiXZdxXtj3HX8H37AkSBcBjPfHL9avbk4AYQGUZUz9qjKwzCw6RRGffphC1y1', 'Client_protocol': 'tcp', 'View_change_status': {'VCDone_queue': {}, 'View_No': 94, 'VC_in_progress': False, 'Last_view_change_started_at': '1970-01-01 00:00:00', 'IC_queue': {'95': {'Voters': {'OgNode': {'reason': 18}}}}, 'Last_complete_view_no': 94}, 'Requests_timeouts': {'Propagates_phase_req_timeouts': 0, 'Ordering_phase_req_timeouts': 0}, 'Uncommitted_ledger_txns': {'0': {'Count': 0}, '1': {'Count': 0}, '2': {'Count': 0}, '3': {'Count': 0}, '1001': {'Count': 0}}, 'Client_port': 9702, 'Committed_state_root_hashes': {'0': "b'4UTk1Eh3Fruxnhx6aCnf71ALDfhT9NBEErg3fQxofyQX'", '1': "b'AYKkVRWmUWBaoon2aRGFezyqo2y81oqvFQppe9DnHR44'", '2': "b'DdTCr9qBxz9TXmWdFUy3nueMuVrCzc1yygj38dpHhhCc'", '1001': "b'2VaN5t2PeF94PM1CdZv9yxjdh2gdDp5sEQ6N6cZUCuAT'"}, 'Uncommitted_ledger_root_hashes': {}, 'Client_ip': '192.168.225.45', 'Freshness_status': {'0': {'Has_write_consensus': True, 'Last_updated_time': '2021-02-25 16:40:51+00:00'}, '1': {'Has_write_consensus': True, 'Last_updated_time': '2021-02-25 16:38:50+00:00'}, '2': {'Has_write_consensus': True, 'Last_updated_time': '2021-02-25 16:39:45+00:00'}, '1001': {'Has_write_consensus': True, 'Last_updated_time': '2021-02-25 16:40:28+00:00'}}, 'Mode': 'participating', 'Node_port': 9701, 'Committed_ledger_root_hashes': {'0': "b'5MWuDhRCnUnERUUc5wZG2hcw8aY26M9aVSo6LCeVFpq6'", '1': "b'4tzkA3dzHf1LkNhYoa6JSJ1LAqcQvMcM2psh2Y8784Ca'", '2': "b'9U5JfdyzVnGP7G4qiJiuoRkscKDCYs5n5BzZXs9TqWse'", '3': "b'WMRHpvEa4r9nyJ5wn2tpbG1CbrGVsenrSwtVNecqsFE'", '1001': "b'HPfQorwaVtD7vmYUAS6yNkqjBtLZeDE4p59R9sEMnFoo'"}, 'did': '5aNBs6DToRDNuXamiswdvPhvoGxoLbdEL5XTLdZrv6Xf', 'Count_of_replicas': 6, 'Node_ip': '192.168.225.45', 'Catchup_status': {'Last_txn_3PC_keys': {'0': {'riddleandcode':[None, None], 'validatedid': [None, None], 'Axuall': [None, None], 'Dynenode1': [None, None], 'MainIncubator': [None, None], 'ifis': [None, None], 'FoundationBuilder': [None, None], 'ovvalidator': [None, None], 'makolab01': [None, None],'danube': [None, None], 'xsvalidatorec2irl': [None, None], 'CERTIZEN_SSI_VALIDATOR': [None, None]}, '1': {}, '2': {}, '3': {'riddleandcode': [None, None], 'validatedid': [None, None], 'Axuall': [None, None], 'Dynenode1': [None, None], 'MainIncubator': [None, None], 'ifis': [None, None], 'FoundationBuilder': [None, None], 'ovvalidator': [None, None], 'makolab01': [None, None], 'danube': [None, None], 'xsvalidatorec2irl': [None, None], 'CERTIZEN_SSI_VALIDATOR': [None, None]}, '1001': {}}, 'Ledger_statuses': {'0': 'synced', '1': 'synced', '2': 'synced', '3': 'synced', '1001': 'synced'}, 'Number_txns_in_catchup': {'0': 0, '1': 0, '2': 0, '3': 0, '1001': 0}, 'Received_LedgerStatus': '', 'Waiting_consistency_proof_msgs': {'0': None, '1': None, '2': None, '3': None, '1001': None}}, 'Uncommitted_state_root_hashes': {'0': "b'4UTk1Eh3Fruxnhx6aCnf71ALDfhT9NBEErg3fQxofyQX'", '1': "b'AYKkVRWmUWBaoon2aRGFezyqo2y81oqvFQppe9DnHR44'", '2': "b'DdTCr9qBxz9TXmWdFUy3nueMuVrCzc1yygj38dpHhhCc'", '1001': "b'2VaN5t2PeF94PM1CdZv9yxjdh2gdDp5sEQ6N6cZUCuAT'"}, 'Metrics': {'master throughput ratio': 1.0, 'transaction-count': {'1001': 221, 'audit': 613520, 'pool': 82, 'ledger': 2982, 'config': 360}, 'master throughput': 0.0, 'Delta': 0.1, 'avg backup throughput': 0.0, 'Omega': 20, 'ordered request durations': {'0': 5.0316031822, '1': 5.1008369606, '2': 4.828201212, '3': 5.3703530114, '4': 4.051814659, '5': 5.2125136331}, 'instances started': {'0': 3487053.595852803, '1': 3487053.598048169, '2': 3487053.60017548, '3': 3487053.603018892, '4': 3487053.605083599, '5': 3487053.607243982}, 'total requests': 1, 'uptime': 171973, 'max master request latencies': 0, 'throughput': {'0': 0.0, '1': 0.0, '2': 0.0, '3': 0.0, '4': 0.0, '5': 0.0}, 'Lambda': 240, 'ordered request counts': {'0': 14, '1': 14, '2': 14, '3': 14, '4': 14, '5': 14}, 'average-per-second': {'write-transactions': 5.8149e-06, 'read-transactions': 0.4165062626}, 'client avg request latencies': {'0': None, '1': None, '2': None, '3': None, '4': None, '5': None}}, 'verkey': '6Ng7zvRuWdYE5gNcDyrDfsFoTTTBsc9rxNTg3WmBLtMqNwKcBcQgX7r'}, 'Hardware': {'HDD_used_by_node': '169 MBs'}}, 'reqId': 1614271364810932600, 'identifier': 'Bhhsxc585EVgbbmosZr65J'}, 'op': 'REPLY'}, 'errors': ["OgNode and Trinsic can't reach each other.", "OgNode and mitrecorp can't reach each other."]}, {'name': 'Trinsic', 'client-address': 'tcp://52.250.41.249:9702', 'node-address': 'tcp://40.91.94.117:9701', 'status': {'ok': False, 'uptime': '189 days, 22:56:42', 'timestamp': 1614271366, 'software': {'indy-node': '1.12.4', 'sovrin': '1.1.89'}, 'warnings': 1, 'errors': 1}, 'warnings': [{'unreachable_nodes': {'count': 1, 'nodes': 'OgNode'}}], 'response': {'op': 'REPLY', 'result': {'data': {'Node_info': {'Catchup_status': {'Received_LedgerStatus': '', 'Number_txns_in_catchup': {'0': 0, '1': 0, '2': 0, '3': 3, '1001': 0}, 'Waiting_consistency_proof_msgs': {'0': None, '1': None, '2': None, '3': None, '1001': None}, 'Last_txn_3PC_keys': {'0': {'Node1289': [None, None], 'Condatis01': [None, None], 'CERTIZEN_SSI_VALIDATOR': [None, None], 'fetch-ai': [None, None], 'Axuall': [None, None], 'ovvalidator': [None, None], 'MainIncubator': [None, None], 'Medici': [None, None], 'FoundationBuilder': [None, None], 'validatedid': [None, None], 'DHIWAY': [None, None], 'Dynenode1': [None, None], 'mitrecorp': [None, None], 'xsvalidatorec2irl': [None, None]}, '1': {}, '2': {}, '3': {}, '1001': {}}, 'Ledger_statuses': {'0': 'synced', '1': 'synced', '2': 'synced', '3': 'synced', '1001': 'synced'}}, 'Committed_ledger_root_hashes': {'0': "b'5MWuDhRCnUnERUUc5wZG2hcw8aY26M9aVSo6LCeVFpq6'", '1': "b'4tzkA3dzHf1LkNhYoa6JSJ1LAqcQvMcM2psh2Y8784Ca'", '2': "b'9U5JfdyzVnGP7G4qiJiuoRkscKDCYs5n5BzZXs9TqWse'", '3': "b'WMRHpvEa4r9nyJ5wn2tpbG1CbrGVsenrSwtVNecqsFE'", '1001': "b'HPfQorwaVtD7vmYUAS6yNkqjBtLZeDE4p59R9sEMnFoo'"}, 'Node_port': 9701, 'Mode': 'participating', 'Count_of_replicas': 7, 'Uncommitted_ledger_txns': {'0': {'Count': 0}, '1': {'Count': 0}, '2': {'Count': 0}, '3': {'Count': 0}, '1001': {'Count': 0}}, 'Committed_state_root_hashes': {'0': "b'4UTk1Eh3Fruxnhx6aCnf71ALDfhT9NBEErg3fQxofyQX'", '1': "b'AYKkVRWmUWBaoon2aRGFezyqo2y81oqvFQppe9DnHR44'", '2': "b'DdTCr9qBxz9TXmWdFUy3nueMuVrCzc1yygj38dpHhhCc'", '1001': "b'2VaN5t2PeF94PM1CdZv9yxjdh2gdDp5sEQ6N6cZUCuAT'"}, 'Name': 'Trinsic', 'BLS_key': '2e9YDi7pouhRDxbGki6dFhpcgUJGzetj2jUQkJdoQ8k1sw3S81ZeHepjhEK5pmLqwkuZFmxYsYis7HJDZvZH7XzVnATh1qcj6Rx3h73vYWpU5zAYGdSA1kUGdenPHf79kmWVQzHyhbVUFt23KhPh6pxk6Y8wrUX2eg6hfg93amyvfEi', 'Client_ip': '10.0.1.4', 'did': 't2LeEE7c4BkdwpzqT1z3sBssrzSrFVKhe13v3Mtuirw', 'verkey': '3c2mvLuz3u2BeQozrnvaM3qPtC7TXxFNy36YgGUhp2JRS1GbVrATgxh', 'Uncommitted_state_root_hashes': {'0': "b'4UTk1Eh3Fruxnhx6aCnf71ALDfhT9NBEErg3fQxofyQX'", '1': "b'AYKkVRWmUWBaoon2aRGFezyqo2y81oqvFQppe9DnHR44'", '2': "b'DdTCr9qBxz9TXmWdFUy3nueMuVrCzc1yygj38dpHhhCc'", '1001': "b'2VaN5t2PeF94PM1CdZv9yxjdh2gdDp5sEQ6N6cZUCuAT'"}, 'Requests_timeouts': {'Ordering_phase_req_timeouts': 158, 'Propagates_phase_req_timeouts': 0}, 'Metrics': {'instances started': {'0': 7936044.81646005, '1': 22695599.313279342, '2': 22695599.317959603, '3': 22695599.323812556, '4': 22695599.32811252, '5': 22695599.332910582, '6': 22695599.33813424}, 'total requests': 539, 'max master request latencies': 0, 'throughput': {'0': 0.0, '1': 0.0, '2': 0.0, '3': 0.0, '4': 0.0, '5': 0.0, '6': 0.0}, 'Omega': 20, 'client avg request latencies': {'0': 0.3181242115, '1': None, '2': None, '3': None, '4': None, '5': None, '6': None}, 'average-per-second': {'write-transactions': 3.28414e-05, 'read-transactions': 0.5972462232}, 'master throughput ratio': None, 'Delta': 0.1, 'ordered request counts': {'0': 66, '1': 0, '2': 0, '3': 0, '4': 0, '5': 0, '6': 0}, 'transaction-count': {'1001': 221, 'ledger': 2982, 'audit': 613520, 'pool': 82, 'config': 360}, 'Lambda': 240, 'ordered request durations': {'0': 23.2746219039, '1': 0, '2': 0, '3': 0, '4': 0, '5': 0, '6': 0}, 'avg backup throughput': 0.0, 'uptime': 16412202, 'master throughput': 0.0}, 'Node_ip': '10.0.2.5', 'Client_port': 9702, 'View_change_status': {'Last_view_change_started_at': '2021-02-06 13:38:44', 'VC_in_progress': False, 'Last_complete_view_no': 94, 'VCDone_queue': {}, 'IC_queue': {'95': {'Voters': {'makolab01': {'reason': 43}}}}, 'View_No': 94}, 'Node_protocol': 'tcp', 'Replicas_status': {'Trinsic:6': {'Watermarks': '0:300', 'Primary': 'ovvalidator:6', 'Last_ordered_3PC': [94, 19], 'Stashed_txns': {'Stashed_PrePrepare': 0, 'Stashed_checkpoints': 0}}, 'Trinsic:0': {'Watermarks': '601000:601300', 'Primary': 'MainIncubator:0', 'Last_ordered_3PC': [94, 601077], 'Stashed_txns': {'Stashed_PrePrepare': 0, 'Stashed_checkpoints': 0}}, 'Trinsic:5': {'Watermarks': '0:300', 'Primary': 'makolab01:5', 'Last_ordered_3PC': [94, 67], 'Stashed_txns': {'Stashed_PrePrepare': 0, 'Stashed_checkpoints': 0}}, 'Trinsic:4': {'Watermarks': '0:300', 'Primary': 'validatedid:4', 'Last_ordered_3PC': [94, 67], 'Stashed_txns': {'Stashed_PrePrepare': 0, 'Stashed_checkpoints': 0}}, 'Trinsic:1': {'Watermarks': '0:300', 'Primary': 'FoundationBuilder:1', 'Last_ordered_3PC': [94, 67], 'Stashed_txns': {'Stashed_PrePrepare': 0, 'Stashed_checkpoints': 0}}, 'Trinsic:3': {'Watermarks': '0:300', 'Primary': 'danube:3', 'Last_ordered_3PC': [94, 67], 'Stashed_txns': {'Stashed_PrePrepare': 0, 'Stashed_checkpoints': 0}}, 'Trinsic:2': {'Watermarks': '0:300', 'Primary': 'xsvalidatorec2irl:2', 'Last_ordered_3PC': [94, 67], 'Stashed_txns': {'Stashed_PrePrepare': 0, 'Stashed_checkpoints': 0}}}, 'Client_protocol': 'tcp', 'Uncommitted_ledger_root_hashes': {}, 'Freshness_status': {'0': {'Has_write_consensus': True, 'Last_updated_time': '2021-02-25 16:40:51+00:00'}, '1': {'Has_write_consensus': True, 'Last_updated_time': '2021-02-25 16:38:50+00:00'}, '2': {'Has_write_consensus': True, 'Last_updated_time': '2021-02-25 16:39:45+00:00'}, '1001': {'Has_write_consensus': True, 'Last_updated_time': '2021-02-25 16:40:28+00:00'}}}, 'Protocol': {}, 'Hardware': {'HDD_used_by_node': '253 MBs'}, 'Update_time': 'Thursday, February 25, 2021 4:42:46 PM +0000', 'Memory_profiler': [], 'Software':{'sovrin': '1.1.89', 'indy-node': '1.12.4', 'OS_version': 'Linux-4.15.0-1082-azure-x86_64-with-Ubuntu-16.04-xenial', 'Installed_packages': ['six 1.11.0', 'sovtokenfees 1.0.9', 'Pympler 0.5', 'packaging 19.0', 'portalocker 0.5.7', 'ioflo 1.5.4', 'distro 1.3.0', 'setuptools 38.5.2', 'sovrin 1.1.89', 'python-dateutil 2.6.1', 'rlp 0.5.1', 'python-rocksdb 0.6.9', 'sha3 0.2.1', 'orderedset 2.0', 'pyzmq 18.1.0', 'base58 1.0.0', 'sortedcontainers 1.5.7', 'indy-plenum 1.12.4', 'jsonpickle 0.9.6', 'indy-crypto 0.4.5-23', 'Pygments 2.2.0', 'timeout-decorator 0.4.0', 'psutil 5.4.3', 'libnacl 1.6.1', 'intervaltree 2.1.0', 'semver 2.7.9', 'sovtoken 1.0.9', 'indy-node 1.12.4'], 'Indy_packages': ['hi  indy-node                 1.12.4                                        amd64        Indy node', 'hi  indy-plenum                         1.12.4                                        amd64        Plenum Byzantine Fault Tolerant Protocol', 'hi  libindy-crypto                      0.4.5                                         amd64        This is the shared crypto libirary for Hyperledger Indy components.', 'hi  python3-indy-crypto                 0.4.5            amd64        This is the official wrapper for Hyperledger Indy Crypto library (https://www.hyperledger.org/projects).', '']}, 'Pool_info': {'Quorums': "{'view_change_done': Quorum(13), 'propagate': Quorum(7), 'reply': Quorum(7), 'observer_data': Quorum(7), 'f': 6, 'bls_signatures': Quorum(13), 'ledger_status': Quorum(12), 'view_change_ack': Quorum(12), 'timestamp': Quorum(7), 'consistency_proof': Quorum(7), 'view_change': Quorum(13), 'backup_instance_faulty':Quorum(7), 'ledger_status_last_3PC': Quorum(7), 'prepare': Quorum(12), 'election': Quorum(13), 'checkpoint': Quorum(12), 'same_consistency_proof': Quorum(7), 'commit': Quorum(13), 'n': 19, 'weak': Quorum(7), 'strong': Quorum(13)}", 'Reachable_nodes_count': 18, 'Read_only': False, 'Blacklisted_nodes': [], 'Unreachable_nodes': [['OgNode', None]], 'Total_nodes_count': 19, 'Suspicious_nodes': '', 'f_value': 6, 'Unreachable_nodes_count': 1, 'Reachable_nodes': [['Axuall', None], ['CERTIZEN_SSI_VALIDATOR', None], ['DHIWAY', None], ['Dynenode1', None], ['FoundationBuilder', 1], ['MainIncubator', 0], ['Node1289', None], ['Trinsic', None], ['cpqd', None], ['danube', 3], ['fetch-ai', None], ['ifis', None], ['makolab01', 5], ['mitrecorp', None], ['ovvalidator', 6], ['riddleandcode', None], ['validatedid', 4], ['xsvalidatorec2irl', 2]]}, 'Extractions': {'journalctl_exceptions': [''], 'node-control status': ['● indy-node-control.service - Service for upgrade of existing Indy Node and other operations', '   Loaded: loaded (/etc/systemd/system/indy-node-control.service; disabled; vendor preset: enabled)', '   Active: active (running) since Wed 2020-08-19 17:45:56 UTC; 6 months 7 days ago', ' Main PID: 12894 (python3)', '    Tasks: 1', '   Memory: 35.0M', '      CPU: 1.891s', '   CGroup: /system.slice/indy-node-control.service', '           └─12894 python3 -O /usr/local/bin/start_node_control_tool --hold-ext sovtoken sovtokenfees sovrin', ''], 'indy-node_status': ['● indy-node.service - Indy Node', '   Loaded: loaded (/etc/systemd/system/indy-node.service; enabled; vendor preset: enabled)', '   Active: active (running) since Wed 2020-08-19 17:45:56 UTC; 6 months 7 days ago', ' Main PID: 12886 (python3)', '    Tasks: 8', '   Memory: 1.4G', '      CPU: 1month 3w 5d 6h 36min 54.821s', '   CGroup: /system.slice/indy-node.service', '           ├─12886 python3 -O /usr/local/bin/start_indy_nodeTrinsic 10.0.2.5 9701 10.0.1.4 9702', '           ├─28814 /bin/sh -c systemctl status indy-node', '           └─28815 systemctl status indy-node', ''], 'upgrade_log': ['2020-06-02 17:34:56.038257\tscheduled\t2020-06-02 16:55:00.555000-06:00\t1.1.81\t1591119295119693000268\tsovrin\n', '2020-06-02 22:55:00.559304\tstarted\t2020-06-02 16:55:00.555000-06:00\t1.1.81\t1591119295119693000268\tsovrin\n', '2020-06-02 22:56:02.971497\tsucceeded\t2020-06-02 16:55:00.555000-06:00\t1.1.81\t1591119295119693000268\tsovrin\n', '2020-08-19 12:30:05.789430\tscheduled\t2020-08-19 17:45:00+00:00\t1.1.89\t1597840189675754810316\tsovrin\n', '2020-08-19 17:45:00.008232\tstarted\t2020-08-19 17:45:00+00:00\t1.1.89\t1597840189675754810316\tsovrin\n', '2020-08-19 17:46:09.970909\tsucceeded\t2020-08-19 17:45:00+00:00\t1.1.89\t1597840189675754810316\tsovrin\n'], 'stops_stat': None}, 'timestamp': 1614271366, 'response-version': '0.0.1'}, 'reqId': 1614271364810932600,'identifier': 'Bhhsxc585EVgbbmosZr65J', 'type': '119'}}, 'errors': ["Trinsic and OgNode can't reach each other."]}, {'name': 'mitrecorp', 'client-address': 'tcp://52.207.178.56:9779', 'node-address': 'tcp://54.144.209.223:9797', 'status': {'ok': False, 'uptime': '121 days, 3:02:20', 'timestamp': 1614271408, 'software': {'indy-node': '1.12.4', 'sovrin': '1.1.89'}, 'warnings': 1, 'errors': 1}, 'warnings': [{'unreachable_nodes': {'count': 1, 'nodes': 'OgNode'}}], 'response': {'result': {'data': {'Extractions': {'indy-node_status': ['● indy-node.service - Indy Node', '   Loaded: loaded (/etc/systemd/system/indy-node.service; enabled; vendor preset: enabled)', '   Active: active (running) since Tue 2020-10-2713:41:01 UTC; 3 months 29 days ago', ' Main PID: 1213 (python3)', '    Tasks: 8', '   Memory: 1.1G', '      CPU: 3w 3d 15h 19min 52.937s', '   CGroup: /system.slice/indy-node.service', '           ├─ 1213 python3 -O /usr/local/bin/start_indy_node mitrecorp 10.90.3.8 9797 10.90.3.4 9779', '           ├─26840 /bin/sh -c systemctl status indy-node', '           └─26841 systemctl status indy-node', ''], 'node-control status': ['● indy-node-control.service - Service for upgrade of existing Indy Node and other operations', '   Loaded: loaded (/etc/systemd/system/indy-node-control.service; disabled; vendor preset: enabled)', '   Active: active (running) since Tue 2020-10-27 13:41:01 UTC; 3 months 29 days ago', ' Main PID: 1231 (python3)', '    Tasks: 1', '   Memory: 43.4M', '      CPU: 2.374s', '   CGroup: /system.slice/indy-node-control.service', '           └─1231 python3 -O /usr/local/bin/start_node_control_tool --hold-ext sovtoken sovtokenfees sovrin', ''], 'upgrade_log': ['2020-01-06 17:05:20.151130\tsucceeded\t2020-01-06 10:05:00.555000-07:00\t1.1.67\t1578330257766790000\tsovrin\n', '2020-02-01 21:38:35.911471\tscheduled\t2020-02-03 11:00:00.555000-07:00\t1.1.71\t1580593114943534000221\tsovrin\n', '2020-02-03 18:00:00.567382\tstarted\t2020-02-03 11:00:00.555000-07:00\t1.1.71\t1580593114943534000221\tsovrin\n', '2020-02-03 18:00:30.219517\tsucceeded\t2020-02-03 11:00:00.555000-07:00\t1.1.71\t1580593114943534000221\tsovrin\n', '2020-06-02 17:34:55.986153\tscheduled\t2020-06-02 16:00:00.555000-06:00\t1.1.81\t1591119295119693000268\tsovrin\n', '2020-06-02 22:00:00.559530\tstarted\t2020-06-02 16:00:00.555000-06:00\t1.1.81\t1591119295119693000268\tsovrin\n', '2020-06-02 22:00:31.664514\tsucceeded\t2020-06-02 16:00:00.555000-06:00\t1.1.81\t1591119295119693000268\tsovrin\n', '2020-08-19 12:30:05.743761\tscheduled\t2020-08-19 17:00:00+00:00\t1.1.89\t1597840189675754810316\tsovrin\n', '2020-08-19 17:00:00.001577\tstarted\t2020-08-19 17:00:00+00:00\t1.1.89\t1597840189675754810316\tsovrin\n', '2020-08-19 17:00:36.235489\tsucceeded\t2020-08-19 17:00:00+00:00\t1.1.89\t1597840189675754810316\tsovrin\n'], 'journalctl_exceptions': [''], 'stops_stat': None}, 'Software': {'sovrin': '1.1.89', 'Installed_packages': ['rlp 0.5.1', 'pyzmq 18.1.0', 'Pympler 0.5', 'indy-node 1.12.4', 'timeout-decorator 0.4.0', 'semver 2.7.9', 'indy-crypto 0.4.5-23', 'Pygments 2.2.0', 'setuptools 38.5.2', 'distro 1.3.0', 'sovrin 1.1.89', 'packaging 19.0', 'psutil 5.4.3', 'indy-plenum 1.12.4', 'sovtoken 1.0.9', 'ptyprocess 0.6.0', 'intervaltree 2.1.0', 'python-rocksdb 0.6.9', 'portalocker 0.5.7', 'sortedcontainers 1.5.7', 'pexpect 4.7.0', 'libnacl 1.6.1', 'sovtokenfees 1.0.9', 'python-dateutil 2.6.1', 'base58 1.0.0', 'six 1.11.0', 'jsonpickle 0.9.6', 'ioflo 1.5.4', 'orderedset 2.0', 'sha3 0.2.1'], 'OS_version': 'Linux-4.4.0-1117-aws-x86_64-with-Ubuntu-16.04-xenial', 'indy-node': '1.12.4', 'Indy_packages': ['hi  indy-node                        1.12.4                                     amd64        Indy node', 'hi  indy-plenum                      1.12.4       amd64        Plenum Byzantine Fault Tolerant Protocol', 'hi  libindy-crypto                   0.4.5                                      amd64        This is the shared crypto libirary for Hyperledger Indy components.', 'hi  python3-indy-crypto              0.4.5                                      amd64        This is the official wrapper for Hyperledger Indy Crypto library (https://www.hyperledger.org/projects).', '']}, 'timestamp': 1614271408, 'Node_info': {'Node_port': 9797, 'Count_of_replicas': 7, 'Replicas_status': {'mitrecorp:6': {'Primary': 'ovvalidator:6', 'Last_ordered_3PC': [94, 19], 'Watermarks': '0:300', 'Stashed_txns': {'Stashed_checkpoints': 0, 'Stashed_PrePrepare': 0}}, 'mitrecorp:3': {'Primary': 'danube:3', 'Last_ordered_3PC': [94, 67], 'Watermarks': '0:300', 'Stashed_txns': {'Stashed_checkpoints': 0, 'Stashed_PrePrepare': 0}}, 'mitrecorp:0': {'Primary': 'MainIncubator:0', 'Last_ordered_3PC': [94, 601077], 'Watermarks': '601000:601300', 'Stashed_txns': {'Stashed_checkpoints': 0, 'Stashed_PrePrepare': 0}}, 'mitrecorp:2': {'Primary': 'xsvalidatorec2irl:2', 'Last_ordered_3PC': [94, 67], 'Watermarks': '0:300', 'Stashed_txns': {'Stashed_checkpoints': 0, 'Stashed_PrePrepare': 0}}, 'mitrecorp:4': {'Primary': 'validatedid:4', 'Last_ordered_3PC': [94, 67], 'Watermarks': '0:300', 'Stashed_txns': {'Stashed_checkpoints': 0, 'Stashed_PrePrepare': 0}}, 'mitrecorp:1': {'Primary': 'FoundationBuilder:1', 'Last_ordered_3PC': [94, 67], 'Watermarks': '0:300', 'Stashed_txns': {'Stashed_checkpoints': 0, 'Stashed_PrePrepare': 0}}, 'mitrecorp:5': {'Primary': 'makolab01:5', 'Last_ordered_3PC': [94, 67], 'Watermarks': '0:300', 'Stashed_txns': {'Stashed_checkpoints': 0, 'Stashed_PrePrepare': 0}}}, 'Metrics': {'Omega': 20, 'average-per-second': {'write-transactions': 6.68875e-05, 'read-transactions': 0.5454064345}, 'instances started': {'0': 31.432220678, '1': 8812676.218949012, '2': 8812676.22249073, '3': 8812676.22644188, '4': 8812676.22994523, '5': 8812676.23341994, '6': 8812676.236923315}, 'master throughput': 0.0, 'total requests': 700, 'throughput': {'0': 0.0, '1': 0.0, '2': 0.0, '3': 0.0, '4': 0.0, '5': 0.0, '6': 0.0}, 'Lambda': 240, 'ordered request durations': {'0': 22.0684519187, '1': 0, '2': 0, '3': 0, '4': 0, '5': 0, '6': 0}, 'ordered request counts': {'0': 66, '1': 0, '2': 0, '3': 0, '4': 0, '5': 0, '6': 0}, 'max master requestlatencies': 0, 'uptime': 10465340, 'master throughput ratio': None, 'avg backup throughput': 0.0, 'Delta': 0.1, 'transaction-count': {'ledger': 2982, '1001': 221, 'pool': 82, 'audit': 613520, 'config': 360}, 'client avg request latencies': {'0': 0.3013703378, '1': None, '2': None, '3': None, '4': None, '5': None, '6': None}}, 'Name': 'mitrecorp', 'Committed_state_root_hashes': {'0': "b'4UTk1Eh3Fruxnhx6aCnf71ALDfhT9NBEErg3fQxofyQX'", '1': "b'AYKkVRWmUWBaoon2aRGFezyqo2y81oqvFQppe9DnHR44'", '2': "b'DdTCr9qBxz9TXmWdFUy3nueMuVrCzc1yygj38dpHhhCc'", '1001': "b'2VaN5t2PeF94PM1CdZv9yxjdh2gdDp5sEQ6N6cZUCuAT'"}, 'Uncommitted_ledger_root_hashes': {}, 'Node_ip': '10.90.3.8', 'Client_port': 9779, 'Uncommitted_ledger_txns': {'0': {'Count': 0}, '1': {'Count': 0}, '2': {'Count': 0}, '3': {'Count': 0}, '1001': {'Count': 0}}, 'Client_protocol': 'tcp', 'Requests_timeouts': {'Propagates_phase_req_timeouts': 0, 'Ordering_phase_req_timeouts': 0}, 'BLS_key': '3TuFUfzVWq2mB8qWeXVkLeXTewmmqciytJ9niKBS135e76zqDW1fFCWCFS37u37xtGTXC9f3mGEhyhL1HWDPLgeAatV4tZbkFAPKdVnwA2thtafoMybvqhDTCBKkLqzC3XmGPsnwZ9eyqYiaC9bXjqn6Dgure5DEaW3Wq4aJKQtVYTF', 'Client_ip': '10.90.3.4', 'Mode': 'participating', 'Uncommitted_state_root_hashes': {'0': "b'4UTk1Eh3Fruxnhx6aCnf71ALDfhT9NBEErg3fQxofyQX'", '1': "b'AYKkVRWmUWBaoon2aRGFezyqo2y81oqvFQppe9DnHR44'", '2': "b'DdTCr9qBxz9TXmWdFUy3nueMuVrCzc1yygj38dpHhhCc'", '1001': "b'2VaN5t2PeF94PM1CdZv9yxjdh2gdDp5sEQ6N6cZUCuAT'"}, 'View_change_status': {'VCDone_queue': {}, 'Last_view_change_started_at': '2021-02-06 13:38:44', 'View_No': 94, 'Last_complete_view_no': 94, 'IC_queue': {'95': {'Voters': {'makolab01': {'reason': 43}}}}, 'VC_in_progress': False}, 'verkey': '5Vn6ZQQMFsDUhHJ2bCP5SwPAgYdZuRuArXz1Jy2J5ybZKUMJ3GXMft2', 'Node_protocol': 'tcp', 'did': 'DySBxWFQrVWmjzcoepq5me72FZbasik3XyQwLtYNcSoa', 'Committed_ledger_root_hashes': {'0': "b'5MWuDhRCnUnERUUc5wZG2hcw8aY26M9aVSo6LCeVFpq6'", '1': "b'4tzkA3dzHf1LkNhYoa6JSJ1LAqcQvMcM2psh2Y8784Ca'", '2': "b'9U5JfdyzVnGP7G4qiJiuoRkscKDCYs5n5BzZXs9TqWse'", '3': "b'WMRHpvEa4r9nyJ5wn2tpbG1CbrGVsenrSwtVNecqsFE'", '1001': "b'HPfQorwaVtD7vmYUAS6yNkqjBtLZeDE4p59R9sEMnFoo'"}, 'Freshness_status': {'0': {'Has_write_consensus': True, 'Last_updated_time': '2021-02-25 16:40:51+00:00'}, '1': {'Has_write_consensus': True, 'Last_updated_time': '2021-02-25 16:38:50+00:00'}, '2': {'Has_write_consensus': True, 'Last_updated_time': '2021-02-25 16:39:45+00:00'}, '1001': {'Has_write_consensus': True, 'Last_updated_time': '2021-02-25 16:40:28+00:00'}}, 'Catchup_status': {'Waiting_consistency_proof_msgs': {'0': None, '1': None, '2': None, '3': None, '1001': None}, 'Received_LedgerStatus': '', 'Ledger_statuses': {'0': 'synced', '1': 'synced', '2': 'synced', '3': 'synced', '1001': 'synced'}, 'Number_txns_in_catchup': {'0': 0, '1': 0, '2': 0, '3': 3, '1001': 0}, 'Last_txn_3PC_keys': {'0': {'DHIWAY': [None, None], 'CERTIZEN_SSI_VALIDATOR': [None, None], 'riddleandcode': [None, None], 'ovvalidator': [None, None], 'xsvalidatorec2irl': [None, None], 'makolab01': [None, None], 'FoundationBuilder': [None, None], 'danube': [None, None], 'Node1289': [None, None], 'validatedid': [None, None], 'Axuall': [None, None], 'Medici': [None, None]}, '1': {}, '2': {}, '3': {}, '1001': {}}}}, 'Update_time': 'Thursday, February 25, 2021 4:43:28 PM +0000', 'Memory_profiler': [], 'response-version': '0.0.1', 'Pool_info': {'Reachable_nodes_count': 18, 'Reachable_nodes': [['Axuall', None], ['CERTIZEN_SSI_VALIDATOR', None], ['DHIWAY', None], ['Dynenode1', None], ['FoundationBuilder', 1], ['MainIncubator', 0], ['Node1289', None], ['Trinsic', None], ['cpqd', None], ['danube', 3], ['fetch-ai', None], ['ifis', None], ['makolab01', 5], ['mitrecorp', None], ['ovvalidator', 6], ['riddleandcode', None], ['validatedid', 4], ['xsvalidatorec2irl', 2]], 'Quorums': "{'bls_signatures': Quorum(13), 'ledger_status_last_3PC': Quorum(7), 'weak': Quorum(7), 'backup_instance_faulty': Quorum(7), 'f': 6, 'reply': Quorum(7), 'n': 19, 'ledger_status': Quorum(12), 'commit': Quorum(13), 'election': Quorum(13), 'strong': Quorum(13), 'observer_data': Quorum(7), 'view_change_ack': Quorum(12), 'prepare': Quorum(12), 'timestamp': Quorum(7), 'view_change': Quorum(13), 'view_change_done': Quorum(13), 'same_consistency_proof': Quorum(7), 'checkpoint': Quorum(12), 'propagate': Quorum(7), 'consistency_proof': Quorum(7)}", 'Unreachable_nodes_count': 1, 'f_value': 6, 'Unreachable_nodes': [['OgNode', None]], 'Read_only': False, 'Suspicious_nodes': '', 'Blacklisted_nodes': [], 'Total_nodes_count': 19}, 'Hardware': {'HDD_used_by_node': '275 MBs'}, 'Protocol': {}}, 'type': '119', 'reqId': 1614271364810932600, 'identifier': 'Bhhsxc585EVgbbmosZr65J'}, 'op': 'REPLY'}, 'errors': ["mitrecorp and OgNode can't reach each other."]}]

    monitor_plugins.apply_all_plugins_on_value(result, network_name)
    exit()

    # Start of engine
    while True:
        try:
            pool = await open_pool(transactions_path=genesis_path)
        except:
            if verbose: print("Pool Timed Out! Trying again...")
            continue
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

    # end of engine feeds pass to anlz result, response, varifiers

    # Ansys plugin
    primary = ""
    packages = {}
    for node, val in response.items():
        jsval = []
        status = {}
        errors = []
        warnings = []
        info = []
        entry = {"name": node}
        try:
            await get_node_addresses(entry, verifiers)
            jsval = json.loads(val)
            if not primary:
                primary = await get_primary_name(jsval, node)
            errors, warnings = await detect_issues(jsval, node, primary, ident)
            info = await get_info(jsval, ident)
            packages[node] = await get_package_info(jsval)
        except json.JSONDecodeError:
            errors = [val]  # likely "timeout"

        # Status Summary
        entry["status"] = await get_status_summary(jsval, errors)
        # Info
        if len(info) > 0:
            entry["status"]["info"] = len(info)
            entry["info"] = info
        # Errors / Warnings
        if len(errors) > 0:
            entry["status"]["errors"] = len(errors)
            entry["errors"] = errors
        if len(warnings) > 0:
            entry["status"]["warnings"] = len(warnings)
            entry["warnings"] = warnings
        # Full Response
        if jsval:
            entry["response"] = jsval # put into status plugin minus response 

        result.append(entry)

        # Ansys plugin end

    # Package Mismatches
    if packages:
        await merge_package_mismatch_info(result, packages)

    # Connection Issues
    await detect_connection_issues(result)

    monitor_plugins.apply_all_plugins_on_value(result, network_name)
    
# ansys plug-in
async def get_node_addresses(entry: any, verifiers: any) -> any:
    if verifiers:
        node_name = entry["name"]
        if "client_addr" in verifiers[node_name]:
            entry["client-address"] = verifiers[node_name]["client_addr"]
        if "node_addr" in verifiers[node_name]:
            entry["node-address"] = verifiers[node_name]["node_addr"]


async def detect_connection_issues(result: any) -> any:
    for node in result:
        connection_errors = []
        node_name = node["name"]
        if "warnings" in node:
            for warning in node["warnings"]:
                if "unreachable_nodes" in warning :
                    for item in warning["unreachable_nodes"]["nodes"].split(', '):
                        # This is the name of the unreachable node.  Now we need to determine whether that node can't see the current one.
                        # If the nodes can't see each other, upgrade to an error condition.
                        unreachable_node_name = item
                        unreachable_node_query_result = [t for t in result if t["name"] == unreachable_node_name]
                        if unreachable_node_query_result:
                            unreachable_node = unreachable_node_query_result[0]
                            if "warnings" in unreachable_node:
                                for unreachable_node_warning in unreachable_node["warnings"]:
                                    if "unreachable_nodes" in unreachable_node_warning :
                                        for unreachable_node_item in unreachable_node_warning["unreachable_nodes"]["nodes"].split(', '):
                                            if unreachable_node_item == node_name:
                                                connection_errors.append(node_name + " and " + unreachable_node_name + " can't reach each other.")

        # Merge errors and update status
        if connection_errors:
            if "errors" in node:
                for item in connection_errors:
                    node["errors"].append(item)
            else:
                node["errors"] = connection_errors
            node["status"]["errors"] = len(node["errors"])
            node["status"]["ok"] = (len(node["errors"]) <= 0)

# Ansys Plug-in
async def get_primary_name(jsval: any, node: str) -> str:
    primary = ""
    if "REPLY" in jsval["op"]:
        if "Node_info" in jsval["result"]["data"]:
            primary = jsval["result"]["data"]["Node_info"]["Replicas_status"][node+":0"]["Primary"]
    return primary

# Ansys plug-in
async def get_status_summary(jsval: any, errors: list) -> any:
    status = {}
    status["ok"] = (len(errors) <= 0)
    if jsval and ("REPLY" in jsval["op"]):
        if "Node_info" in jsval["result"]["data"]:
            status["uptime"] = str(datetime.timedelta(seconds = jsval["result"]["data"]["Node_info"]["Metrics"]["uptime"]))
        if "timestamp" in jsval["result"]["data"]:
            status["timestamp"] = jsval["result"]["data"]["timestamp"]
        else:
            status["timestamp"] = datetime.datetime.now().strftime('%s')
        if "Software" in jsval["result"]["data"]:
            status["software"] = {}
            status["software"]["indy-node"] = jsval["result"]["data"]["Software"]["indy-node"]
            status["software"]["sovrin"] = jsval["result"]["data"]["Software"]["sovrin"]

    return status

# Ansys plug-in
async def get_package_info(jsval: any) -> any:
    packages = {}
    if jsval and ("REPLY" in jsval["op"]):
        if "Software" in jsval["result"]["data"]:
            for installed_package in jsval["result"]["data"]["Software"]["Installed_packages"]:
                package, version = installed_package.split()
                packages[package] = version

    return packages

async def check_package_versions(packages: any) -> any:
    warnings = {}
    for node, package_list in packages.items():
        mismatches = []
        for package, version in package_list.items():
            total = 0
            same = 0
            other_version = ""
            for comp_node, comp_package_list in packages.items():
                if package in comp_package_list:
                    total +=1
                    comp_version = comp_package_list[package]
                    if comp_version == version:
                        same +=1
                    else:
                        other_version = comp_version
            if (same/total) < .5:
                mismatches.append("Package mismatch: '{0}' has '{1}' {2}, while most other nodes have '{1}' {3}".format(node, package, version, other_version))
        if mismatches:
            warnings[node] = mismatches
    return warnings

async def merge_package_mismatch_info(result: any, packages: any):
    package_warnings = await check_package_versions(packages)
    if package_warnings:
        for node_name in package_warnings:
            entry_to_update = [t for t in result if t["name"] == node_name][0]
            if "warnings" in entry_to_update:
                for item in package_warnings[node_name]:
                    entry_to_update["warnings"].append(item)
            else:
                entry_to_update["warnings"] = package_warnings[node_name]
            entry_to_update["status"]["warnings"] = len(entry_to_update["warnings"])

# ansys plug-in
async def get_info(jsval: any, ident: DidKey = None) -> any:
    info = []
    if "REPLY" in jsval["op"]:
        if ident:
            # Pending Upgrade
            if jsval["result"]["data"]["Extractions"]["upgrade_log"]:
                current_upgrade_status = jsval["result"]["data"]["Extractions"]["upgrade_log"][-1]
                if "succeeded" not in current_upgrade_status:
                    info.append("Pending Upgrade: {0}".format(current_upgrade_status.replace('\t', '  ').replace('\n', '')))

    return info

# core to engin? Ansys PLug-in?
async def detect_issues(jsval: any, node: str, primary: str, ident: DidKey = None) -> Tuple[any, any]:
    errors = []
    warnings = []
    ledger_sync_status={}
    if "REPLY" in jsval["op"]:
        if ident:
            # Ledger Write Consensus Issues
            if not jsval["result"]["data"]["Node_info"]["Freshness_status"]["0"]["Has_write_consensus"]:
                errors.append("Config Ledger Has_write_consensus: {0}".format(jsval["result"]["data"]["Node_info"]["Freshness_status"]["0"]["Has_write_consensus"]))
            if not jsval["result"]["data"]["Node_info"]["Freshness_status"]["1"]["Has_write_consensus"]:
                errors.append("Main Ledger Has_write_consensus: {0}".format(jsval["result"]["data"]["Node_info"]["Freshness_status"]["1"]["Has_write_consensus"]))
            if not jsval["result"]["data"]["Node_info"]["Freshness_status"]["2"]["Has_write_consensus"]:
                errors.append("Pool Ledger Has_write_consensus: {0}".format(jsval["result"]["data"]["Node_info"]["Freshness_status"]["2"]["Has_write_consensus"]))
            if "1001" in  jsval["result"]["data"]["Node_info"]["Freshness_status"]:
                if not jsval["result"]["data"]["Node_info"]["Freshness_status"]["1001"]["Has_write_consensus"]:
                    errors.append("Token Ledger Has_write_consensus: {0}".format(jsval["result"]["data"]["Node_info"]["Freshness_status"]["1001"]["Has_write_consensus"]))

            # Ledger Status
            for ledger, status in jsval["result"]["data"]["Node_info"]["Catchup_status"]["Ledger_statuses"].items():
                if status != "synced":
                    ledger_sync_status[ledger] = status
            if ledger_sync_status:
                ledger_status = {}
                ledger_status["ledger_status"] = ledger_sync_status
                ledger_status["ledger_status"]["transaction-count"] = jsval["result"]["data"]["Node_info"]["Metrics"]["transaction-count"]
                warnings.append(ledger_status)

            # Mode
            if jsval["result"]["data"]["Node_info"]["Mode"] != "participating":
                warnings.append("Mode: {0}".format(jsval["result"]["data"]["Node_info"]["Mode"]))

            # Primary Node Mismatch
            if jsval["result"]["data"]["Node_info"]["Replicas_status"][node+":0"]["Primary"] != primary:
                warnings.append("Primary Mismatch! This Nodes Primary: {0} (Expected: {1})".format(jsval["result"]["data"]["Node_info"]["Replicas_status"][node+":0"]["Primary"], primary))

            # Unreachable Nodes
            if jsval["result"]["data"]["Pool_info"]["Unreachable_nodes_count"] > 0:
                unreachable_node_list = []
                unreachable_nodes = {"unreachable_nodes":{}}
                unreachable_nodes["unreachable_nodes"]["count"] = jsval["result"]["data"]["Pool_info"]["Unreachable_nodes_count"]
                for unreachable_node in jsval["result"]["data"]["Pool_info"]["Unreachable_nodes"]:
                    unreachable_node_list.append(unreachable_node[0])
                unreachable_nodes["unreachable_nodes"]["nodes"] = ', '.join(unreachable_node_list)
                warnings.append(unreachable_nodes)

            # Denylisted Nodes
            if len(jsval["result"]["data"]["Pool_info"]["Blacklisted_nodes"]) > 0:
                warnings.append("Denylisted Nodes: {1}".format(jsval["result"]["data"]["Pool_info"]["Blacklisted_nodes"]))
    else:
        if "reason" in jsval:
            errors.append(jsval["reason"])
        else:
            errors.append("unknown error")

    return errors, warnings


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

if __name__ == "__main__":
    monitor_plugins = PluginCollection('plugins')
    monitor_plugins.sort()

    parser = argparse.ArgumentParser(description="Fetch the status of all the indy-nodes within a given pool.")
    parser.add_argument("--net", choices=list_networks(), help="Connect to a known network using an ID.")
    parser.add_argument("--list-nets", action="store_true", help="List known networks.")
    parser.add_argument("--genesis-url", default=os.environ.get('GENESIS_URL') , help="The url to the genesis file describing the ledger pool.  Can be specified using the 'GENESIS_URL' environment variable.")
    parser.add_argument("--genesis-path", default=os.getenv("GENESIS_PATH") or f"{get_script_dir()}/genesis.txn" , help="The path to the genesis file describing the ledger pool.  Can be specified using the 'GENESIS_PATH' environment variable.")
    parser.add_argument("-s", "--seed", default=os.environ.get('SEED') , help="The privileged DID seed to use for the ledger requests.  Can be specified using the 'SEED' environment variable.")
    parser.add_argument("-a", "--anonymous", action="store_true", help="Perform requests anonymously, without requiring privileged DID seed.")
    parser.add_argument("--nodes", help="The comma delimited list of the nodes from which to collect the status.  The default is all of the nodes in the pool.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging.")
    # Get parse args from the plug-ins
    monitor_plugins.get_parse_args(parser)
    args, unknown = parser.parse_known_args()

    verbose = args.verbose

    monitor_plugins.load_all_parse_args(args)

    if verbose: monitor_plugins.plugin_list()

    if args.list_nets:
        print(json.dumps(load_network_list(), indent=2))
        exit()

    if args.net:
        log("Loading known network list ...")
        networks = load_network_list()
        if args.net in networks:
            log("Connecting to '{0}' ...".format(networks[args.net]["name"]))
            args.genesis_url = networks[args.net]["genesisUrl"]
            network_name = networks[args.net]["name"]

    if args.genesis_url:
        download_genesis_file(args.genesis_url, args.genesis_path)
    if not os.path.exists(args.genesis_path):
        print("Set the GENESIS_URL or GENESIS_PATH environment variable or argument.\n", file=sys.stderr)
        parser.print_help()
        exit()

    did_seed = None if args.anonymous else args.seed
    if not did_seed and not args.anonymous:
        print("Set the SEED environment variable or argument, or specify the anonymous flag.\n", file=sys.stderr)
        parser.print_help()
        exit()

    log("indy-vdr version:", indy_vdr.version())
    if did_seed:
        ident = DidKey(did_seed)
        log("DID:", ident.did, " Verkey:", ident.verkey)
    else:
        ident = None

    asyncio.get_event_loop().run_until_complete(fetch_status(args.genesis_path, args.nodes, ident, network_name))