#!/usr/bin/env python3
# Copyright (c) 2014-2019 The Bitcoin Core developers
# Copyright (c) DeFi Blockchain Developers
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.
"""Test EVM behaviour"""
from test_framework.evm_key_pair import EvmKeyPair
from test_framework.test_framework import DefiTestFramework
from test_framework.util import (
    assert_equal,
    assert_raises_rpc_error,
    int_to_eth_u256,
    hex_to_decimal,
)
from decimal import Decimal
import math


class EVMTest(DefiTestFramework):
    def set_test_params(self):
        self.num_nodes = 2
        self.setup_clean_chain = True
        self.extra_args = [
            [
                "-txordering=2",
                "-dummypos=0",
                "-txnotokens=0",
                "-amkheight=50",
                "-bayfrontheight=51",
                "-dakotaheight=50",
                "-eunosheight=80",
                "-fortcanningheight=82",
                "-fortcanninghillheight=84",
                "-fortcanningroadheight=86",
                "-fortcanningcrunchheight=88",
                "-fortcanningspringheight=90",
                "-fortcanninggreatworldheight=94",
                "-fortcanningepilogueheight=96",
                "-grandcentralheight=101",
                "-nextnetworkupgradeheight=105",
                "-subsidytest=1",
                "-txindex=1",
            ],
            [
                "-txordering=2",
                "-dummypos=0",
                "-txnotokens=0",
                "-amkheight=50",
                "-bayfrontheight=51",
                "-dakotaheight=50",
                "-eunosheight=80",
                "-fortcanningheight=82",
                "-fortcanninghillheight=84",
                "-fortcanningroadheight=86",
                "-fortcanningcrunchheight=88",
                "-fortcanningspringheight=90",
                "-fortcanninggreatworldheight=94",
                "-fortcanningepilogueheight=96",
                "-grandcentralheight=101",
                "-nextnetworkupgradeheight=105",
                "-subsidytest=1",
                "-txindex=1",
            ],
        ]

    def run_test(self):
        # Check ERC55 wallet support
        self.erc55_wallet_support()

        # Test TransferDomain, OP_RETURN and EVM Gov vars
        self.evm_gov_vars()

        # Fund accounts
        self.setup_accounts()

        # Test block ordering by nonce and Eth RBF
        self.nonce_order_and_rbf()

        # Check XVM in coinbase
        self.validate_xvm_coinbase()

        # EVM rollback
        self.evm_rollback()

        # Mempool limit of 64 TXs
        self.mempool_tx_limit()

        # Multiple mempool fee replacement
        self.multiple_eth_rbf()

        # Test that node should not crash without chainId param
        self.test_tx_without_chainid()

        # Test evmtx auto nonce
        self.sendtransaction_auto_nonce()

        # Toggle EVM
        self.toggle_evm_enablement()

    def test_tx_without_chainid(self):
        node = self.nodes[0]

        evmkeypair = EvmKeyPair.from_node(node)
        nonce = node.w3.eth.get_transaction_count(evmkeypair.address)

        node.transferdomain(
            [
                {
                    "src": {
                        "address": node.get_genesis_keys().ownerAuthAddress,
                        "amount": "50@DFI",
                        "domain": 2,
                    },
                    "dst": {
                        "address": evmkeypair.address,
                        "amount": "50@DFI",
                        "domain": 3,
                    },
                }
            ]
        )
        node.generate(1)

        tx = {
            "nonce": nonce,
            "to": "0x0000000000000000000000000000000000000000",
            "value": node.w3.to_wei(0.1, "ether"),
            "gas": 21000,
            "gasPrice": node.w3.to_wei(10, "gwei"),
        }

        signed_tx = node.w3.eth.account.sign_transaction(tx, evmkeypair.privkey)
        node.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        node.generate(1)

    def erc55_wallet_support(self):
        # Addresses and keys
        self.address = self.nodes[0].get_genesis_keys().ownerAuthAddress
        self.eth_address = "0x9b8a4af42140d8a4c153a822f02571a1dd037e89"
        self.eth_address_bech32 = "bcrt1qta8meuczw0mhqupzjl5wplz47xajz0dn0wxxr8"
        self.eth_address_privkey = (
            "af990cc3ba17e776f7f57fcc59942a82846d75833fa17d2ba59ce6858d886e23"
        )
        self.to_address = "0x6c34cbb9219d8caa428835d2073e8ec88ba0a110"
        self.to_address_privkey = (
            "17b8cb134958b3d8422b6c43b0732fcdb8c713b524df2d45de12f0c7e214ba35"
        )

        # Import Bech32 compressed private key for:
        # Bech32: bcrt1qu7xc8kkpwzxzamw5236j2gpvtxmgp2zmfzmc32
        # Eth: 0x1286B92185a5d95eA7747F399e6cB1842851fAC3
        self.nodes[0].importprivkey(
            "cNQ9fkAkHfWCPuyi5huZS6co3vND7tkNoWL7HiR2Jck3Jcb28SYW"
        )
        bech32_info = self.nodes[0].getaddressinfo(
            "bcrt1qu7xc8kkpwzxzamw5236j2gpvtxmgp2zmfzmc32"
        )
        assert_equal(bech32_info["ismine"], True)
        assert_equal(bech32_info["solvable"], True)
        assert_equal(
            bech32_info["pubkey"],
            "03451d293bef258fa768bed74a5301ce4cfee2b1a8d9f87d20bb669668d9cb75b8",
        )
        eth_info = self.nodes[0].getaddressinfo(
            "0x1286B92185a5d95eA7747F399e6cB1842851fAC3"
        )
        assert_equal(eth_info["ismine"], True)
        assert_equal(eth_info["solvable"], True)
        assert_equal(
            eth_info["pubkey"],
            "04451d293bef258fa768bed74a5301ce4cfee2b1a8d9f87d20bb669668d9cb75b86e90a39bdc9cf04e708ad0b3a8589ce3d1fab3b37a6e7651e7fa9e61e442abf1",
        )

        # Import Eth private key for:
        # Bech32: bcrt1q25m0h24ef4njmjznwwe85w99cn78k04te6w3qt
        # Eth: 0xe5BBbf6eEDc1F217D72DD97E23049ab4B21AB84E
        self.nodes[0].importprivkey(
            "56c679ab38001e7d427e3fbc4363fcd2100e74d8ac650a2d2ff3a69254d4dae4"
        )
        bech32_info = self.nodes[0].getaddressinfo(
            "bcrt1q25m0h24ef4njmjznwwe85w99cn78k04te6w3qt"
        )
        assert_equal(bech32_info["ismine"], True)
        assert_equal(bech32_info["solvable"], True)
        assert_equal(
            bech32_info["pubkey"],
            "02ed3add70f9d3fde074bc74310d5684f5e5d2836106a8286aef1324f9791658da",
        )
        eth_info = self.nodes[0].getaddressinfo(
            "0xe5BBbf6eEDc1F217D72DD97E23049ab4B21AB84E"
        )
        assert_equal(eth_info["ismine"], True)
        assert_equal(eth_info["solvable"], True)
        assert_equal(
            eth_info["pubkey"],
            "04ed3add70f9d3fde074bc74310d5684f5e5d2836106a8286aef1324f9791658da9034d75da80783a544da73d3bb809df9f8bd50309b51b8ee3fab240d5610511c",
        )

        # Import Bech32 uncompressed private key for:
        # Bech32: bcrt1qzm54jxk82jp34jx49v5uaxk4ye2pv03e5aknl6
        # Eth: 0xd61Cd3F09E2C20376BFa34ed3a4FcF512341fA0E
        self.nodes[0].importprivkey(
            "92e6XLo5jVAVwrQKPNTs93oQco8f8sDNBcpv73Dsrs397fQtFQn"
        )
        bech32_info = self.nodes[0].getaddressinfo(
            "bcrt1qzm54jxk82jp34jx49v5uaxk4ye2pv03e5aknl6"
        )
        assert_equal(bech32_info["ismine"], True)
        assert_equal(bech32_info["iswitness"], True)
        assert_equal(
            bech32_info["pubkey"],
            "02087a947bbb87f5005d25c56a10a7660694b81bffe209a9e89a6e2683a6a900b6",
        )
        eth_info = self.nodes[0].getaddressinfo(
            "0xd61Cd3F09E2C20376BFa34ed3a4FcF512341fA0E"
        )
        assert_equal(eth_info["ismine"], True)
        assert_equal(eth_info["solvable"], True)
        assert_equal(
            eth_info["pubkey"],
            "04087a947bbb87f5005d25c56a10a7660694b81bffe209a9e89a6e2683a6a900b6ff3a7732eb015021deda823f265ed7a5bbec7aa7e83eb395d4cb7d5dea63d144",
        )

        # Dump Eth address and import into node 1
        priv_key = self.nodes[0].dumpprivkey(
            "0xe5BBbf6eEDc1F217D72DD97E23049ab4B21AB84E"
        )
        assert_equal(
            priv_key, "56c679ab38001e7d427e3fbc4363fcd2100e74d8ac650a2d2ff3a69254d4dae4"
        )
        self.nodes[1].importprivkey(priv_key)

        # Check key is now present in node 1
        result = self.nodes[1].getaddressinfo(
            "0xe5BBbf6eEDc1F217D72DD97E23049ab4B21AB84E"
        )
        assert_equal(result["ismine"], True)

        # Check creation and private key dump of new Eth key
        test_eth_dump = self.nodes[0].getnewaddress("", "erc55")
        self.nodes[0].dumpprivkey(test_eth_dump)

        # Generate an address using an alias and make sure it is an witness 16 address
        addr = self.nodes[0].getnewaddress("", "eth")
        addr_info = self.nodes[0].getaddressinfo(addr)
        assert_equal(addr_info["witness_version"], 16)

        # Import addresses
        self.nodes[0].importprivkey(self.eth_address_privkey)  # eth_address
        self.nodes[0].importprivkey(self.to_address_privkey)  # self.to_address

        # Generate chain
        self.nodes[0].generate(101)

    def evm_gov_vars(self):
        # Check setting vars before height
        assert_raises_rpc_error(
            -32600,
            "Cannot be set before NextNetworkUpgradeHeight",
            self.nodes[0].setgov,
            {"ATTRIBUTES": {"v0/params/feature/evm": "true"}},
        )
        assert_raises_rpc_error(
            -32600,
            "Cannot be set before NextNetworkUpgradeHeight",
            self.nodes[0].setgov,
            {"ATTRIBUTES": {"v0/params/feature/transferdomain": "true"}},
        )
        assert_raises_rpc_error(
            -32600,
            "called before NextNetworkUpgrade height",
            self.nodes[0].evmtx,
            self.eth_address,
            0,
            21,
            21000,
            self.to_address,
            0.1,
        )
        assert_raises_rpc_error(
            -32600,
            "Cannot be set before NextNetworkUpgrade",
            self.nodes[0].setgov,
            {"ATTRIBUTES": {"v0/rules/tx/core_op_return_max_size_bytes": 1024}},
        )
        assert_raises_rpc_error(
            -32600,
            "Cannot be set before NextNetworkUpgrade",
            self.nodes[0].setgov,
            {"ATTRIBUTES": {"v0/rules/tx/evm_op_return_max_size_bytes": 65536}},
        )
        assert_raises_rpc_error(
            -32600,
            "Cannot be set before NextNetworkUpgrade",
            self.nodes[0].setgov,
            {"ATTRIBUTES": {"v0/rules/tx/dvm_op_return_max_size_bytes": 4096}},
        )

        # Check that a transferdomain default is not present in listgovs
        assert (
            "v0/transferdomain/dvm-evm/enabled"
            not in self.nodes[0].listgovs()[8][0]["ATTRIBUTES"]
        )
        assert (
            "v0/rules/tx/core_op_return_max_size_bytes"
            not in self.nodes[0].listgovs()[8][0]["ATTRIBUTES"]
        )

        # Move to fork height
        self.nodes[0].generate(4)

        # Check that all transferdomain defaults are now present in listgovs
        result = self.nodes[0].listgovs()[8][0]["ATTRIBUTES"]
        assert_equal(result["v0/transferdomain/dvm-evm/enabled"], "true")
        assert_equal(
            result["v0/transferdomain/dvm-evm/src-formats"], ["bech32", "p2pkh"]
        )
        assert_equal(result["v0/transferdomain/dvm-evm/dest-formats"], ["erc55"])
        assert_equal(result["v0/transferdomain/dvm-evm/native-enabled"], "true")
        assert_equal(result["v0/transferdomain/dvm-evm/dat-enabled"], "false")
        assert_equal(result["v0/transferdomain/evm-dvm/enabled"], "true")
        assert_equal(result["v0/transferdomain/evm-dvm/src-formats"], ["erc55"])
        assert_equal(
            result["v0/transferdomain/evm-dvm/dest-formats"], ["bech32", "p2pkh"]
        )
        assert_equal(
            result["v0/transferdomain/evm-dvm/auth-formats"],
            ["bech32-erc55", "p2pkh-erc55"],
        )
        assert_equal(result["v0/transferdomain/evm-dvm/native-enabled"], "true")
        assert_equal(result["v0/transferdomain/evm-dvm/dat-enabled"], "false")
        assert_equal(result["v0/rules/tx/core_op_return_max_size_bytes"], "1024")
        assert_equal(result["v0/rules/tx/evm_op_return_max_size_bytes"], "65536")
        assert_equal(result["v0/rules/tx/dvm_op_return_max_size_bytes"], "4096")

        # Set OP_RETURN
        self.nodes[0].setgov(
            {
                "ATTRIBUTES": {
                    "v0/rules/tx/core_op_return_max_size_bytes": 20000,
                    "v0/rules/tx/evm_op_return_max_size_bytes": 20000,
                    "v0/rules/tx/dvm_op_return_max_size_bytes": 20000,
                }
            }
        )
        self.nodes[0].generate(1)

        # Check OP_RETURN set
        result = self.nodes[0].getgov("ATTRIBUTES")["ATTRIBUTES"]
        assert_equal(result["v0/rules/tx/core_op_return_max_size_bytes"], "20000")
        assert_equal(result["v0/rules/tx/evm_op_return_max_size_bytes"], "20000")
        assert_equal(result["v0/rules/tx/dvm_op_return_max_size_bytes"], "20000")

        def verify_evm_not_enabled():
            # Check error before EVM enabled
            assert_raises_rpc_error(
                -32600,
                "Cannot create tx, EVM is not enabled",
                self.nodes[0].evmtx,
                self.eth_address,
                0,
                21,
                21000,
                self.to_address,
                0.1,
            )
            assert_raises_rpc_error(
                -32600,
                "Cannot create tx, transfer domain is not enabled",
                self.nodes[0].transferdomain,
                [
                    {
                        "src": {
                            "address": self.address,
                            "amount": "100@DFI",
                            "domain": 2,
                        },
                        "dst": {
                            "address": self.eth_address,
                            "amount": "100@DFI",
                            "domain": 3,
                        },
                    }
                ],
            )

        def verify_transferdomain_not_enabled_post_evm_on():
            # Check error before transferdomain enabled
            assert_raises_rpc_error(
                -32600,
                "Cannot create tx, transfer domain is not enabled",
                self.nodes[0].transferdomain,
                [
                    {
                        "src": {
                            "address": self.address,
                            "amount": "100@DFI",
                            "domain": 2,
                        },
                        "dst": {
                            "address": self.eth_address,
                            "amount": "100@DFI",
                            "domain": 3,
                        },
                    }
                ],
            )

        verify_evm_not_enabled()
        # Activate EVM
        self.nodes[0].setgov({"ATTRIBUTES": {"v0/params/feature/evm": "true"}})
        self.nodes[0].generate(1)
        verify_transferdomain_not_enabled_post_evm_on()

        # Activate transferdomain
        self.nodes[0].setgov(
            {"ATTRIBUTES": {"v0/params/feature/transferdomain": "true"}}
        )
        self.nodes[0].generate(1)

        # Deactivate transferdomain DVM to EVM
        self.nodes[0].setgov(
            {"ATTRIBUTES": {"v0/transferdomain/dvm-evm/enabled": "false"}}
        )
        self.nodes[0].generate(1)

        # Check error transferdomain DVM to EVM is enabled
        assert_raises_rpc_error(
            -32600,
            "DVM to EVM is not currently enabled",
            self.nodes[0].transferdomain,
            [
                {
                    "src": {"address": self.address, "amount": "100@DFI", "domain": 2},
                    "dst": {
                        "address": self.eth_address,
                        "amount": "100@DFI",
                        "domain": 3,
                    },
                }
            ],
        )

        # Activate transferdomain DVM to EVM
        self.nodes[0].setgov(
            {"ATTRIBUTES": {"v0/transferdomain/dvm-evm/enabled": "true"}}
        )
        self.nodes[0].generate(1)

        # Activate transferdomain PKHash address
        self.nodes[0].setgov(
            {"ATTRIBUTES": {"v0/transferdomain/dvm-evm/src-formats": ["bech32"]}}
        )
        self.nodes[0].generate(1)

        # Check transferdomain DVM to EVM before p2pkh addresses are enabled
        assert_raises_rpc_error(
            -32600,
            'Src address must be a legacy or Bech32 address in case of "DVM" domain',
            self.nodes[0].transferdomain,
            [
                {
                    "src": {"address": self.address, "amount": "100@DFI", "domain": 2},
                    "dst": {
                        "address": self.eth_address,
                        "amount": "100@DFI",
                        "domain": 3,
                    },
                }
            ],
        )

        # Activate transferdomain PKHash address
        self.nodes[0].setgov(
            {"ATTRIBUTES": {"v0/transferdomain/dvm-evm/src-formats": ["p2pkh"]}}
        )
        self.nodes[0].generate(1)

        # Check transferdomain DVM to EVM before bech32 addresses are enabled
        assert_raises_rpc_error(
            -32600,
            'Src address must be a legacy or Bech32 address in case of "DVM" domain',
            self.nodes[0].transferdomain,
            [
                {
                    "src": {
                        "address": self.eth_address_bech32,
                        "amount": "100@DFI",
                        "domain": 2,
                    },
                    "dst": {
                        "address": self.eth_address,
                        "amount": "100@DFI",
                        "domain": 3,
                    },
                }
            ],
        )

        # Activate transferdomain PKHash and bech32 address
        self.nodes[0].setgov(
            {
                "ATTRIBUTES": {
                    "v0/transferdomain/dvm-evm/src-formats": ["p2pkh", "bech32"]
                }
            }
        )
        self.nodes[0].generate(1)

        self.nodes[0].setgov(
            {"ATTRIBUTES": {"v0/transferdomain/dvm-evm/dest-formats": ["bech32"]}}
        )
        self.nodes[0].generate(1)

        # Check transferdomain DVM to EVM before ERC55 addresses are enabled
        assert_raises_rpc_error(
            -32600,
            'Dst address must be an ERC55 address in case of "EVM" domain',
            self.nodes[0].transferdomain,
            [
                {
                    "src": {
                        "address": self.eth_address_bech32,
                        "amount": "100@DFI",
                        "domain": 2,
                    },
                    "dst": {
                        "address": self.eth_address,
                        "amount": "100@DFI",
                        "domain": 3,
                    },
                }
            ],
        )

        # Activate transferdomain ERC55 address
        self.nodes[0].setgov(
            {"ATTRIBUTES": {"v0/transferdomain/dvm-evm/dest-formats": ["erc55"]}}
        )
        self.nodes[0].generate(1)

        # Check for invalid parameters in transferdomain rpc
        assert_raises_rpc_error(
            -5,
            "ERC55 addresses not supported",
            self.nodes[0].createrawtransaction,
            [
                {
                    "txid": "0000000000000000000000000000000000000000000000000000000000000000",
                    "vout": 1,
                }
            ],
            [{self.eth_address: 1}],
        )
        assert_raises_rpc_error(
            -5,
            "ERC55 addresses not supported",
            self.nodes[0].sendmany,
            "",
            {self.eth_address: 1},
        )
        assert_raises_rpc_error(
            -5,
            "ERC55 addresses not supported",
            self.nodes[0].sendmany,
            "",
            {self.eth_address: 1},
        )
        assert_raises_rpc_error(
            -5,
            "ERC55 addresses not supported",
            self.nodes[0].sendtoaddress,
            self.eth_address,
            1,
        )
        assert_raises_rpc_error(
            -5,
            "ERC55 addresses not supported",
            self.nodes[0].accounttoaccount,
            self.address,
            {self.eth_address: "1@DFI"},
        )

        # Deactivate transferdomain DVM to EVM
        self.nodes[0].setgov(
            {"ATTRIBUTES": {"v0/transferdomain/evm-dvm/enabled": "false"}}
        )
        self.nodes[0].generate(1)

        # Check error before transferdomain DVM to EVM is enabled
        assert_raises_rpc_error(
            -32600,
            "EVM to DVM is not currently enabled",
            self.nodes[0].transferdomain,
            [
                {
                    "src": {"address": self.address, "amount": "100@DFI", "domain": 3},
                    "dst": {
                        "address": self.eth_address,
                        "amount": "100@DFI",
                        "domain": 2,
                    },
                }
            ],
        )

        # Activate transferdomain DVM to EVM
        self.nodes[0].setgov(
            {"ATTRIBUTES": {"v0/transferdomain/evm-dvm/enabled": "true"}}
        )
        self.nodes[0].generate(1)

        # Deactivate transferdomain ERC55 address
        self.nodes[0].setgov(
            {"ATTRIBUTES": {"v0/transferdomain/evm-dvm/src-formats": ["bech32"]}}
        )
        self.nodes[0].generate(1)

        # Check transferdomain EVM to DVM before ERC55 addresses are enabled
        assert_raises_rpc_error(
            -32600,
            'Src address must be an ERC55 address in case of "EVM" domain',
            self.nodes[0].transferdomain,
            [
                {
                    "src": {
                        "address": self.eth_address,
                        "amount": "100@DFI",
                        "domain": 3,
                    },
                    "dst": {"address": self.address, "amount": "100@DFI", "domain": 2},
                }
            ],
        )

        # Activate transferdomain ERC55 address
        self.nodes[0].setgov(
            {"ATTRIBUTES": {"v0/transferdomain/evm-dvm/src-formats": ["erc55"]}}
        )
        self.nodes[0].generate(1)

        # Dectivate transferdomain ERC55 address
        self.nodes[0].setgov(
            {"ATTRIBUTES": {"v0/transferdomain/evm-dvm/dest-formats": ["bech32"]}}
        )
        self.nodes[0].generate(1)

        # Check transferdomain EVM to DVM before P2PKH addresses are enabled
        assert_raises_rpc_error(
            -32600,
            'Dst address must be a legacy or Bech32 address in case of "DVM" domain',
            self.nodes[0].transferdomain,
            [
                {
                    "src": {
                        "address": self.eth_address,
                        "amount": "100@DFI",
                        "domain": 3,
                    },
                    "dst": {"address": self.address, "amount": "100@DFI", "domain": 2},
                }
            ],
        )

        # Activate transferdomain ERC55 address
        self.nodes[0].setgov(
            {"ATTRIBUTES": {"v0/transferdomain/evm-dvm/dest-formats": ["p2pkh"]}}
        )
        self.nodes[0].generate(1)

        # Check transferdomain EVM to DVM before Bech32 addresses are enabled
        assert_raises_rpc_error(
            -32600,
            'Dst address must be a legacy or Bech32 address in case of "DVM" domain',
            self.nodes[0].transferdomain,
            [
                {
                    "src": {
                        "address": self.eth_address,
                        "amount": "100@DFI",
                        "domain": 3,
                    },
                    "dst": {
                        "address": self.eth_address_bech32,
                        "amount": "100@DFI",
                        "domain": 2,
                    },
                }
            ],
        )

        # Activate transferdomain ERC55 address
        self.nodes[0].setgov(
            {
                "ATTRIBUTES": {
                    "v0/transferdomain/evm-dvm/dest-formats": ["bech32", "p2pkh"]
                }
            }
        )
        self.nodes[0].generate(1)

        # Dectivate transferdomain ERC55 address
        self.nodes[0].setgov(
            {"ATTRIBUTES": {"v0/transferdomain/evm-dvm/auth-formats": ["p2pkh-erc55"]}}
        )
        self.nodes[0].generate(1)

        # Check transferdomain EVM to DVM before Bech32 auth is enabled
        assert_raises_rpc_error(
            -32600,
            "tx must have at least one input from account owner",
            self.nodes[0].transferdomain,
            [
                {
                    "src": {
                        "address": self.eth_address,
                        "amount": "100@DFI",
                        "domain": 3,
                    },
                    "dst": {
                        "address": self.eth_address_bech32,
                        "amount": "100@DFI",
                        "domain": 2,
                    },
                }
            ],
        )

        # Activate transferdomain ERC55 address
        self.nodes[0].setgov(
            {"ATTRIBUTES": {"v0/transferdomain/evm-dvm/auth-formats": ["bech32-erc55"]}}
        )
        self.nodes[0].generate(1)

        # Test setting of finalized block
        self.nodes[0].setgov({"ATTRIBUTES": {"v0/evm/block/finality_count": "100"}})
        self.nodes[0].generate(1)

        # Check Gov var is present
        attrs = self.nodes[0].getgov("ATTRIBUTES")["ATTRIBUTES"]
        assert_equal(attrs["v0/evm/block/finality_count"], "100")

    def setup_accounts(self):
        # Fund DFI address
        self.nodes[0].utxostoaccount({self.address: "300@DFI"})
        self.nodes[0].generate(1)

        # Fund EVM address
        self.nodes[0].transferdomain(
            [
                {
                    "src": {"address": self.address, "amount": "200@DFI", "domain": 2},
                    "dst": {
                        "address": self.eth_address,
                        "amount": "200@DFI",
                        "domain": 3,
                    },
                }
            ]
        )
        self.nodes[0].generate(1)
        self.sync_blocks()

        # Check initial balances
        dfi_balance = self.nodes[0].getaccount(self.address, {}, True)["0"]
        eth_balance = self.nodes[0].eth_getBalance(self.eth_address)
        assert_equal(dfi_balance, Decimal("100"))
        assert_equal(eth_balance, int_to_eth_u256(200))
        assert_equal(len(self.nodes[0].getaccount(self.eth_address, {}, True)), 1)

        # Check Eth balances before transfer
        assert_equal(
            int(self.nodes[0].eth_getBalance(self.eth_address)[2:], 16),
            200000000000000000000,
        )
        assert_equal(int(self.nodes[0].eth_getBalance(self.to_address)[2:], 16), 0)

        # Send tokens to burn address
        self.burn_address = "mfburnZSAM7Gs1hpDeNaMotJXSGA7edosG"
        self.nodes[0].importprivkey(
            "93ViFmLeJVgKSPxWGQHmSdT5RbeGDtGW4bsiwQM2qnQyucChMqQ"
        )
        result = self.nodes[0].getburninfo()
        assert_equal(result["address"], self.burn_address)
        self.nodes[0].accounttoaccount(self.address, {self.burn_address: "1@DFI"})
        self.nodes[0].generate(1)

    def nonce_order_and_rbf(self):
        # Get burn address and miner account balance before transaction
        self.miner_eth_address = self.nodes[0].addressmap(
            self.nodes[0].get_genesis_keys().operatorAuthAddress, 1
        )["format"]["erc55"]
        self.before_blockheight = self.nodes[0].getblockcount()
        self.miner_before = Decimal(
            self.nodes[0].w3.eth.get_balance(self.miner_eth_address)
        )

        # Check accounting of EVM fees
        attributes = self.nodes[0].getgov("ATTRIBUTES")["ATTRIBUTES"]
        assert_equal(attributes["v0/live/economy/evm/block/fee_burnt"], Decimal("0E-8"))
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_priority"], Decimal("0E-8")
        )

        # Test EVM Tx added first in time ordering
        self.nodes[0].evmtx(self.eth_address, 0, 21, 21001, self.to_address, 1)
        self.sync_mempools()

        # Add more EVM Txs to test block ordering
        tx5 = self.nodes[0].evmtx(self.eth_address, 5, 21, 21001, self.to_address, 1)
        tx4 = self.nodes[0].evmtx(self.eth_address, 4, 21, 21001, self.to_address, 1)
        tx2 = self.nodes[0].evmtx(self.eth_address, 2, 21, 21001, self.to_address, 1)
        tx1 = self.nodes[0].evmtx(self.eth_address, 1, 21, 21001, self.to_address, 1)
        tx3 = self.nodes[0].evmtx(self.eth_address, 3, 21, 21001, self.to_address, 1)
        raw_tx = self.nodes[0].getrawtransaction(tx5)
        self.sync_mempools()

        # Check the pending TXs
        result = self.nodes[0].eth_pendingTransactions()
        assert_equal(
            result[0]["blockHash"],
            "0x0000000000000000000000000000000000000000000000000000000000000000",
        )
        assert_equal(result[0]["blockNumber"], "null")
        assert_equal(result[0]["from"], self.eth_address)
        assert_equal(result[0]["gas"], "0x5209")
        assert_equal(result[0]["gasPrice"], "0x4e3b29200")
        assert_equal(
            result[0]["hash"],
            "0xadf0fbeb972cdc4a82916d12ffc6019f60005de6dde1bbc7cb4417fe5a7b1bcb",
        )
        assert_equal(result[0]["input"], "0x")
        assert_equal(result[0]["nonce"], "0x0")
        assert_equal(result[0]["to"], self.to_address.lower())
        assert_equal(result[0]["transactionIndex"], "0x0")
        assert_equal(result[0]["value"], "0xde0b6b3a7640000")
        assert_equal(result[0]["v"], "0x26")
        assert_equal(
            result[0]["r"],
            "0x3a0587be1a14bd5e68bc883e627f3c0999cff9458e30ea8049f17bd7369d7d9c",
        )
        assert_equal(
            result[0]["s"],
            "0x1876f296657bc56499cc6398617f97b2327fa87189c0a49fb671b4361876142a",
        )

        # Create replacement for nonce 0 TX with higher fee
        tx0 = self.nodes[0].evmtx(self.eth_address, 0, 22, 21001, self.to_address, 1)
        self.sync_mempools()

        # Check mempools for TXs
        mempool0 = self.nodes[0].getrawmempool()
        mempool1 = self.nodes[1].getrawmempool()
        assert_equal(sorted(mempool0), sorted(mempool1))

        # Mint TXs
        self.nodes[0].generate(1)
        blockHash = self.nodes[0].getblockhash(self.nodes[0].getblockcount())

        # Check accounting of EVM fees
        txLegacy = {
            "nonce": "0x1",
            "from": self.eth_address,
            "value": "0x1",
            "gas": "0x5208",  # 21000
            "gasPrice": "0x4e3b29200",  # 21_000_000_000,
        }
        txLegacy0 = {
            "nonce": "0x0",
            "from": self.eth_address,
            "value": "0x1",
            "gas": "0x5208",  # 21000
            "gasPrice": "0x51F4D5C00",  # 22_000_000_000,
        }

        # Check accounting of EVM fees
        fees = self.nodes[0].debug_feeEstimate(txLegacy)
        fees0 = self.nodes[0].debug_feeEstimate(txLegacy0)
        self.burnt_fee = hex_to_decimal(fees["burnt_fee"])
        self.burnt_fee0 = hex_to_decimal(fees0["burnt_fee"])
        self.priority_fee = hex_to_decimal(fees["priority_fee"])
        self.priority_fee0 = hex_to_decimal(fees0["priority_fee"])
        attributes = self.nodes[0].getgov("ATTRIBUTES")["ATTRIBUTES"]
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_burnt"],
            self.burnt_fee * 5 + self.burnt_fee0,
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_burnt_min"],
            self.burnt_fee * 5 + self.burnt_fee0,
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_burnt_min_hash"], blockHash
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_burnt_max"],
            self.burnt_fee * 5 + self.burnt_fee0,
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_burnt_max_hash"], blockHash
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_priority"],
            self.priority_fee * 5 + self.priority_fee0,
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_priority_min"],
            self.priority_fee * 5 + self.priority_fee0,
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_priority_min_hash"], blockHash
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_priority_max"],
            self.priority_fee * 5 + self.priority_fee0,
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_priority_max_hash"], blockHash
        )

        # Check TXs in block in correct order
        block_txs = self.nodes[0].getblock(
            self.nodes[0].getblockhash(self.nodes[0].getblockcount())
        )["tx"]
        assert_equal(block_txs[1], tx0)
        assert_equal(block_txs[2], tx1)
        assert_equal(block_txs[3], tx2)
        assert_equal(block_txs[4], tx3)
        assert_equal(block_txs[5], tx4)
        assert_equal(block_txs[6], tx5)

        # Check Eth balances after transfer
        assert_equal(
            int(self.nodes[0].eth_getBalance(self.eth_address)[2:], 16),
            193997333000000000000,
        )
        assert_equal(
            int(self.nodes[0].eth_getBalance(self.to_address)[2:], 16),
            6000000000000000000,
        )

        # Get miner account balance after transfer
        miner_after = Decimal(self.nodes[0].w3.eth.get_balance(self.miner_eth_address))
        self.miner_fee = miner_after - self.miner_before

        # Check EVM Tx shows in block on EVM side
        block = self.nodes[0].eth_getBlockByNumber("latest", False)
        assert_equal(
            block["transactions"],
            [
                "0xcffc5526b42c0defa7d90cc806e50e582a0339a3336c7e32de237fbe4d62263b",
                "0x66c380af8f76295bab799d1228af75bd3c436b7bbeb9d93acd8baac9377a851a",
                "0x02b05a6646feb65bf9491f9551e02678263239dc2512d73c9ad6bc80dc1c13ff",
                "0x1d4c8a49ad46d9362c805d6cdf9a8937ba115eec9def17b3efe23a09ee694e5c",
                "0xa382aa9f70f15bd0bf70e838f5ac0163e2501dbff2712e9622275e655e42ec1c",
                "0x05d4cdabc4ad55fb7caf42a7fb6d4e8cea991e2331cd9d98a5eef10d84b5c994",
            ],
        )

        # Try and send an already sent transaction
        assert_raises_rpc_error(
            -26,
            "evm tx failed to pre-validate invalid nonce. Account nonce 6, signed_tx nonce 5",
            self.nodes[0].sendrawtransaction,
            raw_tx,
        )

    def validate_xvm_coinbase(self):
        # Check EVM blockhash
        eth_block = self.nodes[0].eth_getBlockByNumber("latest")
        eth_hash = eth_block["hash"][2:]
        block = self.nodes[0].getblock(
            self.nodes[0].getblockhash(self.nodes[0].getblockcount()), 3
        )
        coinbase_xvm = block["tx"][0]["vm"]
        assert_equal(coinbase_xvm["vmtype"], "coinbase")
        assert_equal(coinbase_xvm["txtype"], "coinbase")
        block_hash = coinbase_xvm["msg"]["evm"]["blockHash"][2:]
        assert_equal(block_hash, eth_hash)

        # Check EVM miner fee
        opreturn_priority_fee_sats = coinbase_xvm["msg"]["evm"]["priorityFee"]
        opreturn_priority_fee_amount = Decimal(opreturn_priority_fee_sats) / 100000000
        assert_equal(
            opreturn_priority_fee_amount, self.miner_fee / int(math.pow(10, 18))
        )

        # Check EVM beneficiary address
        opreturn_miner_address = coinbase_xvm["msg"]["evm"]["beneficiary"][2:]
        miner_eth_address = (
            self.nodes[0]
            .addressmap(self.nodes[0].get_genesis_keys().operatorAuthAddress, 1)[
                "format"
            ]["erc55"][2:]
            .lower()
        )
        assert_equal(opreturn_miner_address, miner_eth_address)

    def evm_rollback(self):
        # Test rollback of EVM TX
        self.rollback_to(self.before_blockheight, self.nodes)
        miner_rollback = Decimal(
            self.nodes[0].w3.eth.get_balance(self.miner_eth_address)
        )
        assert_equal(self.miner_before, miner_rollback)

        # Check Eth balances before transfer
        assert_equal(
            int(self.nodes[0].eth_getBalance(self.eth_address)[2:], 16),
            200000000000000000000,
        )
        assert_equal(int(self.nodes[0].eth_getBalance(self.to_address)[2:], 16), 0)

    def mempool_tx_limit(self):
        # Test max limit of TX from a specific sender
        for i in range(64):
            self.nodes[0].evmtx(self.eth_address, i, 21, 21001, self.to_address, 1)

        # Test error at the 64th EVM TX
        assert_raises_rpc_error(
            -26,
            "too-many-eth-txs-by-sender",
            self.nodes[0].evmtx,
            self.eth_address,
            64,
            21,
            21001,
            self.to_address,
            1,
        )

        # Mint a block
        self.nodes[0].generate(1)
        self.blockHash = self.nodes[0].getblockhash(self.nodes[0].getblockcount())
        block_txs = self.nodes[0].getblock(
            self.nodes[0].getblockhash(self.nodes[0].getblockcount())
        )["tx"]
        assert_equal(len(block_txs), 65)

        # Check accounting of EVM fees
        attributes = self.nodes[0].getgov("ATTRIBUTES")["ATTRIBUTES"]
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_burnt"], self.burnt_fee * 64
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_burnt_min"], self.burnt_fee * 64
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_burnt_min_hash"], self.blockHash
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_burnt_max"], self.burnt_fee * 64
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_burnt_max_hash"], self.blockHash
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_priority"], self.priority_fee * 64
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_priority_min"],
            self.priority_fee * 64,
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_priority_min_hash"],
            self.blockHash,
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_priority_max"],
            self.priority_fee * 64,
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_priority_max_hash"],
            self.blockHash,
        )

        # Check Eth balances after transfer
        assert_equal(
            int(self.nodes[0].eth_getBalance(self.eth_address)[2:], 16),
            135971776000000000000,
        )
        assert_equal(
            int(self.nodes[0].eth_getBalance(self.to_address)[2:], 16),
            64000000000000000000,
        )

        # Try and send another TX to make sure mempool has removed entries
        tx = self.nodes[0].evmtx(self.eth_address, 64, 21, 21001, self.to_address, 1)
        self.nodes[0].generate(1)
        self.blockHash1 = self.nodes[0].getblockhash(self.nodes[0].getblockcount())

        # Check accounting of EVM fees
        attributes = self.nodes[0].getgov("ATTRIBUTES")["ATTRIBUTES"]
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_burnt"], self.burnt_fee * 65
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_burnt_min"], self.burnt_fee
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_burnt_min_hash"], self.blockHash1
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_burnt_max"], self.burnt_fee * 64
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_burnt_max_hash"], self.blockHash
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_priority"], self.priority_fee * 65
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_priority_min"], self.priority_fee
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_priority_min_hash"],
            self.blockHash1,
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_priority_max"],
            self.priority_fee * 64,
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_priority_max_hash"],
            self.blockHash,
        )

        # Check TX is in block
        block_txs = self.nodes[0].getblock(
            self.nodes[0].getblockhash(self.nodes[0].getblockcount())
        )["tx"]
        assert_equal(block_txs[1], tx)

    def multiple_eth_rbf(self):
        # Test multiple replacement TXs with differing fees
        self.nodes[0].evmtx(self.eth_address, 65, 22, 21001, self.to_address, 1)
        self.nodes[0].evmtx(self.eth_address, 65, 23, 21001, self.to_address, 1)
        tx0 = self.nodes[0].evmtx(self.eth_address, 65, 25, 21001, self.to_address, 1)
        assert_raises_rpc_error(
            -26,
            "evm-low-fee",
            self.nodes[0].evmtx,
            self.eth_address,
            65,
            21,
            21001,
            self.to_address,
            1,
        )
        assert_raises_rpc_error(
            -26,
            "evm-low-fee",
            self.nodes[0].evmtx,
            self.eth_address,
            65,
            24,
            21001,
            self.to_address,
            1,
        )
        self.nodes[0].evmtx(self.to_address, 0, 22, 21001, self.eth_address, 1)
        self.nodes[0].evmtx(self.to_address, 0, 23, 21001, self.eth_address, 1)
        tx1 = self.nodes[0].evmtx(self.to_address, 0, 25, 21001, self.eth_address, 1)
        assert_raises_rpc_error(
            -26,
            "evm-low-fee",
            self.nodes[0].evmtx,
            self.to_address,
            0,
            21,
            21001,
            self.eth_address,
            1,
        )
        assert_raises_rpc_error(
            -26,
            "evm-low-fee",
            self.nodes[0].evmtx,
            self.to_address,
            0,
            24,
            21001,
            self.eth_address,
            1,
        )

        # Check mempool only contains two entries
        assert_equal(
            sorted(self.nodes[0].getrawmempool()),
            [
                "2b13a48b2af32206a2d60d535ad46d4958c25b4ddd4c30f3a2da32f092c23916",
                "6a6b53538b66e0eb477ce923901e6fa1714c4f52a83f8f1793c92c14ebc0f910",
            ],
        )
        self.nodes[0].generate(1)

        # Check accounting of EVM fees
        txLegacy65 = {
            "nonce": "0x1",
            "from": self.eth_address,
            "value": "0x1",
            "gas": "0x5208",  # 21000
            "gasPrice": "0x5D21DBA00",  # 25_000_000_000,
        }
        fees65 = self.nodes[0].debug_feeEstimate(txLegacy65)
        self.burnt_fee65 = hex_to_decimal(fees65["burnt_fee"])
        self.priority_fee65 = hex_to_decimal(fees65["priority_fee"])
        attributes = self.nodes[0].getgov("ATTRIBUTES")["ATTRIBUTES"]
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_burnt"],
            self.burnt_fee * 65 + 2 * self.burnt_fee65,
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_priority"],
            self.priority_fee * 65 + 2 * self.priority_fee65,
        )
        attributes = self.nodes[0].getgov("ATTRIBUTES")["ATTRIBUTES"]
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_burnt"],
            self.burnt_fee * 65 + 2 * self.burnt_fee65,
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_burnt_min"], self.burnt_fee
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_burnt_min_hash"], self.blockHash1
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_burnt_max"], self.burnt_fee * 64
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_burnt_max_hash"], self.blockHash
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_priority"],
            self.priority_fee * 65 + 2 * self.priority_fee65,
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_priority_min"], self.priority_fee
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_priority_min_hash"],
            self.blockHash1,
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_priority_max"],
            self.priority_fee * 64,
        )
        assert_equal(
            attributes["v0/live/economy/evm/block/fee_priority_max_hash"],
            self.blockHash,
        )

        # Check highest paying fee TX in block
        block_txs = self.nodes[0].getblock(
            self.nodes[0].getblockhash(self.nodes[0].getblockcount())
        )["tx"]
        assert_equal(block_txs[1], tx0)
        assert_equal(block_txs[2], tx1)

    def sendtransaction_auto_nonce(self):
        self.nodes[0].clearmempool()
        nonce = self.nodes[0].w3.eth.get_transaction_count(self.eth_address)

        evm_nonces = [nonce, nonce + 2, nonce + 3]

        # send evmtxs with nonces
        for nonce in evm_nonces:
            self.nodes[0].eth_sendTransaction(
                {
                    "nonce": self.nodes[0].w3.to_hex(nonce),
                    "from": self.eth_address,
                    "to": "0x0000000000000000000000000000000000000000",
                    "value": "0x1",
                    "gas": "0x100000",
                    "gasPrice": "0x4e3b29200",
                }
            )

        # send transferdomain without specifying nonce
        self.nodes[0].eth_sendTransaction(
            {
                "from": self.eth_address,
                "to": "0x0000000000000000000000000000000000000000",
                "value": "0x1",
                "gas": "0x100000",
                "gasPrice": "0x4e3b29200",
            }
        )

        balance_before = self.nodes[0].w3.eth.get_balance(
            "0x0000000000000000000000000000000000000000"
        )
        assert_equal(len(self.nodes[0].getrawmempool()), 4)
        self.nodes[0].generate(5)
        balance_after = self.nodes[0].w3.eth.get_balance(
            "0x0000000000000000000000000000000000000000"
        )

        assert_equal(
            len(self.nodes[0].getrawmempool()), 0
        )  # all TXs should make it through
        assert_equal(
            balance_before + 4, balance_after
        )  # burn balance should increase by 4wei

    def toggle_evm_enablement(self):
        # Deactivate EVM
        self.nodes[0].setgov({"ATTRIBUTES": {"v0/params/feature/evm": "false"}})
        self.nodes[0].generate(1)
        evm_disabling_block = self.nodes[0].eth_getBlockByNumber("latest")

        self.nodes[0].generate(1)
        evm_disabled_first_block = self.nodes[0].eth_getBlockByNumber("latest")
        assert_equal(evm_disabling_block, evm_disabled_first_block)

        # Reactivate EVM
        self.nodes[0].setgov({"ATTRIBUTES": {"v0/params/feature/evm": "true"}})
        self.nodes[0].generate(1)
        evm_enabling_block = self.nodes[0].eth_getBlockByNumber("latest")
        assert_equal(evm_disabled_first_block, evm_enabling_block)

        self.nodes[0].generate(1)
        # Check block is one higher than before
        evm_first_valid_block = self.nodes[0].eth_getBlockByNumber("latest")
        assert_equal(
            int(evm_first_valid_block["number"], base=16),
            int(evm_enabling_block["number"], base=16) + 1,
        )


if __name__ == "__main__":
    EVMTest().main()
