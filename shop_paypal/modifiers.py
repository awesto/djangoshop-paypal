# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from datetime import date
from django.utils.translation import ugettext_lazy as _
from shop.modifiers.base import PaymentModifier as PaymentModifierBase
from .payment import PayPalPayment


class PaymentModifier(PaymentModifierBase):
    """
    Cart modifier which handles payment through PayPal.
    """
    identifier = PayPalPayment.namespace
    payment_provider = PayPalPayment()
    commision_percentage = None

    def get_choice(self):
        return (self.identifier, "PayPal")

    def is_disabled(self, cart):
        return cart.total == 0

    def add_extra_cart_row(self, cart, request):
        from decimal import Decimal
        from shop.rest.serializers import ExtraCartRow

        if not self.is_active(cart) or not self.commision_percentage:
            return
        amount = cart.subtotal * Decimal(self.commision_percentage / 100.0)
        instance = {'label': _("plus {}% handling fees").format(self.commision_percentage), 'amount': amount}
        cart.extra_rows[self.identifier] = ExtraCartRow(instance)
        cart.total += amount

    def update_render_context(self, context):
        super(PaymentModifier, self).update_render_context(context)
        context['payment_modifiers']['paypal_payment'] = True
