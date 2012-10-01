eplant
======

easy etree planting

You can plant an etree by subscribing it in terms of builtin python types.

    ('a tag name', [optional attrs dict], [optional children tags or text])

Some examples:

    ('tag', ) -> <tag/>
    ('tag', {'attr': 'value'}) -> <tag attr="value"/>
    ('tag', {'attr': 'value'}, 'text') -> <tag attr="value">text</tag>
    ('tag', ('child', )) -> <tag><child/></tag>
    ('tag',
      ('child', ),
      ('another_tag', 'text')) -> <tag><child/><another_tag>text</another_tag></tag>


---------
namespaces
---------

Of course xml without namespaces is unusable, so there is `eplant.namespace`
and `eplant.qname` primitives.

`eplant.namespace` — a class that represents a namespace and can be used to
emit tag and attribute(!) names. You can use `__call__` or `__div__` methods of
`eplant.namespace` object to get some name in that namespace.

Real world example::

    from eplant import namespace, as_etree
    se = namespace('http://schemas.xmlsoap.org/soap/envelope/', 'se')
    mhe = namespace('http://my.header.ext/', 'mhe')

    @as_etree()
    def Envelope(body):
        return \
        (se/'Envelope',
            (se/'Header',
                (mhe/'From', {se/'mustUnderstand': 'true'}, 'me'),
            (se/'Body', body))


--------
examples
--------

Simple usage::

    >>> from eplant import to_etree
    >>> from xml.etree.ElementTree import tostring
    >>> plant = ('SomeRootTag',
    ...             ('FirstChild', 'text'),
    ...             ('SecondChild', {'attr': 'value'}, 'text'))
    >>> tree = to_etree(plant)
    >>> tostring(tree)
    '<SomeRootTag><FirstChild>text</FirstChild><SecondChild attr="value">text</SecondChild></SomeRootTag>'

`as_etree` decorator factory example::

    >>> from eplant import as_etree
    >>> from xml.etree.ElementTree import tostring
    >>> @as_etree()
    ... def SomeRootTag():
    ...     return \
    ...     ('SomeRootTag',
    ...        ('FirstChild', 'text'),
    ...        ('SecondChild', {'attr': 'value'}, 'text'))
    >>> tostring(SomeRootTag())
    '<SomeRootTag><FirstChild>text</FirstChild><SecondChild attr="value">text</SecondChild></SomeRootTag>'

