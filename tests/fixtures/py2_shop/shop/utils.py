import ConfigParser

def load(path):
    cfg = ConfigParser.ConfigParser()
    cfg.read(path)
    return cfg

def money(value):
    if isinstance(value, basestring):
        value = float(value)
    return "%.2f" % value
