# -*- coding: utf-8 -*-

'''
eplant - easy etree planting.

Example:

    >>> from eplant import to_etree
    >>> from xml.etree.ElementTree import tostring
    >>> plant = ('SomeRootTag',
    ...             ('FirstChild', 'text'),
    ...             ('SecondChild', {'attr': 'value'}, 'text'))
    >>> tree = to_etree(plant)
    >>> tostring(tree)
    '<SomeRootTag><FirstChild>text</FirstChild><SecondChild attr="value">text</SecondChild></SomeRootTag>'
    >>> from xml.etree.ElementTree import tostring
    >>> def SomeRootTag():
    ...     return \
    ...     ('SomeRootTag',
    ...        ('FirstChild', 'text'),
    ...        ('SecondChild', {'attr': 'value'}, 'text'))
    >>> tostring(to_etree(SomeRootTag()))
    '<SomeRootTag><FirstChild>text</FirstChild><SecondChild attr="value">text</SecondChild></SomeRootTag>'
'''

import types
import functools
try:
    from xml.etree import cElementTree as ElementTree
except ImportError:
    from xml.etree import ElementTree
from xml.sax.saxutils import escape, quoteattr


def is_eplant_node(obj):
    return isinstance(obj, (tuple, list)) and \
           len(obj) >= 1 and \
           isinstance(obj[0], basestring)


class namespace(object):

    def __init__(self, uri, prefix):
        self.uri = uri
        self.prefix = prefix

    def __call__(self, name, force=False):
        if isinstance(name, qname):
            if not force:
                return name
            name = name.name
        return qname(name, self.uri, self.prefix)

    def __div__(self, name):
        return self(name)

    __getattr__ = __div__


class qname(unicode):

    def __new__(cls, name, uri='', prefix=None, **kwargs):
        self = unicode.__new__(cls,
                               u'%s:%s' % (prefix, name) if uri else name,
                               **kwargs)
        self.name = name
        self.uri = uri
        self.prefix = prefix
        return self

    def __repr__(self):
        return '<qname %s uri=%r>' % (unicode.__repr__(self), self.uri)

    def to_etree(self):
        return '{%s}%s' % (self.uri, self.name)


def _unpack(struct):
    length = len(struct)
    name, attrs, children = struct[0], {}, ()
    if len(struct) > 1:
        if isinstance(struct[1], dict):
            attrs, children = struct[1], struct[2:]
        else:
            children = struct[1:]
    return name, dict(attrs), children


identity = lambda i,v: v
_type_converters = {
    type(None): lambda i,v: u'',
    str: lambda i,v: v.decode('utf-8'),
    unicode: identity,
    int: lambda i,v: unicode(v),
    float: lambda i,v: unicode(v),
    bool: lambda i,v: unicode(v).lower(),
    qname: lambda i,v: i.QName(v.to_etree()),
}


def to_etree(struct, impl=ElementTree, converters=None, _level=0):
    '''Transforms to etree representation. Optionaly you can provide a custom
    `ElementTree` implementation module, for example `lxml.etree`
    converters - `dict[type:callable(impl, value)->unicode]`'''
    if not _level:
        converters = dict(_type_converters, **(converters or {}))
    if not is_eplant_node(struct):
        raise ValueError('Not an eplant structure')
    name, attrs, children = _unpack(struct)
    if isinstance(name, qname):
        name = impl.QName(name.to_etree())
    for k,v in attrs.items():
        if isinstance(k, qname):
            attrs.pop(k)
            k = k.to_etree()
        if isinstance(v, qname):
            v = impl.QName(v.to_etree())
        attrs[k] = v
    node = impl.Element(name, attrs)
    content = None
    last_child = None
    for child in children:
        if is_eplant_node(child):
            if content:
                if last_child is not None:
                    last_child.tail = content
                else:
                    node.text = content
                content = None
            last_child = to_etree(child, impl, converters, _level+1)
            node.append(last_child)
            continue
        match = False
        for t in type(child).__mro__:
            #Note: this special hack is `xml.etree.ElementTree` related
            if t is qname and impl is ElementTree:
                raise ValueError('xml.etree.ElementTree does not support '
                                 '`Qname` as tag content: %r' % node)
            if t in converters:
                value = converters[t](impl, child)
                content = value if content is None else content + value
                match = True
                break
        if not match:
            raise ValueError('Unknown type %r' % child)
    if content is not None:
        if last_child is not None:
            last_child.tail = content
        else:
            node.text = content
    return node


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

    def update_namespace(self, uri, prefix):
        if prefix in self.namespaces and uri != self.namespaces[prefix]:
            raise ValueError('Namespace prefix %r represents '
                             'different namespaces: %r, %r' % (
                             prefix,
                             self.namespaces[prefix],
                             uri))
        self.namespaces[prefix] = uri

    def visit_tag(self, name, attrs):
        for n in [name]+attrs.keys():
            if isinstance(n, qname):
                self.update_namespace(n.uri, 'xmlns:'+n.prefix)


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

    def __getattr__(self, name):
        return getattr(self.tree, name)


# vim: set sts=4 sw=4 et ai:
