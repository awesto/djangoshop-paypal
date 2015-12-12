from setuptools import setup, find_packages
import os
import shop_paypal

CLASSIFIERS = [
    'Environment :: Web Environment',
    'Framework :: Django',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Topic :: Software Development :: Libraries :: Application Frameworks',
    'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
]

setup(
    author="Jacob Rief",
    author_email="jacob.rief@gmail.com",
    name='djangoshop-paypal',
    version=shop_paypal.__version__,
    description="PayPal Payment Provider Integration for django-shop",
    long_description=open(os.path.join(os.path.dirname(__file__), 'README.md')).read(),
    url='https://github.com/jrief/djangoshop-paypal',
    license='MIT License',
    platforms=['OS Independent'],
    classifiers=CLASSIFIERS,
    install_requires=[
        'Django>=1.8',
        'django-shop>=0.3.0',
        'paypalrestsdk>=1.11.0',
    ],
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
)
