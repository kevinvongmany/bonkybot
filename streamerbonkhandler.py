import asyncio
import json
import websockets

ACTIONS = [
    {
      "variable": "pull_ghost",
      "redeem_id": "2c6c5e10-d1d0-421d-81e2-61625b240785",
      "bits": 15
    },
    {
      "variable": "class_ability",
      "redeem_id": "d6f84886-b1e4-4fb4-bd5d-1ef65bfd79ca",
      "bits": 20
    },
    {
      "variable": "powered_melee",
      "redeem_id": "b07b2dc4-4354-4262-b9b5-7a51111d92a0",
      "bits": 25
    },
    {
      "variable": "grenade",
      "redeem_id": "c712353b-7bca-45d9-b1f3-3b30b6fb835b",
      "bits": 30
    },
    {
      "variable": "jump_and_ability",
      "redeem_id": "4f736bed-5a76-4862-ac55-7ca2ae2d871a",
      "bits": 45
    },
    {
      "variable": "turn_around",
      "redeem_id": "b229fcde-81ed-4a60-8e86-9a056cf4efa8",
      "bits": 50
    },
    {
      "variable": "open_inventory",
      "redeem_id": "a620d39a-b0bf-4988-bd12-a4be0b1d5327",
      "bits": 55
    },
    {
      "variable": "jumpscare",
      "redeem_id": "6c1e4401-fcd3-48b0-b949-7cf71631d701",
      "bits": 60
    },
    {
      "variable": "look_down",
      "redeem_id": "09a3d545-557b-44ed-9b39-c750500dd8e2",
      "bits": 75
    },
    {
      "variable": "super",
      "redeem_id": "9f11096b-06a7-4cf8-bb03-db9e756fa441",
      "bits": 100
    },
    {
      "variable": "transcendence",
      "redeem_id": "62700a0b-be51-48b6-abc3-9930f1937e12",
      "bits": 130
    },
    {
      "variable": "hold_forward",
      "redeem_id": "5565817a-59dd-4d45-957e-402f207e90f8",
      "bits": 150
    },
    {
      "variable": "dump_heavy",
      "redeem_id": "614e54df-97b4-4b7e-a9dc-57294bf0b61f",
      "bits": 200
    },
    {
      "variable": "dance_party",
      "redeem_id": "603b33de-96cf-4515-8bc4-3b70674d42bd",
      "bits": 250
    },
    {
      "variable": "all_abilities",
      "redeem_id": "ea1bd7df-5797-45f6-b602-a0a161e629ca",
      "bits": 300,
      "gifted_subs": 1
    },
    {
      "variable": "dump_kinetic",
      "redeem_id": "4b9c68eb-5757-4707-9518-4e942f8528d0"
    },
    {
      "variable": "random_loadout",
      "redeem_id": "4db82d4e-1c36-4ade-a126-02e7c341a19a"
    },
    {
      "variable": "alt_f4",
      "redeem_id": "6fa376e2-0844-4f16-b923-80cf80612c6d",
      "bits": 5000,
      "gifted_subs": 10
    }
  ]

async def send_ws_message(message):
    uri = "wss://l0axmgjep7.execute-api.ap-southeast-2.amazonaws.com/beta"

    message = {
        "action": "sendmessage",
        "message": message
    }

    async with websockets.connect(uri) as websocket:
        # Send the message as a JSON string
        await websocket.send(json.dumps(message))
        print(f"Sent: {message}")

        # Optionally receive a reply
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=3)
            print("Received:", response)
        except asyncio.TimeoutError:
            print("No reply received (timeout or no server response)")

def main():
    asyncio.run(send_ws_message("dance_party"))


if __name__ == "__main__":
    main()

