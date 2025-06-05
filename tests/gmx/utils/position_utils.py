"""
This file aims to emulate the off-chain `Keeper`'s actions for increase position.
"""
from decimal import Decimal
from eth_abi import encode
from eth_utils import keccak
from gmx_python_sdk.scripts.v2.gmx_utils import create_hash_string, get_reader_contract, get_datastore_contract
from gmx_python_sdk.scripts.v2.utils.keys import IS_ORACLE_PROVIDER_ENABLED, MAX_ORACLE_REF_PRICE_DEVIATION_FACTOR
from rich.console import Console
from web3 import Web3

from eth_defi.gmx.config import GMXConfig
from tests.gmx.utils.helpers import deploy_custom_oracle_provider, deploy_custom_oracle, override_storage_slot, execute_order

ORDER_LIST = create_hash_string("ORDER_LIST")
print = Console().print


def emulate_keepers_for_positions(gmx_config: GMXConfig, initial_token_symbol: str, w3: Web3, recipient_address: str, initial_token_address: str, debug_logs: bool = False, swap_path: list = None):
    if debug_logs:
        erc20_abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function",
            },
            {
                "constant": False,
                "inputs": [
                    {"name": "_to", "type": "address"},
                    {"name": "_value", "type": "uint256"},
                ],
                "name": "transfer",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function",
            },
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function",
            },
            {
                "constant": True,
                "inputs": [],
                "name": "symbol",
                "outputs": [{"name": "", "type": "string"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function",
            },
        ]

        initial_token_contract = w3.eth.contract(address=initial_token_address, abi=erc20_abi)

        decimals = initial_token_contract.functions.decimals().call()
        symbol = initial_token_contract.functions.symbol().call()

        # Check initial balances
        balance = initial_token_contract.functions.balanceOf(recipient_address).call()
        print(f"Recipient {initial_token_symbol} balance: {Decimal(balance / 10 ** decimals)} {symbol}")

    deployed: tuple = (None, None)  # (None, None)
    if not deployed[0]:
        deployed_oracle_address = deploy_custom_oracle_provider(w3, recipient_address)
        custom_oracle_contract_address = deploy_custom_oracle(w3, recipient_address)
    else:
        deployed_oracle_address = deployed[0]
        custom_oracle_contract_address = deployed[1]

    try:
        config = gmx_config.get_write_config()
        # order_key = order.create_order_and_get_key()

        data_store = get_datastore_contract(config)

        # print(f"Order LIST: {ORDER_LIST.hex()}")

        assert ORDER_LIST.hex().removeprefix("0x") == "0x86f7cfd5d8f8404e5145c91bebb8484657420159dabd0753d6a59f3de3f7b8c1".removeprefix("0x"), "Order list mismatch"
        order_count = data_store.functions.getBytes32Count(ORDER_LIST).call()
        if order_count == 0:
            msg = "No orders found"
            raise Exception(msg)

        # Get the most recent order key
        order_key = data_store.functions.getBytes32ValuesAt(ORDER_LIST, order_count - 1, order_count).call()[0]
        print(f"Order created with key: {order_key.hex()}")

        # for key in keys:
        #     print(f"Key: {key.hex()}")

        reader = get_reader_contract(config)
        order_info = reader.functions.getOrder(data_store.address, order_key).call()
        print(f"Order: {order_info}")

        # data_store_owner = "0xE7BfFf2aB721264887230037940490351700a068"
        controller = "0xf5F30B10141E1F63FC11eD772931A8294a591996"
        oracle_provider = "0x5d6B84086DA6d4B0b6C0dF7E02f8a6A039226530"
        custom_oracle_provider = deployed_oracle_address  # "0xA1D67424a5122d83831A14Fa5cB9764Aeb15CD99"
        # NOTE: Somehow have to sign the oracle params by this bad boy
        oracle_signer = "0x0F711379095f2F0a6fdD1e8Fccd6eBA0833c1F1f"
        # set this value to true to pass the provider enabled check in contract
        # OrderHandler(0xfc9bc118fddb89ff6ff720840446d73478de4153)
        data_store.functions.setBool("0x1153e082323163af55b3003076402c9f890dda21455104e09a048bf53f1ab30c", True).transact({"from": controller})

        value = data_store.functions.getBool("0x1153e082323163af55b3003076402c9f890dda21455104e09a048bf53f1ab30c").call()
        print(f"Value: {value}")

        assert value, "Value should be true"

        # * Dynamically fetch the storage slot for the oracle provider
        # ? Get this value dynamically https://github.com/gmx-io/gmx-synthetics/blob/e8344b5086f67518ca8d33e88c6be0737f6ae4a4/contracts/data/Keys.sol#L938
        # ? Python ref: https://gist.github.com/Aviksaikat/cc69acb525695e44db340d64e9889f5e
        encoded_data = encode(["bytes32", "address"], [IS_ORACLE_PROVIDER_ENABLED, custom_oracle_provider])
        slot = f"0x{keccak(encoded_data).hex()}"

        # Enable the oracle provider
        data_store.functions.setBool(slot, True).transact({"from": controller})
        is_oracle_provider_enabled: bool = data_store.functions.getBool(slot).call()
        print(f"Value: {is_oracle_provider_enabled}")
        assert is_oracle_provider_enabled, "Value should be true"

        # TODO: This will change for various tokens apparently
        # pass the test `address expectedProvider = dataStore.getAddress(Keys.oracleProviderForTokenKey(token));` in Oracle.sol#L278
        address_slot: str = "0xee7ecf2be3f04718c696284b0fa544a16d84b94ffa10065f156555438db93488"
        data_store.functions.setAddress(address_slot, custom_oracle_provider).transact({"from": controller})

        new_address = data_store.functions.getAddress(address_slot).call()
        print(f"New address: {new_address}")
        # 0x0000000000000000000000005d6B84086DA6d4B0b6C0dF7E02f8a6A039226530
        assert new_address == custom_oracle_provider, "New address should be the oracle provider"

        # need this to be set to pass the `Oracle._validatePrices` check. Key taken from tenderly tx debugger
        address_key: str = "0xf986b0f912da0acadea6308636145bb2af568ddd07eb6c76b880b8f341fef306"  # "0xf986b0f912da0acadea6308636145bb2af568ddd07eb6c76b880b8f341fef306"

        data_store.functions.setAddress(address_key, custom_oracle_provider).transact({"from": controller})
        value = data_store.functions.getAddress(address_key).call()
        print(f"Value: {value}")
        assert value == custom_oracle_provider, "Value should be recipient address"

        # ? Set another key value to pass the test in `Oracle.sol` this time for ChainlinkDataStreamProvider
        address_key: str = "0x659d3e479f4f2d295ea225e3d439a6b9d6fbf14a5cd4689e7d007fbab44acb8a"
        data_store.functions.setAddress(address_key, custom_oracle_provider).transact({"from": controller})
        value = data_store.functions.getAddress(address_key).call()
        print(f"Value: {value}")
        assert value == custom_oracle_provider, "Value should be recipient address"

        # ? Set the `maxRefPriceDeviationFactor` to pass tests in `Oracle.sol`
        # price_deviation_factor_key: str = f"0x{MAX_ORACLE_REF_PRICE_DEVIATION_FACTOR.hex()}"
        # * set some big value to pass the test
        # large_value: int = 10021573904618365809021423188717
        # data_store.functions.setUint(price_deviation_factor_key, large_value).transact({"from": controller})
        # value = data_store.functions.getUint(price_deviation_factor_key).call()
        # print(f"Value: {value}")
        # assert value == large_value, f"Value should be {large_value}"

        # oracle_contract_address: str = "0x918b60ba71badfada72ef3a6c6f71d0c41d4785c"
        # token_b_max_value_slot: str = "0x636d2c90aa7802b40e3b1937e91c5450211eefbc7d3e39192aeb14ee03e3a958"
        # token_b_min_value_slot: str = "0x636d2c90aa7802b40e3b1937e91c5450211eefbc7d3e39192aeb14ee03e3a959"

        # TODO: Fix the pricing & add pricing for market tokens as well
        # oracle_prices = OraclePrices(chain=parameters["chain"]).get_recent_prices()

        # # Index token price setup
        # max_price: int = int(oracle_prices[TOKENS[INDEX_TOKEN_SYMBOL]]["maxPriceFull"])
        # min_price: int = int(oracle_prices[TOKENS[INDEX_TOKEN_SYMBOL]]["minPriceFull"])
        # max_res = override_storage_slot(oracle_contract_address, token_b_max_value_slot, max_price, w3)
        # min_res = override_storage_slot(oracle_contract_address, token_b_min_value_slot, min_price, w3)

        # # Short token price setup
        # max_price = int(oracle_prices[TOKENS[COLLATERAL_TOKEN_SYMBOL]]["maxPriceFull"])
        # min_price = int(oracle_prices[TOKENS[COLLATERAL_TOKEN_SYMBOL]]["minPriceFull"])
        # max_res = override_storage_slot(oracle_contract_address, token_b_max_value_slot, max_price, w3)
        # min_res = override_storage_slot(oracle_contract_address, token_b_min_value_slot, min_price, w3)

        # # Start/Initial token price setup
        # max_price = int(oracle_prices[TOKENS[INITIAL_TOKEN_SYMBOL]]["maxPriceFull"])
        # min_price = int(oracle_prices[TOKENS[INITIAL_TOKEN_SYMBOL]]["minPriceFull"])
        # max_res = override_storage_slot(oracle_contract_address, token_b_max_value_slot, max_price, w3)
        # min_res = override_storage_slot(oracle_contract_address, token_b_min_value_slot, min_price, w3)

        # print(f"Max price: {max_price}")
        # print(f"Min price: {min_price}")
        # print(f"Max res: {max_res}")
        # print(f"Min res: {min_res}")

        # print(f"Order key: {order_key.hex()}")
        overrides = {
            "simulate": False,
            "tokens": swap_path,
        }
        # Execute the order with oracle prices
        execute_order(
            config=config,
            connection=w3,
            order_key=order_key,
            deployed_oracle_address=custom_oracle_provider,
            overrides=overrides,
            is_swap=False,
        )

    except Exception as e:
        print(f"Error during swap process: {e!s}")
        raise e
