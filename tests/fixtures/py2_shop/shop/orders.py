from shop import payments
from shop.models import Cart

def checkout(cart):
    for i in xrange(3):
        try:
            return payments.charge(cart)
        except IOError, e:
            print "retry", i, e
