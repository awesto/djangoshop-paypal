# REST based PayPal Payment Provider Integration for django-shop

This integrates PayPal for django-shop version 1.0 and above.

## Installation

for django-shop version 1.2.x:

```
pip install djangoshop-paypal<1.3
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
    'CLIENT_ID': '<client-id-as-provided-by-PayPal>',
    'CLIENT_SECRET': '<client-secret-as-provided-by-PayPal>',
    'PURCHASE_DESCRIPTION': "Thanks for purchasing at My Shop",
}
```

and for production:

```
SHOP_PAYPAL = {
    'API_ENDPOINT': 'https://api.paypal.com',
    'MODE': 'live',
    'CLIENT_ID': '<client-id-as-provided-by-PayPal>',
    'CLIENT_SECRET': '<client-secret-as-provided-by-PayPal>',
    'PURCHASE_DESCRIPTION': "Thanks for purchasing at My Shop",
}
```

Add ``'shop_paypal.modifiers.PaymentModifier'`` to the list of ``SHOP_CART_MODIFIERS``.

Add ``'shop_paypal.payment.OrderWorkflowMixin'`` to the list of ``SHOP_ORDER_WORKFLOWS``.

When rendering the payment method form, "PayPal" shall appear in the list of possible payments.

Successful payments are redirected onto the just created order detail page.

If a payment was rejected by PayPal, **djangoshop-paypal** redirects onto the CMS page with the ID
``shop-cancel-payment``, so make sure that such a page exists.


