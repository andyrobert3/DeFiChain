#!/usr/bin/env python3
# Copyright (c) 2014-2019 The Bitcoin Core developers
# Copyright (c) DeFi Blockchain Developers
# Distributed under the MIT software license, see the accompanying
# file LICENSE or http://www.opensource.org/licenses/mit-license.php.
"""Test EVM miner behaviour"""
from test_framework.evm_contract import EVMContract
from test_framework.test_framework import DefiTestFramework
from test_framework.util import (
    assert_equal,
    assert_raises_rpc_error,
)
from decimal import Decimal


class EVMTest(DefiTestFramework):
    def set_test_params(self):
        self.num_nodes = 1
        self.setup_clean_chain = True
        self.extra_args = [
            [
                "-dummypos=0",
                "-txnotokens=0",
                "-amkheight=50",
                "-bayfrontheight=51",
                "-dakotaheight=51",
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

    def setup(self):
        self.address = self.nodes[0].get_genesis_keys().ownerAuthAddress
        self.address_erc55 = self.nodes[0].addressmap(self.address, 1)["format"][
            "erc55"
        ]
        self.ethAddress = "0x9b8a4af42140d8a4c153a822f02571a1dd037e89"
        self.ethPrivKey = (
            "af990cc3ba17e776f7f57fcc59942a82846d75833fa17d2ba59ce6858d886e23"
        )
        self.toAddress = "0x6c34cbb9219d8caa428835d2073e8ec88ba0a110"
        self.toPrivKey = (
            "17b8cb134958b3d8422b6c43b0732fcdb8c713b524df2d45de12f0c7e214ba35"
        )
        self.nodes[0].importprivkey(self.ethPrivKey)  # ethAddress
        self.nodes[0].importprivkey(self.toPrivKey)  # toAddress

        # Generate chain
        self.nodes[0].generate(101)

        assert_raises_rpc_error(
            -32600,
            "called before NextNetworkUpgrade height",
            self.nodes[0].evmtx,
            self.ethAddress,
            0,
            21,
            21000,
            self.toAddress,
            0.1,
        )

        # Move to fork height
        self.nodes[0].generate(4)

        self.nodes[0].getbalance()
        self.nodes[0].utxostoaccount({self.address: "201@DFI"})
        self.nodes[0].setgov(
            {
                "ATTRIBUTES": {
                    "v0/params/feature/evm": "true",
                    "v0/params/feature/transferdomain": "true",
                    "v0/transferdomain/dvm-evm/enabled": "true",
                    "v0/transferdomain/dvm-evm/src-formats": ["p2pkh", "bech32"],
                    "v0/transferdomain/dvm-evm/dest-formats": ["erc55"],
                    "v0/transferdomain/evm-dvm/src-formats": ["erc55"],
                    "v0/transferdomain/evm-dvm/auth-formats": ["bech32-erc55"],
                    "v0/transferdomain/evm-dvm/dest-formats": ["p2pkh", "bech32"],
                }
            }
        )
        self.nodes[0].generate(2)
        self.nodes[0].transferdomain(
            [
                {
                    "src": {"address": self.address, "amount": "100@DFI", "domain": 2},
                    "dst": {
                        "address": self.ethAddress,
                        "amount": "100@DFI",
                        "domain": 3,
                    },
                }
            ]
        )
        self.nodes[0].generate(1)
        self.start_height = self.nodes[0].getblockcount()

    def block_size_gas_limit(self):
        self.rollback_to(self.start_height)
        abi, bytecode, _ = EVMContract.from_file("Loop.sol", "Loop").compile()
        compiled = self.nodes[0].w3.eth.contract(abi=abi, bytecode=bytecode)
        tx = compiled.constructor().build_transaction(
            {
                "chainId": self.nodes[0].w3.eth.chain_id,
                "nonce": self.nodes[0].w3.eth.get_transaction_count(self.ethAddress),
                "maxFeePerGas": 10_000_000_000,
                "maxPriorityFeePerGas": 1_500_000_000,
                "gas": 1_000_000,
            }
        )
        signed = self.nodes[0].w3.eth.account.sign_transaction(tx, self.ethPrivKey)
        hash = self.nodes[0].w3.eth.send_raw_transaction(signed.rawTransaction)
        self.nodes[0].generate(1)
        receipt = self.nodes[0].w3.eth.wait_for_transaction_receipt(hash)
        contract = self.nodes[0].w3.eth.contract(
            address=receipt["contractAddress"], abi=abi
        )

        hashes = []
        start_nonce = self.nodes[0].w3.eth.get_transaction_count(self.ethAddress)
        for i in range(40):
            # tx call actual used gas - 1_761_626.
            # tx should always pass evm tx validation, but may return early in construct block.
            tx = contract.functions.loop(10_000).build_transaction(
                {
                    "chainId": self.nodes[0].w3.eth.chain_id,
                    "nonce": start_nonce + i,
                    "gasPrice": 25_000_000_000,
                    "gas": 30_000_000,
                }
            )
            signed = self.nodes[0].w3.eth.account.sign_transaction(tx, self.ethPrivKey)
            hash = self.nodes[0].w3.eth.send_raw_transaction(signed.rawTransaction)
            hashes.append(signed.hash.hex().lower()[2:])

        hash = self.nodes[0].eth_sendTransaction(
            {
                "nonce": hex(start_nonce + 40),
                "from": self.ethAddress,
                "to": self.toAddress,
                "value": "0xDE0B6B3A7640000",  # 1 DFI
                "gas": "0x5209",
                "gasPrice": "0x5D21DBA00",  # 25_000_000_000
            }
        )
        hashes.append(hash.lower()[2:])
        hash = self.nodes[0].eth_sendTransaction(
            {
                "nonce": hex(start_nonce + 41),
                "from": self.ethAddress,
                "to": self.toAddress,
                "value": "0xDE0B6B3A7640000",  # 1 DFI
                "gas": "0x5209",
                "gasPrice": "0x5D21DBA00",  # 25_000_000_000
            }
        )
        hashes.append(hash.lower()[2:])

        first_block_total_txs = 17
        second_block_total_txs = 17
        third_block_total_txs = 8

        self.nodes[0].generate(1)
        block_info = self.nodes[0].getblock(self.nodes[0].getbestblockhash(), 4)
        # Check that the first 17 evm contract call txs is minted in the current block
        assert_equal(len(block_info["tx"]) - 1, first_block_total_txs)
        for idx, tx_info in enumerate(block_info["tx"][1:]):
            if idx == 0:
                continue
            assert_equal(tx_info["vm"]["vmtype"], "evm")
            assert_equal(tx_info["vm"]["txtype"], "Evm")
            assert_equal(tx_info["vm"]["msg"]["sender"], self.ethAddress)
            assert_equal(tx_info["vm"]["msg"]["nonce"], start_nonce + idx)
            assert_equal(tx_info["vm"]["msg"]["hash"], hashes[idx])
            assert_equal(tx_info["vm"]["msg"]["to"], receipt["contractAddress"].lower())

        self.nodes[0].generate(1)
        block_info = self.nodes[0].getblock(self.nodes[0].getbestblockhash(), 4)
        # Check that the next 17 of the evm contract call txs is minted in the next block
        assert_equal(len(block_info["tx"]) - 1, second_block_total_txs)
        for idx, tx_info in enumerate(block_info["tx"][1:]):
            assert_equal(tx_info["vm"]["vmtype"], "evm")
            assert_equal(tx_info["vm"]["txtype"], "Evm")
            assert_equal(tx_info["vm"]["msg"]["sender"], self.ethAddress)
            assert_equal(
                tx_info["vm"]["msg"]["nonce"], start_nonce + first_block_total_txs + idx
            )
            assert_equal(
                tx_info["vm"]["msg"]["hash"], hashes[first_block_total_txs + idx]
            )
            assert_equal(tx_info["vm"]["msg"]["to"], receipt["contractAddress"].lower())

        # Check that the remaining evm txs is minted into this block
        self.nodes[0].generate(1)
        block_info = self.nodes[0].getblock(self.nodes[0].getbestblockhash(), 4)
        assert_equal(len(block_info["tx"]) - 1, third_block_total_txs)
        # Check ordering of evm txs - first 6 evm txs are evm contract all txs
        tx_infos = block_info["tx"][1:]
        for idx in range(1, (40 - first_block_total_txs - second_block_total_txs)):
            assert_equal(tx_infos[idx]["vm"]["vmtype"], "evm")
            assert_equal(tx_infos[idx]["vm"]["txtype"], "Evm")
            assert_equal(tx_infos[idx]["vm"]["msg"]["sender"], self.ethAddress)
            assert_equal(
                tx_infos[idx]["vm"]["msg"]["nonce"],
                start_nonce + first_block_total_txs + second_block_total_txs + idx,
            )
            assert_equal(
                tx_infos[idx]["vm"]["msg"]["hash"],
                hashes[first_block_total_txs + second_block_total_txs + idx],
            )
            assert_equal(
                tx_infos[idx]["vm"]["msg"]["to"], receipt["contractAddress"].lower()
            )
        for idx in range(6, third_block_total_txs):
            assert_equal(tx_infos[idx]["vm"]["vmtype"], "evm")
            assert_equal(tx_infos[idx]["vm"]["txtype"], "Evm")
            assert_equal(tx_infos[idx]["vm"]["msg"]["sender"], self.ethAddress)
            assert_equal(
                tx_infos[idx]["vm"]["msg"]["nonce"],
                start_nonce + first_block_total_txs + second_block_total_txs + idx,
            )
            assert_equal(
                tx_infos[idx]["vm"]["msg"]["hash"],
                hashes[first_block_total_txs + second_block_total_txs + idx],
            )
            assert_equal(tx_infos[idx]["vm"]["msg"]["to"], self.toAddress)

    def invalid_evm_tx_in_block_creation(self):
        self.rollback_to(self.start_height)
        before_balance = Decimal(
            self.nodes[0].getaccount(self.ethAddress)[0].split("@")[0]
        )
        start_nonce = self.nodes[0].w3.eth.get_transaction_count(self.ethAddress)
        for idx in range(20):
            self.nodes[0].eth_sendTransaction(
                {
                    "nonce": hex(start_nonce + idx),
                    "from": self.ethAddress,
                    "to": self.toAddress,
                    "value": "0x8AC7230489E80000",  # 10 DFI
                    "gas": "0x5209",
                    "gasPrice": "0x5D21DBA00",  # 25_000_000_000
                }
            )

        self.nodes[0].generate(1)

        # Accounting
        # Each tx transfers 10 DFI
        tx_value = Decimal("10")
        # Each tx gas fees: 25_000_000_000 * 21_000
        gas_fee = Decimal("0.000525")
        # 9 txs should succeed, the remaining 11 txs fail due to out of funds
        correct_transfer = tx_value * Decimal("9")
        # Miner gets paid the gas fees for all txs executed, even if they fail
        correct_gas_fees = gas_fee * Decimal("20")
        correct_balance = correct_transfer + correct_gas_fees
        deducted_balance = before_balance - Decimal(
            self.nodes[0].getaccount(self.ethAddress)[0].split("@")[0]
        )
        assert_equal(deducted_balance, correct_balance)

        # Check to ensure both custom evm txs were minted on DVM side
        block_info = self.nodes[0].getblock(self.nodes[0].getbestblockhash(), 4)
        assert_equal(len(block_info["tx"]) - 1, 20)

    def state_dependent_txs_in_block_and_queue(self):
        self.rollback_to(self.start_height)
        before_balance = Decimal(
            self.nodes[0].getaccount(self.ethAddress)[0].split("@")[0]
        )
        assert_equal(before_balance, Decimal("100"))

        abi, bytecode, _ = EVMContract.from_file(
            "StateChange.sol", "StateChange"
        ).compile()
        compiled = self.nodes[0].w3.eth.contract(abi=abi, bytecode=bytecode)
        tx = compiled.constructor().build_transaction(
            {
                "chainId": self.nodes[0].w3.eth.chain_id,
                "nonce": self.nodes[0].w3.eth.get_transaction_count(self.ethAddress),
                "maxFeePerGas": 10_000_000_000,
                "maxPriorityFeePerGas": 1_500_000_000,
                "gas": 1_000_000,
            }
        )
        signed = self.nodes[0].w3.eth.account.sign_transaction(tx, self.ethPrivKey)
        hash = self.nodes[0].w3.eth.send_raw_transaction(signed.rawTransaction)
        self.nodes[0].generate(1)
        contract_address = self.nodes[0].w3.eth.wait_for_transaction_receipt(hash)[
            "contractAddress"
        ]
        contract = self.nodes[0].w3.eth.contract(address=contract_address, abi=abi)

        # gas used values
        gas_used_when_true = Decimal("1589866")
        gas_used_when_false = Decimal("23830")
        gas_used_when_change_state = Decimal("21952")

        # Set state to true
        tx = contract.functions.changeState(True).build_transaction(
            {
                "chainId": self.nodes[0].w3.eth.chain_id,
                "nonce": self.nodes[0].w3.eth.get_transaction_count(self.ethAddress),
                "gasPrice": 25_000_000_000,
                "gas": 30_000_000,
            }
        )
        signed = self.nodes[0].w3.eth.account.sign_transaction(tx, self.ethPrivKey)
        hash = self.nodes[0].w3.eth.send_raw_transaction(signed.rawTransaction)
        self.nodes[0].generate(1)

        tx = contract.functions.loop(9_000).build_transaction(
            {
                "chainId": self.nodes[0].w3.eth.chain_id,
                "nonce": self.nodes[0].w3.eth.get_transaction_count(self.ethAddress),
                "gasPrice": 25_000_000_000,
                "gas": 30_000_000,
            }
        )
        signed = self.nodes[0].w3.eth.account.sign_transaction(tx, self.ethPrivKey)
        hash = self.nodes[0].w3.eth.send_raw_transaction(signed.rawTransaction)
        self.nodes[0].generate(1)
        gas_used = Decimal(
            self.nodes[0].w3.eth.wait_for_transaction_receipt(hash)["gasUsed"]
        )
        assert_equal(gas_used, gas_used_when_true)

        # Set state to false
        tx = contract.functions.changeState(False).build_transaction(
            {
                "chainId": self.nodes[0].w3.eth.chain_id,
                "nonce": self.nodes[0].w3.eth.get_transaction_count(self.ethAddress),
                "gasPrice": 25_000_000_000,
                "gas": 30_000_000,
            }
        )
        signed = self.nodes[0].w3.eth.account.sign_transaction(tx, self.ethPrivKey)
        hash = self.nodes[0].w3.eth.send_raw_transaction(signed.rawTransaction)
        self.nodes[0].generate(1)
        gas_used = Decimal(
            self.nodes[0].w3.eth.wait_for_transaction_receipt(hash)["gasUsed"]
        )
        assert_equal(gas_used, gas_used_when_change_state)

        tx = contract.functions.loop(9_000).build_transaction(
            {
                "chainId": self.nodes[0].w3.eth.chain_id,
                "nonce": self.nodes[0].w3.eth.get_transaction_count(self.ethAddress),
                "gasPrice": 25_000_000_000,
                "gas": 30_000_000,
            }
        )
        signed = self.nodes[0].w3.eth.account.sign_transaction(tx, self.ethPrivKey)
        hash = self.nodes[0].w3.eth.send_raw_transaction(signed.rawTransaction)
        self.nodes[0].generate(1)
        gas_used = Decimal(
            self.nodes[0].w3.eth.wait_for_transaction_receipt(hash)["gasUsed"]
        )
        assert_equal(gas_used, gas_used_when_false)

        # Set state back to true
        tx = contract.functions.changeState(True).build_transaction(
            {
                "chainId": self.nodes[0].w3.eth.chain_id,
                "nonce": self.nodes[0].w3.eth.get_transaction_count(self.ethAddress),
                "gasPrice": 25_000_000_000,
                "gas": 30_000_000,
            }
        )
        signed = self.nodes[0].w3.eth.account.sign_transaction(tx, self.ethPrivKey)
        hash = self.nodes[0].w3.eth.send_raw_transaction(signed.rawTransaction)
        self.nodes[0].generate(1)

        hashes = []
        count = self.nodes[0].w3.eth.get_transaction_count(self.ethAddress)
        for idx in range(10):
            tx = contract.functions.loop(9_000).build_transaction(
                {
                    "chainId": self.nodes[0].w3.eth.chain_id,
                    "nonce": count + idx,
                    "gasPrice": 25_000_000_000,
                    "gas": 30_000_000,
                }
            )
            signed = self.nodes[0].w3.eth.account.sign_transaction(tx, self.ethPrivKey)
            hash = self.nodes[0].w3.eth.send_raw_transaction(signed.rawTransaction)
            hashes.append((signed.hash.hex()))

        # Send change of state
        tx = contract.functions.changeState(False).build_transaction(
            {
                "chainId": self.nodes[0].w3.eth.chain_id,
                "nonce": count + 10,
                "gasPrice": 25_000_000_000,
                "gas": 30_000_000,
            }
        )
        signed = self.nodes[0].w3.eth.account.sign_transaction(tx, self.ethPrivKey)
        hash = self.nodes[0].w3.eth.send_raw_transaction(signed.rawTransaction)
        hashes.append(signed.hash.hex())

        for idx in range(15):
            tx = contract.functions.loop(9_000).build_transaction(
                {
                    "chainId": self.nodes[0].w3.eth.chain_id,
                    "nonce": count + 11 + idx,
                    "gasPrice": 25_000_000_000,
                    "gas": 30_000_000,
                }
            )
            signed = self.nodes[0].w3.eth.account.sign_transaction(tx, self.ethPrivKey)
            hash = self.nodes[0].w3.eth.send_raw_transaction(signed.rawTransaction)
            hashes.append(signed.hash.hex())

        self.nodes[0].generate(1)

        block = self.nodes[0].eth_getBlockByNumber("latest")
        assert_equal(len(block["transactions"]), 26)

        # Check first 10 txs should have gas used when true
        for idx in range(10):
            gas_used = Decimal(
                self.nodes[0].w3.eth.wait_for_transaction_receipt(hashes[idx])[
                    "gasUsed"
                ]
            )
            assert_equal(block["transactions"][idx], hashes[idx])
            assert_equal(gas_used, gas_used_when_true)

        gas_used = Decimal(
            self.nodes[0].w3.eth.wait_for_transaction_receipt(hashes[10])["gasUsed"]
        )
        assert_equal(gas_used, gas_used_when_change_state)

        # Check last 5 txs should have gas used when false
        for idx in range(8):
            gas_used = Decimal(
                self.nodes[0].w3.eth.wait_for_transaction_receipt(hashes[11 + idx])[
                    "gasUsed"
                ]
            )
            assert_equal(block["transactions"][11 + idx], hashes[11 + idx])
            assert_equal(gas_used, gas_used_when_false)

        # TODO: Thereotical block size calculated in txqueue would be:
        # gas_used_when_true * 18 + gas_used_when_change_state = 28639540
        # But the minted block is only of size 16111252.
        correct_gas_used = (
            gas_used_when_true * 10
            + gas_used_when_false * 15
            + gas_used_when_change_state
        )
        block_info = self.nodes[0].getblock(self.nodes[0].getbestblockhash(), 4)
        assert_equal(
            block_info["tx"][0]["vm"]["xvmHeader"]["gasUsed"], correct_gas_used
        )

    def multiple_evm_and_transferdomain_txs(self):
        self.rollback_to(self.start_height)
        abi, bytecode, _ = EVMContract.from_file("Loop.sol", "Loop").compile()
        compiled = self.nodes[0].w3.eth.contract(abi=abi, bytecode=bytecode)
        tx = compiled.constructor().build_transaction(
            {
                "chainId": self.nodes[0].w3.eth.chain_id,
                "nonce": self.nodes[0].w3.eth.get_transaction_count(self.ethAddress),
                "maxFeePerGas": 10_000_000_000,
                "maxPriorityFeePerGas": 1_500_000_000,
                "gas": 1_000_000,
            }
        )
        signed = self.nodes[0].w3.eth.account.sign_transaction(tx, self.ethPrivKey)
        hash = self.nodes[0].w3.eth.send_raw_transaction(signed.rawTransaction)
        self.nodes[0].generate(1)

        start_nonce = self.nodes[0].w3.eth.get_transaction_count(self.ethAddress)
        start_nonce_erc55 = self.nodes[0].w3.eth.get_transaction_count(
            self.address_erc55
        )
        receipt = self.nodes[0].w3.eth.wait_for_transaction_receipt(hash)
        contract = self.nodes[0].w3.eth.contract(
            address=receipt["contractAddress"], abi=abi
        )

        for i in range(16):
            # tx call actual used gas - 1_761_626.
            # tx should always pass evm tx validation, but may return early in construct block.
            tx = contract.functions.loop(10_000).build_transaction(
                {
                    "chainId": self.nodes[0].w3.eth.chain_id,
                    "nonce": start_nonce + i,
                    "gasPrice": 25_000_000_000,
                    "gas": 30_000_000,
                }
            )
            signed = self.nodes[0].w3.eth.account.sign_transaction(tx, self.ethPrivKey)
            self.nodes[0].w3.eth.send_raw_transaction(signed.rawTransaction)

        for i in range(6):
            self.nodes[0].transferdomain(
                [
                    {
                        "src": {
                            "address": self.address,
                            "amount": "1@DFI",
                            "domain": 2,
                        },
                        "dst": {
                            "address": self.ethAddress,
                            "amount": "1@DFI",
                            "domain": 3,
                        },
                        "nonce": start_nonce_erc55 + i,
                    }
                ]
            )
        self.nodes[0].generate(1)
        assert_equal(len(self.nodes[0].getrawmempool()), 0)

    def multiple_transferdomain_txs(self):
        self.rollback_to(self.start_height)
        start_nonce_erc55 = self.nodes[0].w3.eth.get_transaction_count(
            self.address_erc55
        )
        for i in range(10):
            self.nodes[0].transferdomain(
                [
                    {
                        "src": {
                            "address": self.address,
                            "amount": "1@DFI",
                            "domain": 2,
                        },
                        "dst": {
                            "address": self.ethAddress,
                            "amount": "1@DFI",
                            "domain": 3,
                        },
                        "nonce": start_nonce_erc55 + i,
                    }
                ]
            )
        self.nodes[0].generate(1)

        for i in range(10):
            assert_raises_rpc_error(
                -32600,
                "transferdomain evm tx failed to pre-validate : Invalid nonce. Account nonce 11, signed_tx nonce {}".format(
                    start_nonce_erc55 + i
                ),
                self.nodes[0].transferdomain,
                [
                    {
                        "src": {
                            "address": self.address,
                            "amount": "1@DFI",
                            "domain": 2,
                        },
                        "dst": {
                            "address": self.ethAddress,
                            "amount": "1@DFI",
                            "domain": 3,
                        },
                        "nonce": start_nonce_erc55 + i,
                    }
                ],
            )

    def run_test(self):
        self.setup()

        # Multiple mempool fee replacement
        self.block_size_gas_limit()

        # # Test invalid tx in block creation
        self.invalid_evm_tx_in_block_creation()

        # # Test for block size overflow from fee mismatch between tx queue and block
        self.state_dependent_txs_in_block_and_queue()

        # Test for multiple expensive evm txs and transferdomain txs in the same block
        self.multiple_evm_and_transferdomain_txs()

        # Test for multiple transferdomain txs in the same block
        self.multiple_transferdomain_txs()


if __name__ == "__main__":
    EVMTest().main()
