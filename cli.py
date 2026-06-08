import argparse
import os
import sys

from dotenv import load_dotenv

from bot.client import BinanceClient
from bot.orders import place_order
from bot.logging_config import setup_logging


def main():
    parser = argparse.ArgumentParser(
        description="Binance Futures Testnet Trading Bot"
    )

    parser.add_argument(
        "--symbol",
        required=True
    )

    parser.add_argument(
        "--side",
        required=True
    )

    parser.add_argument(
        "--type",
        required=True
    )

    parser.add_argument(
        "--quantity",
        required=True,
        type=float
    )

    parser.add_argument(
        "--price",
        type=float
    )

    args = parser.parse_args()

    logger = setup_logging()

    load_dotenv()

    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")

    if not api_key or not api_secret:
        print(
            "Missing API credentials in .env",
            file=sys.stderr
        )
        sys.exit(1)

    client = BinanceClient(
        api_key,
        api_secret
    )

    try:

        response = place_order(
            client,
            logger,
            args.symbol,
            args.side,
            args.type,
            args.quantity,
            args.price
        )

        print("\nORDER SUCCESSFUL")
        print("-" * 40)

        print(f"Order ID     : {response.get('orderId')}")
        print(f"Status       : {response.get('status')}")
        print(f"Symbol       : {response.get('symbol')}")
        print(f"Side         : {response.get('side')}")
        print(f"Type         : {response.get('type')}")
        print(f"Executed Qty : {response.get('executedQty')}")
        print(f"Price        : {response.get('price')}")

    except Exception as e:

        print(
            f"ERROR: {e}",
            file=sys.stderr
        )

        sys.exit(1)


if __name__ == "__main__":
    main()