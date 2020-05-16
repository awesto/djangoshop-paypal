import paypalrestsdk
import warnings
from decimal import Decimal

from django.conf import settings
from django.conf.urls import url
from django.core.exceptions import ImproperlyConfigured
from django.http.response import HttpResponseRedirect, HttpResponseBadRequest
from django.urls import NoReverseMatch, resolve, reverse
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_str
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

    def build_absolute_url(self, request, endpoint):
        shop_ns = resolve(request.path).namespace
        url = reverse('{}:{}:{}'.format(shop_ns, self.namespace, endpoint))
        return request.build_absolute_uri(url)

    def create_payment_payload(self, cart, request):
        items = []
        for cart_item in cart.items.all():
            kwargs = dict(cart_item.extra, product_code=cart_item.product_code)
            product = cart_item.product.get_product_variant(**kwargs)
            price = product.get_price(request)
            items.append({
                'name': cart_item.product.product_name,
                'quantity': str(int(cart_item.quantity)),
                'price': str(price.as_decimal()),
                'currency': price.currency,
            })
        extra_costs = cart.total - cart.subtotal
        if extra_costs:
            items.append({
                'description': force_str(_("Additional charges")),
                'quantity': '1',
                'price': str(extra_costs.as_decimal()),
                'currency': extra_costs.currency,
            })
        payload = {
            'intent': 'sale',
            'payer': {
                'payment_method': 'paypal',
            },
            'redirect_urls': {
                'return_url': self.build_absolute_url(request, 'return'),
                'cancel_url': self.build_absolute_url(request, 'cancel'),
            },
            'transactions': [{
                'item_list': {
                    'items': items,
                },
                'amount': {
                    'total': str(cart.total.as_decimal()),
                    'currency': cart.total.currency,
                },
                'description': force_str(settings.SHOP_PAYPAL['PURCHASE_DESCRIPTION'])
            }],
        }
        return payload

    def get_payment_request(self, cart, request):
        """
        From the given request, redirect onto the checkout view, hosted by PayPal.
        """
        paypal_api = self.get_paypal_api()
        payload = self.create_payment_payload(cart, request)
        payment = paypalrestsdk.Payment(payload, api=paypal_api)
        if payment.create():
            redirect_url = [link for link in payment.links if link.rel == 'approval_url'][0].href
        else:
            warnings.warn(str(payment.error))
            redirect_url = payload['redirect_urls']['cancel_url']
        return '$window.location.href="{0}";'.format(redirect_url)

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
        super().__init__(*args, **kwargs)

    @transition(field='status', source=['created'], target='paid_with_paypal')
    def add_paypal_payment(self, charge):
        transaction = charge['transactions'][0]
        assert self.currency == transaction['amount']['currency'].upper(), "Currency mismatch"
        Money = MoneyMaker(self.currency)
        amount = Money(Decimal(transaction['amount']['total']))
        OrderPayment.objects.create(order=self, amount=amount, transaction_id=charge['id'], payment_method=PayPalPayment.namespace)

    def is_fully_paid(self):
        return super().is_fully_paid()

    @transition(field='status', source='paid_with_paypal', conditions=[is_fully_paid],
        custom=dict(admin=True, button_name=_("Acknowledge Payment")))
    def acknowledge_paypal_payment(self):
        self.acknowledge_payment()
