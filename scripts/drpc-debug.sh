#!/bin/bash

set -e
set -u

echo "Call direct: ${JSON_RPC_ETHEREUM}"

curl -X POST -H "Content-Type: application/json" \
  --data '{
    "jsonrpc": "2.0",
    "method": "eth_call",
    "params": [
      {
        "to": "0xbEef047a543E45807105E51A8BBEFCc5950fcfBa",
        "data": "0x01e1d114"
      },
      "0x15296e6"
    ],
    "id": 1
  }' \
  $JSON_RPC_ETHEREUM

echo
echo "Call direct 2"
echo

curl -X POST -H "Content-Type: application/json" \
  --data '{
    "jsonrpc": "2.0",
    "method": "eth_call",
    "params": [
      {
        "to": "0xbEef047a543E45807105E51A8BBEFCc5950fcfBa",
        "data": "0x01e1d114"
      },
      "0x1233d06"
    ],
    "id": 1
  }' \
  $JSON_RPC_ETHEREUM


echo
echo "Call 19086598"
echo

# 0x399542e9000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000003000000000000000000000000000000000000000000000000000000000000006000000000000000000000000000000000000000000000000000000000000000e00000000000000000000000000000000000000000000000000000000000000160000000000000000000000000beef047a543e45807105e51a8bbefcc5950fcfba0000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000000401e1d11400000000000000000000000000000000000000000000000000000000000000000000000000000000beef047a543e45807105e51a8bbefcc5950fcfba0000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000000418160ddd00000000000000000000000000000000000000000000000000000000000000000000000000000000beef047a543e45807105e51a8bbefcc5950fcfba00000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000004ddca3f4300000000000000000000000000000000000000000000000000000000
# 19086598
curl -X POST -H "Content-Type: application/json" \
    --data '{
      "jsonrpc": "2.0",
      "method": "eth_call",
      "params": [
        {
          "to": "0xca11bde05977b3631167028862be2a173976ca11",
          "gas": "0xe8990a4600",
          "data": "0x399542e90000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000080000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000001800000000000000000000000000000000000000000000000000000000000000200000000000000000000000000b591d637cfd989a21e31873dbe64afa4bf18f1690000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000000401e1d11400000000000000000000000000000000000000000000000000000000000000000000000000000000b591d637cfd989a21e31873dbe64afa4bf18f1690000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000000418160ddd00000000000000000000000000000000000000000000000000000000000000000000000000000000872def0be6a91b212e67bbd56d37b6cc9513b7b70000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000000401e1d11400000000000000000000000000000000000000000000000000000000000000000000000000000000872def0be6a91b212e67bbd56d37b6cc9513b7b70000000000000000000000000000000000000000000000000000000000000040000000000000000000000000000000000000000000000000000000000000000418160ddd00000000000000000000000000000000000000000000000000000000"
        },
        "0x320e13"
      ],
      "id": 1
    }' \
    $JSON_RPC_MANTLE_2




    0xcA11bde05977b3631167028862bE2a173976CA11', 'data': '