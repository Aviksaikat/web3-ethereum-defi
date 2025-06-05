"""
Tests for GMXTrading with parametrized chain testing.

This test suite verifies the functionality of the GMXTrading class
when connected to different networks. The tests focus on creating
orders in debug mode without submitting actual transactions.
"""

from gmx_python_sdk.scripts.v2.order.create_decrease_order import DecreaseOrder
from gmx_python_sdk.scripts.v2.order.create_increase_order import IncreaseOrder
from gmx_python_sdk.scripts.v2.order.create_swap_order import SwapOrder
import pytest

from eth_defi.gmx.trading import GMXTrading
from eth_defi.gmx.utils import get_positions
from tests.gmx.utils.position_utils import emulate_keepers_for_positions
from tests.gmx.utils.swap_utils import emulate_keepers_for_swap, ORDER_LIST


# TODO: use to avoid race condition https://web3-ethereum-defi.readthedocs.io/api/core/_autosummary/eth_defi.trace.assert_transaction_success_with_explanation.html#eth_defi.trace.assert_transaction_success_with_explanation


@pytest.fixture()
def trading_manager(gmx_config_fork):
    """
    Create a GMXTrading instance for the current chain being tested.
    The wallet already has all tokens needed for testing through gmx_config_fork.
    """
    return GMXTrading(gmx_config_fork)


def test_initialization(chain_name, gmx_config):
    """
    Test that the trading module initializes correctly with chain-specific config.
    """
    trading = GMXTrading(gmx_config)
    assert trading.config == gmx_config
    assert trading.config.get_chain().lower() == chain_name.lower()


def test_open_position_long(chain_name, trading_manager, gmx_config_fork, usdc, reader_contract, data_store_contract, get_order_key):
    """
    Test opening a long position.

    This tests creating an IncreaseOrder for a long position.
    """
    # Select appropriate parameters based on the chain
    if chain_name == "arbitrum":
        market_symbol = "ETH"
        collateral_symbol = "USDC"
    # avalanche
    else:
        market_symbol = "AVAX"
        collateral_symbol = "USDC"

    # Get test wallet address
    wallet_address = gmx_config_fork.get_wallet_address()

    # Check initial balances
    initial_usdc_balance = usdc.contract.functions.balanceOf(wallet_address).call()

    # Create a long position with USDC as collateral
    # Using ACTUAL transaction (not debug mode) to test balance changes
    increase_order = trading_manager.open_position(
        market_symbol=market_symbol,
        collateral_symbol=collateral_symbol,
        start_token_symbol=collateral_symbol,
        is_long=True,
        size_delta_usd=100,
        leverage=2,
        slippage_percent=0.003,
        debug_mode=False,
        execution_buffer=2.2,
    )

    # Verify the order was created with the right type
    assert isinstance(increase_order, IncreaseOrder)

    # Verify key properties of the order
    assert hasattr(increase_order, "config")
    assert hasattr(increase_order, "market_key")
    assert hasattr(increase_order, "collateral_address")
    assert hasattr(increase_order, "index_token_address")
    assert hasattr(increase_order, "is_long")
    assert hasattr(increase_order, "size_delta")
    assert hasattr(increase_order, "initial_collateral_delta_amount")
    assert hasattr(increase_order, "slippage_percent")

    # Verify position direction
    assert increase_order.is_long is True

    # Verify the order has our debug flag
    assert hasattr(increase_order, "debug_mode")
    assert increase_order.debug_mode is False

    # Check final balances (USDC should decrease)
    final_usdc_balance = usdc.contract.functions.balanceOf(wallet_address).call()

    # Verify USDC was spent
    assert final_usdc_balance < initial_usdc_balance, "USDC balance should decrease after opening a long position"

    order_key = get_order_key
    order_info = reader_contract.functions.getOrder(data_store_contract.address, order_key).call()

    # Check if the order is opened for the given collateral
    assert usdc.address in order_info[0]


def test_open_position_short(chain_name, trading_manager, gmx_config_fork, usdc, get_order_key, data_store_contract, reader_contract):
    """
    Test opening a short position.

    This tests creating an IncreaseOrder for a short position.
    """
    # Select appropriate parameters based on the chain
    if chain_name == "arbitrum":
        market_symbol = "BTC"
    # avalanche
    else:
        market_symbol = "AVAX"

    # Get test wallet address
    wallet_address = gmx_config_fork.get_wallet_address()

    # Check initial balances
    initial_usdc_balance = usdc.contract.functions.balanceOf(wallet_address).call()

    # Create a short position with USDC as collateral
    increase_order = trading_manager.open_position(
        market_symbol=market_symbol,
        collateral_symbol="USDC",
        start_token_symbol="USDC",
        is_long=False,
        size_delta_usd=200,
        leverage=1.5,
        slippage_percent=0.003,
        debug_mode=False,
        execution_buffer=2.2,
    )

    # Verify the order was created with the right type
    assert isinstance(increase_order, IncreaseOrder)

    # Verify key properties
    assert hasattr(increase_order, "market_key")
    assert hasattr(increase_order, "size_delta")
    assert hasattr(increase_order, "initial_collateral_delta_amount")

    # Verify position direction
    assert increase_order.is_long is False

    # Verify debug mode
    assert increase_order.debug_mode is False

    # Check final balances (USDC should decrease)
    final_usdc_balance = usdc.contract.functions.balanceOf(wallet_address).call()

    # Verify USDC was spent
    assert final_usdc_balance < initial_usdc_balance, "USDC balance should decrease after opening a short position"

    order_key = get_order_key
    order_info = reader_contract.functions.getOrder(data_store_contract.address, order_key).call()

    # Check if the order is opened for the given collateral
    assert usdc.address in order_info[0]

    order_count = data_store_contract.functions.getBytes32Count(ORDER_LIST).call()
    order_key = data_store_contract.functions.getBytes32ValuesAt(ORDER_LIST, order_count - 1, order_count).call()[0]

    deposit = reader_contract.functions.getDeposit(data_store_contract.address, order_key).call()

    print(f"{deposit=}")


# TODO: can't use USDC->LINK swap for some reason. So use the start token as collateral token for this test
def test_open_position_high_leverage(chain_name, trading_manager, gmx_config_fork, wrapped_native_token, link, get_order_key, data_store_contract, reader_contract):
    """
    Test opening a position with high leverage.

    This tests creating an IncreaseOrder with higher leverage.
    """
    # The collateral & start tokens are kept the same intentionally bcz a swap will happen if they differ.
    # In order to make the swap successful we have to emulate the keepers for swap interaction. Why not avoid this?
    if chain_name == "arbitrum":
        market_symbol = "LINK"
        collateral_symbol = "LINK"
        start_token = "LINK"
        token_contract = link
    # avalanche
    else:
        market_symbol = "AVAX"
        collateral_symbol = "AVAX"
        start_token = "USDC"
        token_contract = wrapped_native_token

    # Get test wallet address
    wallet_address = gmx_config_fork.get_wallet_address()

    # Check initial balances
    initial_token_balance = token_contract.contract.functions.balanceOf(wallet_address).call()

    print(f"{initial_token_balance=}")

    # Create a long position with high leverage
    increase_order = trading_manager.open_position(
        market_symbol=market_symbol,
        collateral_symbol=collateral_symbol,
        start_token_symbol=start_token,
        is_long=False,
        size_delta_usd=100000,
        leverage=1,
        slippage_percent=0.03,
        debug_mode=False,
        execution_buffer=2.2,
    )

    # Verify the order was created with the right type
    assert isinstance(increase_order, IncreaseOrder)

    # Verify position setup
    assert increase_order.is_long is False
    assert increase_order.debug_mode is False

    # Check final balances (Token should decrease)
    final_token_balance = token_contract.contract.functions.balanceOf(wallet_address).call()

    # Verify token was spent
    # assert final_token_balance < initial_token_balance, f"{token_contract.symbol} balance should decrease after opening a high leverage position"

    positions = get_positions(gmx_config_fork.get_read_config(), wallet_address)

    emulate_keepers_for_positions(gmx_config_fork, start_token, gmx_config_fork.web3, wallet_address, link.address, swap_path=increase_order.swap_path)

    print(f"{positions=}")

    assert len(positions) == 1


def test_close_position(chain_name, trading_manager, gmx_config_fork, usdc, web3_fork):
    """
    Test closing a position.

    This test first creates a position, then closes it to ensure both operations work correctly.
    """
    # Select appropriate parameters based on the chain
    if chain_name == "arbitrum":
        market_symbol = "ETH"
    # avalanche
    else:
        market_symbol = "AVAX"

    # Get test wallet address
    wallet_address = gmx_config_fork.get_wallet_address()

    # First, create a position to close
    trading_manager.open_position(
        market_symbol=market_symbol,
        collateral_symbol="USDC",
        start_token_symbol="USDC",
        is_long=True,
        size_delta_usd=500,
        leverage=2,
        slippage_percent=0.003,
        debug_mode=False,
        execution_buffer=2.2,
    )

    # Small delay to allow the position to be processed
    web3_fork.provider.make_request("evm_increaseTime", [60])  # Advance time by 60 seconds
    web3_fork.provider.make_request("evm_mine", [])  # Mine a new block

    # Check USDC balance before closing position
    usdc_balance_before_close = usdc.contract.functions.balanceOf(wallet_address).call()

    # Close the position
    decrease_order = trading_manager.close_position(
        market_symbol=market_symbol,
        collateral_symbol="USDC",
        start_token_symbol="USDC",
        is_long=True,
        size_delta_usd=500,
        initial_collateral_delta=250,
        slippage_percent=0.003,
        debug_mode=False,
        execution_buffer=2.2,
    )  # Close full position  # Remove half of collateral

    # Verify the order was created with the right type
    assert isinstance(decrease_order, DecreaseOrder)

    # Verify key properties
    assert hasattr(decrease_order, "config")
    assert hasattr(decrease_order, "market_key")
    assert hasattr(decrease_order, "collateral_address")
    assert hasattr(decrease_order, "index_token_address")
    assert hasattr(decrease_order, "is_long")
    assert hasattr(decrease_order, "size_delta")
    assert hasattr(decrease_order, "initial_collateral_delta_amount")
    assert hasattr(decrease_order, "slippage_percent")

    # Verify the position being closed is long
    assert decrease_order.is_long is True

    # Verify debug mode
    assert decrease_order.debug_mode is False

    # Check USDC balance after closing position
    usdc_balance_after_close = usdc.contract.functions.balanceOf(wallet_address).call()

    # Verify USDC balance has increased after closing the position
    # Note: Due to fees, we might not get back the exact amount, but should be more than before
    assert usdc_balance_after_close > usdc_balance_before_close, "USDC balance should increase after closing a position"


def test_close_position_full_size(chain_name, trading_manager, gmx_config_fork, usdc, web3_fork):
    """
    Test closing a full position.

    This tests creating a DecreaseOrder for a full position.
    """
    # Select appropriate parameters based on the chain
    if chain_name == "arbitrum":
        market_symbol = "BTC"
        size_delta = 2000
        collateral_delta = 1333
    # avalanche
    else:
        market_symbol = "AVAX"
        size_delta = 200
        collateral_delta = 133
        collateral_symbol = "AVAX"

    # Get test wallet address
    wallet_address = gmx_config_fork.get_wallet_address()

    # First, create a position to close
    trading_manager.open_position(
        market_symbol=market_symbol,
        collateral_symbol="USDC",
        start_token_symbol="USDC",
        is_long=False,
        size_delta_usd=size_delta,
        leverage=1.5,
        slippage_percent=0.003,
        debug_mode=False,
        execution_buffer=2.2,
    )

    # Small delay to allow the position to be processed
    web3_fork.provider.make_request("evm_increaseTime", [60])  # Advance time by 60 seconds
    web3_fork.provider.make_request("evm_mine", [])  # Mine a new block

    # Check USDC balance before closing position
    usdc_balance_before_close = usdc.contract.functions.balanceOf(wallet_address).call()

    # Close a full short position
    decrease_order = trading_manager.close_position(
        market_symbol=market_symbol,
        collateral_symbol="USDC",
        start_token_symbol="USDC",
        is_long=False,
        size_delta_usd=size_delta,
        initial_collateral_delta=collateral_delta,
        slippage_percent=0.003,
        debug_mode=False,
        execution_buffer=2.2,
    )  # Full position size  # Full collateral

    # Verify the order was created with the right type
    assert isinstance(decrease_order, DecreaseOrder)

    # Verify the position being closed is short
    assert decrease_order.is_long is False

    # Verify debug mode
    assert decrease_order.debug_mode is False

    # Check USDC balance after closing position
    usdc_balance_after_close = usdc.contract.functions.balanceOf(wallet_address).call()

    # Verify USDC balance has increased after closing the position
    assert usdc_balance_after_close > usdc_balance_before_close, "USDC balance should increase after closing a full position"


def test_swap_tokens(chain_name, trading_manager, gmx_config_fork, arb, wsol, wallet_with_arb, wallet_with_native_token):
    """
    Test swapping tokens.

    This tests creating a SwapOrder.
    """
    start_token_symbol: str = "ARB"
    start_token_address = arb.contract.functions.address
    # Select appropriate parameters based on the chain
    if chain_name == "arbitrum":
        out_token_symbol = "SOL"
        out_token_address = wsol.contract.functions.address
    # avalanche
    else:
        # For https://github.com/gmx-io/gmx-synthetics/issues/164 skip the test for avalanche
        pytest.skip("Skipping swap_tokens for avalanche because of the known issue in the Reader contract")
        out_token_symbol = "GMX"

    # Get test wallet address
    wallet_address = gmx_config_fork.get_wallet_address()

    # Check initial balances
    initial_arb_balance = arb.contract.functions.balanceOf(wallet_address).call()

    # Swap USDC for chain-specific native token
    swap_order = trading_manager.swap_tokens(
        out_token_symbol=out_token_symbol,
        start_token_symbol=start_token_symbol,
        amount=50000.3785643,  # 50000 ARB tokens & fractions for fun
        slippage_percent=0.02,  # 0.2% slippage
        debug_mode=False,
        execution_buffer=2.5,  # this is needed to pass the gas usage
    )

    # Verify the order was created with the right type
    assert isinstance(swap_order, SwapOrder)

    # Verify key properties
    assert hasattr(swap_order, "config")
    assert hasattr(swap_order, "market_key")
    assert hasattr(swap_order, "start_token")
    assert hasattr(swap_order, "out_token")
    assert hasattr(swap_order, "initial_collateral_delta_amount")
    assert hasattr(swap_order, "slippage_percent")
    assert hasattr(swap_order, "swap_path")

    # Verify swap path exists
    assert hasattr(swap_order, "swap_path")

    # Verify debug mode
    assert swap_order.debug_mode is False

    # Check final balances
    final_arb_balance = arb.contract.functions.balanceOf(wallet_address).call()
    decimals = wsol.contract.functions.decimals().call()

    # Verify balances changed
    assert final_arb_balance < initial_arb_balance, "USDC balance should decrease after swap"

    emulate_keepers_for_swap(
        gmx_config_fork,
        initial_token_symbol=start_token_symbol,
        target_token_symbol=out_token_symbol,
        w3=gmx_config_fork.web3,
        recipient_address=wallet_address,
        initial_token_address=start_token_address,
        target_token_address=out_token_address,
    )

    output = wsol.contract.functions.balanceOf(wallet_address).call()

    # As of 21 May 2025, 50k ARB -> 122 SOL (Roughly). Keeping it at 100 just be safe.
    assert output // decimals >= 100
