def validate_order_input(symbol, side, order_type, quantity, price=None):
    if not symbol or not isinstance(symbol, str):
        raise ValueError("Symbol must be a non-empty string")

    symbol = symbol.upper()

    side = side.upper()
    if side not in ["BUY", "SELL"]:
        raise ValueError("Side must be BUY or SELL")

    order_type = order_type.upper()
    if order_type not in ["MARKET", "LIMIT"]:
        raise ValueError("Order type must be MARKET or LIMIT")

    try:
        quantity = float(quantity)
        if quantity <= 0:
            raise ValueError
    except ValueError:
        raise ValueError("Quantity must be a positive number")

    if order_type == "LIMIT":
        if price is None:
            raise ValueError("Price is required for LIMIT orders")

        try:
            price = float(price)
            if price <= 0:
                raise ValueError
        except ValueError:
            raise ValueError("Price must be a positive number")

    return {
        "symbol": symbol,
        "side": side,
        "order_type": order_type,
        "quantity": quantity,
        "price": price,
    }