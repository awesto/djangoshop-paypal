# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import paypalrestsdk
import warnings
from decimal import Decimal

from django.conf import settings
from django.conf.urls import url
from django.core.serializers.json import DjangoJSONEncoder
from django.core.urlresolvers import resolve, reverse
from django.core.exceptions import ImproperlyConfigured
from django.http.response import HttpResponseRedirect, HttpResponseBadRequest
from django.urls import NoReverseMatch
from django.utils.translation import ugettext_lazy as _
from cms.models import Page

from shop.models.cart import CartModel
from shop.models.order import BaseOrder, OrderModel, OrderPayment
from shop.money import MoneyMaker
from shop.payment.providers import PaymentProvider
from django_fsm import transition


class PayPalPayment(PaymentProvider):
    """
    Provides a payment service for PayPal.
    """
    namespace = 'paypal-payment'

    def get_urls(self):
        return [
            url(r'^return', self.return_view, name='return'),
            url(r'^cancel$', self.cancel_view, name='cancel'),
        ]

    @classmethod
    def get_paypal_api(cls):
        api = paypalrestsdk.Api({
            'mode': settings.SHOP_PAYPAL['MODE'],
            'client_id': settings.SHOP_PAYPAL['CLIENT_ID'],
            'client_secret': settings.SHOP_PAYPAL['CLIENT_SECRET'],
        })
        return api

    def get_payment_request(self, cart, request):
        """
        From the given request, redirect onto the checkout view, hosted by PayPal.
        """
        shop_ns = resolve(request.path).namespace
        return_url = reverse('{}:{}:return'.format(shop_ns, self.namespace))
        cancel_url = reverse('{}:{}:cancel'.format(shop_ns, self.namespace))
        paypal_api = self.get_paypal_api()
        auth_token_hash = paypal_api.get_token_hash()
        items = []
        for cart_item in cart.items.all():
            items.append({
                'name': cart_item.product.product_name,
                'quantity': str(int(cart_item.quantity)),
                'price': str(cart_item.product.unit_price.as_decimal()),
                'currency': cart_item.product.unit_price.currency,
            })
        payload = {
            'url': '{API_ENDPOINT}/v1/payments/payment'.format(**settings.SHOP_PAYPAL),
            'method': 'POST',
            'headers': {
                'Content-Type': 'application/json',
                'Authorization': '{token_type} {access_token}'.format(**auth_token_hash),
            },
            'data': {
                'intent': 'sale',
                'redirect_urls': {
                    'return_url': request.build_absolute_uri(return_url),
                    'cancel_url': request.build_absolute_uri(cancel_url),
                },
                'payer': {
                    'payment_method': 'paypal',
                },
                'transactions': [{
                    'item_list': {
                        'items': items,
                    },
                    'amount': {
                        'total': str(cart.total.as_decimal()),
                        'currency': cart.total.currency,
                    },
                    'description': settings.SHOP_PAYPAL['PURCHASE_DESCRIPTION']
                }]
            }
        }
        config = json.dumps(payload, cls=DjangoJSONEncoder)
        success_handler = """
            function successCallback(r) {
                console.log(r);
                $window.location.href=r.data.links.filter(function(e){
                    return e.rel==='approval_url';
                })[0].href;
            }""".replace('  ', '').replace('\n', '')
        error_handler = """
            function errorCallback(r) {
                console.error(r);
            }""".replace('  ', '').replace('\n', '')
        js_expression = '$http({0}).then({1},{2})'.format(config, success_handler, error_handler)
        return js_expression

    @classmethod
    def return_view(cls, request):
        try:
            payment_id = request.GET['paymentId']
            params = {'payer_id': request.GET['PayerID']}
        except KeyError as err:
            warnings.warn("Request for PayPal return_url is invalid: {}".format(err.message))
            return HttpResponseBadRequest("Invalid Payment Request")
        try:
            paypal_api = cls.get_paypal_api()
            payment = paypalrestsdk.Payment.find(payment_id, api=paypal_api)
            approved = payment.execute(params)
        except Exception as err:
            warnings.warn("An internal error occurred on the upstream server: {}".format(err))
            return cls.cancel_view(request)

        if approved:
            cart = CartModel.objects.get_from_request(request)
            order = OrderModel.objects.create_from_cart(cart, request)
            order.populate_from_cart(cart, request)
            order.add_paypal_payment(payment.to_dict())
            order.save(with_notification=True)
            return HttpResponseRedirect(order.get_absolute_url())
        return cls.cancel_view(request)

    @classmethod
    def cancel_view(cls, request):
        try:
            cancel_url = Page.objects.public().get(reverse_id='shop-cancel-payment').get_absolute_url()
        except Page.DoesNotExist:
            try:
                cancel_url = reverse('shop-cancel-payment')
            except NoReverseMatch:
                warnings.warn("Please add a page with an id `cancel-payment` to the CMS.")
                cancel_url = '/page__shop-cancel-payment__not-found-in-cms'
        return HttpResponseRedirect(cancel_url)


class OrderWorkflowMixin(object):
    TRANSITION_TARGETS = {
        'paid_with_paypal': _("Paid with PayPal"),
    }

    def __init__(self, *args, **kwargs):
        if not isinstance(self, BaseOrder):
            raise ImproperlyConfigured('OrderWorkflowMixin is not of type BaseOrder')
        super(OrderWorkflowMixin, self).__init__(*args, **kwargs)

    @transition(field='status', source=['created'], target='paid_with_paypal')
    def add_paypal_payment(self, charge):
        transaction = charge['transactions'][0]
        assert self.currency == transaction['amount']['currency'].upper(), "Currency mismatch"
        Money = MoneyMaker(self.currency)
        amount = Money(Decimal(transaction['amount']['total']))
        OrderPayment.objects.create(order=self, amount=amount, transaction_id=charge['id'], payment_method=PayPalPayment.namespace)

    def is_fully_paid(self):
        return super(OrderWorkflowMixin, self).is_fully_paid()

    @transition(field='status', source='paid_with_paypal', conditions=[is_fully_paid],
        custom=dict(admin=True, button_name=_("Acknowledge Payment")))
    def acknowledge_paypal_payment(self):
        self.acknowledge_payment()
