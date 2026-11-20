from shop.orders import checkout
from shop.models import Cart

def handler(request):
    print "request", request
    return checkout(Cart())
