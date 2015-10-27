# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import paypalrestsdk
import warnings
from django.conf import settings
from django.conf.urls import patterns, url
from django.core.serializers.json import DjangoJSONEncoder
from django.core.urlresolvers import resolve, reverse
from django.core.exceptions import ImproperlyConfigured
from django.http.response import HttpResponseRedirect, HttpResponseBadRequest
from django.utils.translation import ugettext_lazy as _
from cms.models import Page
from shop.models.cart import CartModel
from shop.models.order import BaseOrder, OrderModel, OrderPayment
from shop.payment.base import PaymentProvider
from django_fsm import transition


class PayPalPayment(PaymentProvider):
    """
    Provides a payment service for PayPal.
    """
    namespace = 'paypal-payment'

    def get_urls(self):
        urlpatterns = patterns('',
            url(r'^return', self.return_view, name='return'),
            url(r'^cancel$', self.cancel_view, name='cancel'),
        )
        return urlpatterns

    @classmethod
    def get_auth_token(cls):
        api = paypalrestsdk.set_config(
            mode=settings.SHOP_PAYPAL['MODE'],
            client_id=settings.SHOP_PAYPAL['CLIENT_ID'],
            client_secret=settings.SHOP_PAYPAL['CLIENT_SECRET'])
        auth_token_hash = api.get_token_hash()
        return auth_token_hash

    def get_payment_request(self, cart, request):
        """
        From the given request, redirect onto the checkout view, hosted by PayPal.
        """
        shop_ns = resolve(request.path).namespace
        return_url = reverse('{}:{}:return'.format(shop_ns, self.namespace))
        cancel_url = reverse('{}:{}:cancel'.format(shop_ns, self.namespace))
        cart = CartModel.objects.get_from_request(request)
        cart.update(request)  # to calculate the total
        auth_token_hash = self.get_auth_token()
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
                    'amount': {
                        'total': cart.total.as_decimal(),
                        'currency': cart.total.currency,
                    }
                }]
            }
        }
        config = json.dumps(payload, cls=DjangoJSONEncoder)
        success_handler = """
            function(r){
                console.log(r);
                $window.location.href=r.links.filter(function(e){
                    return e.rel==='approval_url';
                })[0].href;
            }""".replace('  ', '').replace('\n', '')
        error_handler = """
            function(r){
                console.error(r);
            }""".replace('  ', '').replace('\n', '')
        js_expression = '$http({0}).success({1}).error({2})'.format(config, success_handler, error_handler)
        return js_expression

    @classmethod
    def return_view(cls, request):
        try:
            payment_id = request.GET['paymentId']
            params = {'payer_id': request.GET['PayerID']}
        except KeyError as err:
            warnings.warn("Request for PayPal return_url is invalid: ", err.message)
            return HttpResponseBadRequest("Invalid Payment Request")
        try:
            cls.get_auth_token()
            payment = paypalrestsdk.Payment.find(payment_id)
            approved = payment.execute(params)
        except Exception as err:
            warnings.warn("An internal error occurred on the upstream server: ", err.message)
            return cls.cancel_view(request)
        if approved:
            cart = CartModel.objects.get_from_request(request)
            order = OrderModel.objects.create_from_cart(cart, request)
            order.add_paypal_payment(payment.to_dict())
            order.save()
            thank_you_url = OrderModel.objects.get_latest_url()
            return HttpResponseRedirect(thank_you_url)
        return cls.cancel_view(request)

    @classmethod
    def cancel_view(cls, request):
        try:
            cancel_url = Page.objects.public().get(reverse_id='cancel-payment').get_absolute_url()
        except Page.DoesNotExist:
            warnings.warn("Please add a page with an id `cancel-payment` to the CMS.")
            cancel_url = '/page__cancel-payment__not-found-in-cms'
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
        payment = OrderPayment(order=self, transaction_id=charge['id'], payment_method=PayPalPayment.namespace)
        transaction = charge['transactions'][0]
        assert payment.amount.currency == transaction['amount']['currency'].upper(), "Currency mismatch"
        payment.amount = payment.amount.__class__(transaction['amount']['total'])
        payment.save()

    def is_fully_paid(self):
        return super(OrderWorkflowMixin, self).is_fully_paid()

    @transition(field='status', source='paid_with_paypal', conditions=[is_fully_paid],
        custom=dict(admin=True, button_name=_("Acknowledge Payment")))
    def acknowledge_paypal_payment(self):
        self.acknowledge_payment()
