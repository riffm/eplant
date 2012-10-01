# -*- coding: utf-8 -*-

'''
eplant - easy etree planting.

'''

import types
import functools
from xml.etree import ElementTree
from xml.sax.saxutils import escape, quoteattr


def to_etree(struct, builder=None, **kw):
    '''Transforms to etree representation. Optionaly you can provide a custom
    builder object, for example `lxml.etree.TreeBuilder`'''
    builder = builder or ElementTree.TreeBuilder(**kw)
    _build_etree(struct, builder)
    return builder.close()


def _unpack(struct):
    assert isinstance(struct, (tuple, list)), struct
    assert len(struct) >= 1, struct
    assert isinstance(struct[0], basestring), struct[0]
    name, attrs, children = struct[0], {}, ()
    if len(struct) > 1:
        if isinstance(struct[1], dict):
            attrs, children = struct[1], struct[2:]
        else:
            children = struct[1:]
    return name, dict(attrs), children


def _build_etree(struct, builder):
    name, attrs, children = _unpack(struct)
    if isinstance(name, qname):
        name = name.to_etree()
    for k,v in attrs.items():
        if isinstance(k, qname):
            attrs.pop(k)
            k = k.to_etree()
        attrs[k] = v
    builder.start(name, attrs)
    if children:
        for child in children:
            if isinstance(child, basestring):
                builder.data(child)
            else:
                _build_etree(child, builder)
    builder.end(name)


def as_etree(**kw):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return to_etree(func(*args, **kwargs), **kw)
        return wrapper
    return decorator


class namespace(object):

    def __init__(self, uri, shortcut):
        self.uri = uri
        self.shortcut = shortcut

    def __call__(self, name, force=False):
        if isinstance(name, qname):
            if not force:
                return name
            name = name.name
        return qname(name, self.uri, self.shortcut)

    def __div__(self, name):
        return self(name)


class qname(unicode):

    def __new__(cls, name, uri=None, shortcut=None, **kwargs):
        assert uri and shortcut
        self = unicode.__new__(cls, u'%s:%s' % (shortcut, name), **kwargs)
        self.name = name
        self.uri = uri
        self.shortcut = shortcut
        return self

    def __repr__(self):
        return '<qname %s uri=%r>' % (unicode.__repr__(self), self.uri)

    def to_etree(self):
        return '{%s}%s' % (self.uri, self.name)


class _sample_property(object):

    def __init__(self, method, name=None):
        self.method = method
        self.__doc__ = method.__doc__
        self.name = name or method.__name__

    def __get__(self, inst, cls):
        if inst is None:
            return self
        result = self.method(inst)
        setattr(inst, self.name, result)
        return result

    def __call__(self, obj):
        return self.method(obj)


class Sample(object):
    '''
    XML sample class with ability to override parts in subclasses or by initial
    parameters. Must be used when function is not enougth.
    Every public method of instance became a cached attribute.
    '''

    class __metaclass__(type):
        def __new__(cls, cls_name, bases, attributes):
            self = type.__new__(cls, cls_name, bases, attributes)
            for name in dir(self):
                if name.startswith('_'):
                    continue
                value = getattr(self, name)
                if isinstance(value, types.MethodType):
                    new_value = value.im_func
                # already decorated attribute, assigned from another class
                elif isinstance(value, _sample_property) and name!= value.name:
                    new_value = value.method
                # classmethod, staticmethod and etc
                else:
                    continue
                setattr(self, name, _sample_property(new_value, name=name))
            return self

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def timestamp(dt):
    tz = dt.strftime('%z')
    if tz:
        tz = tz[:-2]+':'+tz[-2:]
    return dt.strftime('%Y-%m-%dT%H:%M:%S') + tz


def _escape_text(text):
    if isinstance(text, safe):
        return text
    return safe(escape(text))


def _escape_attr(attr):
    if isinstance(attr, safe):
        return attr
    return safe(quoteattr(attr))


class safe(str): pass


def _encode_tag(struct, indent=2, level=0):
    name, attrs, children = _unpack(struct)
    start_name = name
    if attrs:
        start_name = '%s %s' % (name, _encode_attrs(attrs))
    out = []
    write = out.append
    def do_indent(newline=True):
        if indent and newline:
            write('\n')
        write(' '*indent*level)
    do_indent(newline=level)
    if children:
        write('<%s>' % start_name)
        children_count = len(children)
        for i, child in enumerate(children):
            if isinstance(child, str):
                write(_escape_text(child))
            elif isinstance(child, unicode):
                write(_escape_text(child.encode('utf-8')))
            else:
                write(_encode_tag(child,
                                 indent=indent,
                                 level=level+1 if indent else 0))
                do_indent(newline=i==children_count-1)
        write('</%s>' % name)
    else:
        write('<%s/>' % start_name)
    return safe(''.join(out))


def encode(struct, indent=0):
    '''
    Optional independent implementation data -> str encoding.
    '''
    namespaces = NamespaceCollector().visit(struct).namespaces
    struct = update_tag(struct, attrs=namespaces)
    return '<?xml version="1.0"?>\n%s' % _encode_tag(struct, indent=indent)


def _encode_attrs(attrs):
    out = []
    write = out.append
    for k, v in sorted(attrs.items()):
        if isinstance(v, unicode):
            v = v.encode('utf-8')
        write(u'%s=%s' % (k, _escape_attr(str(v))))
    return ' '.join(out)


class Visitor(object):

    def visit(self, struct):
        self.general_visit(struct)
        return self

    def general_visit(self, struct):
        name, attrs, children = _unpack(struct)
        self.visit_tag(name, dict(attrs))
        for child in children:
            if isinstance(child, (list, tuple)):
                self.general_visit(child)
            else:
                self.visit_content(child)

    def visit_tag(self, name, attrs):
        pass

    def visit_content(self, content):
        pass


class NamespaceCollector(Visitor):

    def __init__(self):
        self.namespaces = {}

    def update_namespace(self, uri, shortcut):
        if shortcut in self.namespaces and uri != self.namespaces[shortcut]:
            raise ValueError('Namespace shortcut %r represents '
                             'different namespaces: %r, %r' % (
                             shortcut,
                             self.namespaces[shortcut],
                             uri))
        self.namespaces[shortcut] = uri

    def visit_tag(self, name, attrs):
        for n in [name]+attrs.keys():
            if isinstance(n, qname):
                self.update_namespace(n.uri, 'xmlns:'+n.shortcut)


def update_tag(tag, name=None, attrs=None, children=()):
    old_name, old_attrs, old_children = _unpack(tag)
    if name is None:
        name = old_name
    if attrs is None:
        attrs = dict(old_attrs)
    else:
        attrs = dict(old_attrs, **attrs)
    if not children:
        children = old_children
    return tuple([name, attrs]+list(children))


class EtreeModifier(object):

    def __init__(self, tree, namespaces=None):
        self.tree = tree
        self.namespaces = namespaces or {}

    def find_or_fail(self, path, namespaces=None):
        ns = dict(self.namespaces)
        ns.update(namespaces or {})
        node = self.tree.find(path, namespaces=ns)
        if node is None:
            raise ValueError('Path %r returns empty set' % path)
        return node

    def set_text(self, path, text, namespaces=None):
        self.find_or_fail(path, namespaces).text = text

    def get_text(self, path, namespaces=None):
        return self.find_or_fail(path, namespaces).text

    def set_attr(self, path, name, value, namespaces=None):
        self.find_or_fail(path, namespaces).set(name, value)

    def get_attr(self, path, name, namespaces=None):
        return self.find_or_fail(path, namespaces).get(name)


# vim: set sts=4 sw=4 et ai:
