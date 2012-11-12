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
emit tag and attribute names. You can use `__call__` or `__getattr__` methods of
`eplant.namespace` object to get some name in that namespace.

Real world example::

    from eplant import namespace, to_etree
    se = namespace('http://schemas.xmlsoap.org/soap/envelope/', 'se')
    mhe = namespace('http://my.header.ext/', 'mhe')

    def Envelope(who, body):
        return to_etree(
            (se.Envelope,
                (se.Header,
                    (mhe.From, {se.mustUnderstand: True}, who)),
                (se.Body, body))
        )

    from xml.etree.ElementTree import tostring
    print tostring(Envelope('me', 'hello'))


    $ python example.py
    <ns0:Envelope xmlns:ns0="http://schemas.xmlsoap.org/soap/envelope/"xmlns:ns1="http://my.header.ext/"><ns0:Header><ns1:From ns0:mustUnderstand="true">me</ns1:From></ns0:Header><ns0:Body>hello</ns0:Body></ns0:Envelope>
