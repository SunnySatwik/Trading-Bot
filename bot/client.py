import time
import hmac
import hashlib
import requests


class BinanceAPIError(Exception):
    pass


class BinanceClient:
    BASE_URL = "https://testnet.binancefuture.com"

    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret

    def _sign(self, params):
        query_string = "&".join(
            [f"{key}={value}" for key, value in params.items()]
        )

        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        return signature

    def place_order(
        self,
        symbol,
        side,
        order_type,
        quantity,
        price=None
    ):

        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
            "timestamp": int(time.time() * 1000)
        }

        if order_type == "LIMIT":
            params["price"] = price
            params["timeInForce"] = "GTC"

        params["signature"] = self._sign(params)

        headers = {
            "X-MBX-APIKEY": self.api_key
        }

        response = requests.post(
            f"{self.BASE_URL}/fapi/v1/order",
            params=params,
            headers=headers,
            timeout=10
        )

        if response.status_code != 200:
            raise BinanceAPIError(
                f"Binance Error: {response.text}"
            )

        return response.json()