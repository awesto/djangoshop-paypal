# Stripe Payment Provider Integration for django-shop

This integrates Stripe for django-shop version 0.3 and above.


## Installation

In ``settings.py`` add ``'shop_paypal'`` to ``INSTALLED_APPS``.

In ``settings.py`` add

```
SHOP_PAYPAL = {
    'API_ENDPOINT': 'https://api.sandbox.paypal.com',  # or 'https://api.paypal.com'
    'MODE': 'sandbox',  # 'sandbox' or 'live'
    'CLIENT_ID': '<client-id-as-delivered-by-PayPal>',
    'CLIENT_SECRET': '<client-secret-as-delivered-by-PayPal>',
}
```

In ``settings.py`` add ``'shop_paypal.payment.PaymentModifier'`` to ``SHOP_CART_MODIFIERS``.

In ``settings.py`` add ``'shop_paypal.payment.OrderWorkflowMixin'`` to ``SHOP_ORDER_WORKFLOWS``.
