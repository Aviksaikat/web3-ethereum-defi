import json
import os

from pathlib import Path
from gmx_python_sdk.scripts.v2.utils.exchange import execute_with_oracle_params
from gmx_python_sdk.scripts.v2.utils.hash_utils import hash_data
from cchecksum import to_checksum_address
from web3 import Web3
from gmx_python_sdk.scripts.v2.get.get_oracle_prices import OraclePrices

ABIS_PATH = os.path.dirname(os.path.abspath(__file__))


def set_opt_code(w3: Web3, bytecode=None, contract_address=None):
    # Use Anvil's RPC to set the contract's bytecode
    response = w3.provider.make_request("anvil_setCode", [contract_address, bytecode])

    # print(f"{response=}")

    # Verify the response from anvil. For anvil the result is None so don't need this check
    # if response.get("result"):
    #     print("Code successfully set via anvil")
    # else:
    #     print(f"Failed to set code: {response.get('error', {}).get('message', 'Unknown error')}")

    # Now verify that the code was actually set by retrieving it
    deployed_code = w3.eth.get_code(contract_address).hex()

    # Compare the deployed code with the mock bytecode
    if deployed_code == bytecode.hex():
        print("✅ Code verification successful: Deployed bytecode matches mock bytecode")
    else:
        print("❌ Code verification failed: Deployed bytecode does not match mock bytecode")
        print(f"Expected: {bytecode.hex()}")
        print(f"Actual: {deployed_code}")

        # You can also check if the length at least matches
        if len(deployed_code) == len(bytecode) or len(deployed_code) == len("0x" + bytecode.lstrip("0x")):
            print("Lengths match but content differs")
        else:
            print(f"Length mismatch - Expected: {len(bytecode)}, Got: {len(deployed_code)}")


def deploy_custom_oracle(w3: Web3, account) -> str:
    # /// Delpoy the `Oracle` contract here & then return the deployed bytecode
    # Check balance
    balance = w3.eth.get_balance(account)
    # print(f"Deployer balance: {w3.from_wei(balance, 'ether')} ETH")

    # Load contract ABI and bytecode
    artifacts_path = Path(f"{ABIS_PATH}/../mock_abis/Oracle.json")

    with open(artifacts_path) as f:
        contract_json = json.load(f)
        abi = contract_json["abi"]
        bytecode = contract_json["bytecode"]

    # Constructor arguments
    role_store = "0x3c3d99FD298f679DBC2CEcd132b4eC4d0F5e6e72"
    data_store = "0xFD70de6b91282D8017aA4E741e9Ae325CAb992d8"
    event_emitter = "0xC8ee91A54287DB53897056e12D9819156D3822Fb"
    sequender_uptime_feed = "0xFdB631F5EE196F0ed6FAa767959853A9F217697D"

    # Create contract factory
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)

    # Prepare transaction for contract deployment
    nonce = w3.eth.get_transaction_count(account)
    transaction = contract.constructor(role_store, data_store, event_emitter, sequender_uptime_feed).build_transaction(
        {
            "from": account,
            "nonce": nonce,
            "gas": 33000000,
            "gasPrice": w3.to_wei("50", "gwei"),
        }
    )

    # Send transaction
    tx_hash = w3.eth.send_transaction(transaction)
    # print(f"📝 Deployment tx hash: {tx_hash.hex()}")

    # Wait for transaction receipt
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    contract_address = tx_receipt.contractAddress
    print(f"🚀 Deployed GmOracleProvider to: {contract_address}")
    # print(f"   Gas used: {tx_receipt.gasUsed}")

    # Get deployed contract
    deployed_contract = w3.eth.contract(address=contract_address, abi=abi)

    # Fetch on-chain bytecode and print its size
    code = w3.eth.get_code(contract_address)
    # print(f"📦 On-chain code size (bytes): {len(code) // 2}")

    # List contract methods
    # methods = [func for func in deployed_contract.functions]
    # print("🔧 Available contract methods:")
    # for method in methods:
    #     print(f"   - {method}")

    # Verify constructor-stored state
    role_store_address = deployed_contract.functions.roleStore().call()
    data_store_address = deployed_contract.functions.dataStore().call()
    event_emitter_address = deployed_contract.functions.eventEmitter().call()

    # print(f"📌 roleStore address: {role_store_address}")
    # print(f"📌 dataStore address: {data_store_address}")
    # print(f"📌 eventEmitter address: {event_emitter_address}")
    bytecode = w3.eth.get_code(contract_address)

    original_oracle_contract = to_checksum_address("0x918b60ba71badfada72ef3a6c6f71d0c41d4785c")

    set_opt_code(w3, bytecode, original_oracle_contract)

    return contract_address


def deploy_custom_oracle_provider(w3: Web3, account) -> str:
    # Check balance
    balance = w3.eth.get_balance(account)
    # print(f"Deployer balance: {w3.from_wei(balance, 'ether')} ETH")

    # Load contract ABI and bytecode
    artifacts_path = Path(f"{ABIS_PATH}/../mock_abis/GmOracleProvider.json")
    with open(artifacts_path) as f:
        contract_json = json.load(f)
        abi = contract_json["abi"]
        bytecode = contract_json["bytecode"]

    # Constructor arguments
    role_store = "0x3c3d99FD298f679DBC2CEcd132b4eC4d0F5e6e72"
    data_store = "0xFD70de6b91282D8017aA4E741e9Ae325CAb992d8"
    oracle_store = "0xA8AF9B86fC47deAde1bc66B12673706615E2B011"

    # Create contract factory
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)

    # Prepare transaction for contract deployment
    nonce = w3.eth.get_transaction_count(account)
    transaction = contract.constructor(role_store, data_store, oracle_store).build_transaction(
        {
            "from": account,
            "nonce": nonce,
            "gas": 33000000,
            "gasPrice": w3.to_wei("50", "gwei"),
        }
    )

    # Send transaction
    tx_hash = w3.eth.send_transaction(transaction)
    # print(f"📝 Deployment tx hash: {tx_hash.hex()}")

    # Wait for transaction receipt
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    contract_address = tx_receipt.contractAddress
    print(f"🚀 Deployed GmOracleProvider to: {contract_address}")
    # print(f"   Gas used: {tx_receipt.gasUsed}")

    # Get deployed contract
    deployed_contract = w3.eth.contract(address=contract_address, abi=abi)

    # Fetch on-chain bytecode and print its size
    code = w3.eth.get_code(contract_address)
    # print(f"📦 On-chain code size (bytes): {len(code) // 2}")

    # List contract methods
    # methods = [func for func in deployed_contract.functions]
    # print("🔧 Available contract methods:")
    # for method in methods:
    #     print(f"   - {method}")

    # Verify constructor-stored state
    role_store_address = deployed_contract.functions.roleStore().call()
    data_store_address = deployed_contract.functions.dataStore().call()

    # print(f"📌 roleStore address: {role_store_address}")
    # print(f"📌 dataStore address: {data_store_address}")

    return contract_address


def override_storage_slot(
    contract_address: str,
    slot: str = "0x636d2c90aa7802b40e3b1937e91c5450211eefbc7d3e39192aeb14ee03e3a958",
    value: int = 171323136489203020000000,
    web3: Web3 = None,
) -> dict:
    """
    Override a storage slot in an Anvil fork.

    Args:
        contract_address: The address of the contract
        slot: The storage slot to override (as a hex string)
        value: The value to set (as an integer)
        web3: Web3 object
    """

    # Check connection
    if not web3.is_connected():
        raise Exception(f"Could not connect to Anvil node at {web3.provider.endpoint_uri}")

    # Format the value to a 32-byte hex string with '0x' prefix
    # First convert to hex without '0x'
    hex_value = hex(value)[2:]

    # Pad to 64 characters (32 bytes) and add '0x' prefix
    padded_hex_value = "0x" + hex_value.zfill(64)

    # Make sure the slot has '0x' prefix
    if not slot.startswith("0x"):
        slot = "0x" + slot

    # Ensure contract address has '0x' prefix and is checksummed
    if not contract_address.startswith("0x"):
        contract_address = "0x" + contract_address

    contract_address = web3.to_checksum_address(contract_address)

    # Call the anvil_setStorageAt RPC method
    result = web3.provider.make_request("anvil_setStorageAt", [contract_address, slot, padded_hex_value])

    # Check for errors
    if "error" in result:
        raise Exception(f"Error setting storage: {result['error']}")

    print(f"Successfully set storage at slot {slot} to {padded_hex_value}")

    storage_value = web3.eth.get_storage_at(contract_address, slot)
    # print(f"Verified value: {storage_value.hex()}")

    return result


def execute_order(config, connection, order_key, deployed_oracle_address, logger=None, overrides=None, is_swap: bool = True):
    """
    Execute an order with oracle prices

    Args:
        config: Configuration object containing chain and other settings
        connection: Web3 connection object
        order_key: Key of the order to execute
        deployed_oracle_address: Address of the deployed oracle contract
        initial_token_address: Address of the initial token
        target_token_address: Address of the target token
        logger: Logger object (optional)
        overrides: Optional parameters to override defaults
        is_swap: Optional parameter to decide which type of keeper action to trigger. Default is True which is for swaps

    Returns:
        Result of the execute_with_oracle_params call
    """
    if logger is None:
        import logging

        logger = logging.getLogger(__name__)

    if overrides is None:
        overrides = {}

    # Process override parameters
    gas_usage_label = overrides.get("gas_usage_label")
    oracle_block_number_offset = overrides.get("oracle_block_number_offset")

    # Set token addresses if not provided
    tokens = overrides.get(
        "tokens",
        [],
    )

    # Fetch real-time prices
    oracle_prices = OraclePrices(chain=config.chain).get_recent_prices()

    # Extract prices for the tokens
    default_min_prices = []
    default_max_prices = []

    for token in tokens:
        if token in oracle_prices:
            token_data = oracle_prices[token]

            # Get the base price values
            min_price = int(token_data["minPriceFull"])
            max_price = int(token_data["maxPriceFull"])

            default_min_prices.append(min_price)
            default_max_prices.append(max_price)
        else:
            # Fallback only if token not found in oracle prices
            logger.warning(f"Price for token {token} not found, using fallback price")
            default_min_prices.append(5000 * 10**18 if token == tokens[0] else 1 * 10**9)
            default_max_prices.append(5000 * 10**18 if token == tokens[0] else 1 * 10**9)

    # Set default parameters if not provided
    data_stream_tokens = overrides.get("data_stream_tokens", [])
    data_stream_data = overrides.get("data_stream_data", [])
    price_feed_tokens = overrides.get("price_feed_tokens", [])
    precisions = overrides.get("precisions", [1, 1])

    min_prices = default_min_prices
    max_prices = default_max_prices

    # Get oracle block number if not provided
    oracle_block_number = overrides.get("oracle_block_number")
    if not oracle_block_number:
        oracle_block_number = connection.eth.block_number

    # Apply oracle block number offset if provided
    if oracle_block_number_offset:
        if oracle_block_number_offset > 0:
            # Since we can't "mine" blocks in Python directly, this would be handled differently
            # in a real application. Here we just adjust the number.
            pass

        oracle_block_number += oracle_block_number_offset

    # Extract additional oracle parameters
    oracle_blocks = overrides.get("oracle_blocks")
    min_oracle_block_numbers = overrides.get("min_oracle_block_numbers")
    max_oracle_block_numbers = overrides.get("max_oracle_block_numbers")
    oracle_timestamps = overrides.get("oracle_timestamps")
    block_hashes = overrides.get("block_hashes")

    oracle_signer = overrides.get("oracle_signer", config.get_signer())

    # Build the parameters for execute_with_oracle_params
    params = {
        "key": order_key,
        "oracleBlockNumber": oracle_block_number,
        "tokens": tokens,
        "precisions": precisions,
        "minPrices": min_prices,
        "maxPrices": max_prices,
        "simulate": overrides.get("simulate", False),
        "gasUsageLabel": gas_usage_label,
        "oracleBlocks": oracle_blocks,
        "minOracleBlockNumbers": min_oracle_block_numbers,
        "maxOracleBlockNumbers": max_oracle_block_numbers,
        "oracleTimestamps": oracle_timestamps,
        "blockHashes": block_hashes,
        "dataStreamTokens": data_stream_tokens,
        "dataStreamData": data_stream_data,
        "priceFeedTokens": price_feed_tokens,
    }

    # Create a fixture-like object with necessary properties
    fixture = {
        "config": config,
        "web3Provider": connection,
        "chain": config.chain,
        "accounts": {"signers": [oracle_signer] * 7},
        "props": {
            "oracleSalt": hash_data(["uint256", "string"], [config.chain_id, "xget-oracle-v1"]),
            "signerIndexes": [0, 1, 2, 3, 4, 5, 6],  # Default signer indexes
        },
    }

    # Call execute_with_oracle_params with the built parameters
    return execute_with_oracle_params(fixture, params, config, deployed_oracle_address=deployed_oracle_address, is_swap=is_swap)
