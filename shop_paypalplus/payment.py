# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import paypalrestsdk
import warnings
from django.conf import settings
from django.conf.urls import patterns, url
from django.core.cache import cache
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


class PayPalPlusPayment(PaymentProvider):
    """
    Provides a payment service for PayPalPlus.
    """
    namespace = 'paypalplus-payment'
    cache_key = 'paypal-auth_token'

    def get_urls(self):
        urlpatterns = patterns('',
            url(r'^return', self.return_view, name='return'),
            url(r'^cancel$', self.cancel_view, name='cancel'),
        )
        return urlpatterns

    @classmethod
    def get_auth_token(cls):
        auth_token_hash = cache.get(cls.cache_key)
        if auth_token_hash is None:
            api = paypalrestsdk.set_config(
                mode=settings.SHOP_PAYPALPLUS['MODE'],
                client_id=settings.SHOP_PAYPALPLUS['CLIENT_ID'],
                client_secret=settings.SHOP_PAYPALPLUS['CLIENT_SECRET'])
            auth_token_hash = api.get_token_hash()
            expires_in = auth_token_hash.pop('expires_in') - 30
            cache.set(cls.cache_key, auth_token_hash, expires_in)
        else:
            paypalrestsdk.set_config(auth_token_hash)
        print auth_token_hash
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
            'url': '{API_ENDPOINT}/v1/payments/payment'.format(**settings.SHOP_PAYPALPLUS),
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
                        'currency': cart.total.get_currency(),
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
        print js_expression
        return js_expression

    @classmethod
    def return_view(cls, request):
        try:
            params = {'paymentId': request.GET['paymentId'], 'PayerID': request.GET['PayerID']}
        except KeyError as err:
            warnings.warn("Request for PayPal return_url is invalid: ", err.message)
            return HttpResponseBadRequest("Invalid Payment Request")
        cart = CartModel.objects.get_from_request(request)
        order = OrderModel.objects.create_from_cart(cart, request)
        # paymentId=PAY-6RV70583SB702805EKEYSZ6Y&token=EC-60U79048BN7719609&PayerID=7E7MGXCWTTKK2
        cls.get_auth_token()
        payment = paypalrestsdk.Payment.find(params['paymentId'])
        response = payment.execute(params['PayerID'])
        if response['state'] == 'approved':
            order.add_charge(response)
        order.save()
        thank_you_url = OrderModel.objects.get_latest_url()
        return HttpResponseRedirect(thank_you_url)

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
    def add_charge(self, response):
        payment = OrderPayment(order=self, transaction_id=response['id'], payment_method=PayPalPlusPayment.namespace)
        assert payment.amount.get_currency() == response['transactions']['amount']['currency'].upper(), "Currency mismatch"
        payment.amount = response['transactions']['amount']['total']
        payment.save()
