# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from datetime import date
from django.utils.translation import ugettext_lazy as _
from shop.modifiers.base import PaymentModifier as PaymentModifierBase
from .payment import PayPalPlusPayment


class PaymentModifier(PaymentModifierBase):
    """
    Cart modifier which handles payment through PayPal Plus.
    """
    identifier = PayPalPlusPayment.namespace
    payment_provider = PayPalPlusPayment()
    commision_percentage = None

    def get_choice(self):
        return (self.identifier, _("PayPal Plus"))

    def add_extra_cart_row(self, cart, request):
        from decimal import Decimal
        from shop.rest.serializers import ExtraCartRow

        if not self.is_active(cart) or not self.commision_percentage:
            return
        amount = cart.subtotal * Decimal(self.commision_percentage / 100.0)
        instance = {'label': _("+ {}% handling fees").format(self.commision_percentage), 'amount': amount}
        cart.extra_rows[self.identifier] = ExtraCartRow(instance)
        cart.total += amount

    def update_render_context(self, context):
        super(PaymentModifier, self).update_render_context(context)
        context['payment_modifiers']['paypalplus_payment'] = True
