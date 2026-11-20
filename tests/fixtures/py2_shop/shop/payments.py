import urllib2
from shop import orders

def charge(cart):
    data = urllib2.urlopen("https://pay.example.com").read()
    return unicode(data)

def refund(order_id):
    return orders.checkout(None)
