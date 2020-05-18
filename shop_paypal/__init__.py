"""
See PEP 386 (https://www.python.org/dev/peps/pep-0386/)

Release logic:
 1. Increase version number (change __version__ below).
 2. Check that all changes have been documented in CHANGELOG.md.
 3. git add shop_paypal/__init__.py CHANGELOG.md
 4. git commit -m 'Bump to {new version}'
 5. git tag {new version}
 6. git push --tags
 7. python setup.py sdist
 8. twine upload dist/djangoshop-paypal-{new version}.tar.gz
"""
__version__ = '1.2'
