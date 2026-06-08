from bot.validators import validate_order_input
from bot.client import BinanceAPIError


def place_order(
    client,
    logger,
    symbol,
    side,
    order_type,
    quantity,
    price=None
):
    try:

        validated = validate_order_input(
            symbol,
            side,
            order_type,
            quantity,
            price
        )

        logger.info(
            f"Order Request: {validated}"
        )

        response = client.place_order(
            validated["symbol"],
            validated["side"],
            validated["order_type"],
            validated["quantity"],
            validated["price"]
        )

        logger.info(
            f"Order Success | "
            f"OrderId={response.get('orderId')} | "
            f"Status={response.get('status')} | "
            f"ExecutedQty={response.get('executedQty')}"
        )

        return response

    except BinanceAPIError:
        logger.exception("Binance API Error")
        raise

    except Exception:
        logger.exception("Unexpected Error")
        raise