from shop.utils import money

class Cart(object):
    def __init__(self):
        self.items = {}

    def total(self):
        s = 0
        for name, price in self.items.iteritems():
            s += price
        return money(s)

    def has(self, name):
        return self.items.has_key(name)
