#!/usr/bin/env python
from setuptools import setup, find_packages
import shop_paypal

with open('README.md', 'r') as fh:
    long_description = fh.read()

CLASSIFIERS = [
    'Environment :: Web Environment',
    'Framework :: Django',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Framework :: Django',
    'Framework :: Django :: 2.1',
    'Framework :: Django :: 2.2',
    'Framework :: Django :: 3.0',
    'Topic :: Software Development :: Libraries :: Application Frameworks',
    'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
]

setup(
    author="Jacob Rief",
    author_email="jacob.rief@gmail.com",
    name='djangoshop-paypal',
    version=shop_paypal.__version__,
    description="PayPal Payment Provider Integration for django-shop",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/jrief/djangoshop-paypal',
    license='MIT License',
    platforms=['OS Independent'],
    classifiers=CLASSIFIERS,
    install_requires=[
        'paypalrestsdk>=1.13.0',
        'requests>=2.14.1',
    ],
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
)
