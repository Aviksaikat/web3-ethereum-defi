"""Deploy Safe multisig wallets.

Safe source code:

- https://github.com/safe-global/safe-smart-account/blob/main/contracts/Safe.sol
"""
import logging

from eth_account.signers.local import LocalAccount
from eth_typing import HexAddress
from safe_eth.safe import Safe
from safe_eth.safe.safe import SafeV141
from web3 import Web3

from eth_defi.safe.safe_compat import create_safe_ethereum_client
from eth_defi.trace import assert_transaction_success_with_explanation

logger = logging.getLogger(__name__)


def deploy_safe(
    web3: Web3,
    deployer: LocalAccount,
    owners: list[HexAddress | str],
    threshold: int,
    master_copy_address = "0x41675C099F32341bf84BFc5382aF534df5C7461a",
) -> Safe:
    """Deploy a new Safe wallet.

    - Use version Safe v 1.4.1

    :param deployer:
        Must be LocalAccount due to Safe library limitations.

    :param master_copy_address:
        See Safe info.

        - https://help.safe.global/en/articles/40834-verify-safe-creation
        - https://basescan.org/address/0x41675C099F32341bf84BFc5382aF534df5C7461a
    """

    assert isinstance(deployer, LocalAccount), f"Safe can be only deployed using LocalAccount"
    for a in owners:
        assert type(a) == str and a.startswith("0x"), f"owners must be hex addresses, got {type(a)}"

    logger.info("Deploying safe.\nOwners: %s\nThreshold: %s", owners, threshold)
    ethereum_client = create_safe_ethereum_client(web3)

    owners = [Web3.to_checksum_address(a) for a in owners]
    master_copy_address = Web3.to_checksum_address(master_copy_address)

    safe_tx = SafeV141.create(
        ethereum_client,
        deployer,
        master_copy_address,
        owners,
        threshold,
    )
    contract_address = safe_tx.contract_address
    safe = SafeV141(contract_address, ethereum_client)

    # Check that we can read back Safe data
    retrieved_owners = safe.retrieve_owners()
    assert retrieved_owners == owners
    return safe


def add_new_safe_owners(
    web3: Web3,
    safe: Safe,
    deployer: LocalAccount,
    owners: list[HexAddress | str],
    threshold: int,
):
    """Update Safe owners and threshold list.

    - Safe cannot replace the existing owner list
    - Designed to create the owner list after a deployment.
    - The multisig must be in 1-of-1 deployer state

    .. note ::

        We cannot remove deployer account from the list, but it must be done by the new owners

    More info:

    - https://github.com/safe-global/safe-smart-account/blob/main/contracts/base/OwnerManager.sol#L56C14-L56C35
    """

    assert isinstance(safe, Safe), f"Not safe: {safe}"
    assert isinstance(deployer, LocalAccount), f"Safe can be only updated using deployer LocalAccount"

    logger.info(
        "Updating Safe owner list: %s with threshold %d",
        owners,
        threshold,
    )

    # Add all owners
    for owner in owners:
        assert isinstance(owner, str), f"Owner must be hex addresses, got {type(owner)}"
        assert owner.startswith("0x"), f"Owner must be hex addresses, got {type(owner)}"

        if owner == deployer.address:
            logger.info("Deployer: already exist on Safe cosigner")
            continue

        tx = safe.contract.functions.addOwnerWithThreshold(owner, 1).build_transaction(
            {"from": deployer.address, "gas": 0, "gasPrice": 0}
        )
        safe_tx = safe.build_multisig_tx(safe.address, 0, tx["data"])
        safe_tx.sign(deployer._private_key.hex())
        tx_hash, tx = safe_tx.execute(
            tx_sender_private_key=deployer._private_key.hex(),
        )
        assert_transaction_success_with_explanation(web3, tx_hash)

    # Change the threshold
    tx = safe.contract.functions.changeThreshold(threshold).build_transaction(
        {"from": deployer.address, "gas": 0, "gasPrice": 0}
    )
    safe_tx = safe.build_multisig_tx(safe.address, 0, tx["data"])
    safe_tx.sign(deployer._private_key.hex())
    tx_hash, tx = safe_tx.execute(
        tx_sender_private_key=deployer._private_key.hex(),
    )
    assert_transaction_success_with_explanation(web3, tx_hash)
