# REST based PayPal Payment Provider Integration for django-shop

This integrates the PayPal for django-shop version 0.9 and above.

## Installation

for django-shop version 0.10.x:

```
pip install djangoshop-paypal==0.1.4
```

for django-shop version 0.10.x:

```
pip install djangoshop-paypal==0.2.0
```

## Configuration

In ``settings.py`` of the merchant's project:

Add ``'shop_paypal'`` to ``INSTALLED_APPS``.

At [PayPal](https://paypal.com/) create a business account and apply for the vendor credentials.
For a testing account add them as:

```
SHOP_PAYPAL = {
    'API_ENDPOINT': 'https://api.sandbox.paypal.com',
    'MODE': 'sandbox',
    'CLIENT_ID': '<client-id-as-delivered-by-PayPal>',
    'CLIENT_SECRET': '<client-secret-as-delivered-by-PayPal>',
}
```

and for production:

```
SHOP_PAYPAL = {
    'API_ENDPOINT': 'https://api.paypal.com',
    'MODE': 'live',
    'CLIENT_ID': '<client-id-as-delivered-by-PayPal>',
    'CLIENT_SECRET': '<client-secret-as-delivered-by-PayPal>',
}
```

Add ``'shop_paypal.modifiers.PaymentModifier'`` to the list of ``SHOP_CART_MODIFIERS``.

Add ``'shop_paypal.payment.OrderWorkflowMixin'`` to the list of ``SHOP_ORDER_WORKFLOWS``.

When rendering the payment method form, "PayPal" shall appear in the list of possible payments.

Successful payments are redirected onto the CMS page with the ID ``shop-order-last``. If no such
CMS page exists, the URL which resolves to ``shop-order-last`` is returned.

If a payment was rejected by PayPal, **djangoshop-paypal** redirects onto the CMS page with the ID
``shop-cancel-payment``.  If no such CMS page exists, the URL which resolves to
``shop-cancel-payment`` is returned.
