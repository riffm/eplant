# -*- coding: utf-8 -*-

import unittest
import datetime
from xml.etree import ElementTree
from eplant import (
        _encode_tag, Sample, to_etree, namespace, qname, timestamp,
        NamespaceCollector, EtreeModifier, encode)


has_lxml = False
try:
    from lxml import etree
except ImportError:
    pass
else:
    has_lxml = True




class Tests(unittest.TestCase):

    def test_sample_attr_access(self):
        class BaseSample(Sample):
            def tag(self):
                return ('tag',)
        s = BaseSample()
        tag = s.tag
        self.assertEqual(tag, ('tag',))
        self.assertEqual(s.tag, ('tag',))

    def test_attr_as_dependency(self):
        class BaseSample(Sample):
            def tag(self):
                return ('tag', self.tag2)
            def tag2(self):
                return ('tag2',)
        s = BaseSample()
        tag = s.tag
        self.assertEqual(tag, ('tag', ('tag2',)))
        self.assertEqual(s.tag2, ('tag2',))

    def test_encode_a_tag(self):
        self.assertEqual(_encode_tag(('tag',)), '<tag/>')

    def test_encode_a_tag_with_attrs(self):
        self.assertEqual(_encode_tag(('tag', {'a':1, 'b':2})),
                         '<tag a="1" b="2"/>')

    def test_encode_a_tag_with_str_data(self):
        self.assertEqual(_encode_tag(('tag', 'text')), '<tag>text</tag>')

    def test_encode_a_tag_with_unicode_data(self):
        self.assertEqual(_encode_tag(('tag', u'текст')),
                        u'<tag>текст</tag>'.encode('utf-8'))

    def test_encode_a_tag_with_str_data_and_attrs(self):
        self.assertEqual(_encode_tag(('tag', {'a':1}, 'text')),
                         '<tag a="1">text</tag>')

    def test_cdata_escaping_in_tag_body(self):
        self.assertEqual(_encode_tag(('tag', '<&>"\'\n\t\r')),
                         '<tag>&lt;&amp;&gt;"\'\n\t\r</tag>')

    def test_cdata_escaping_in_tag_attr(self):
        self.assertEqual(_encode_tag(('tag', {'a':'<&>"\'\n\r\t'})),
                         '<tag a="&lt;&amp;&gt;&quot;\'&#10;&#13;&#9;"/>')

    def test_must_not_double_escape(self):
        tag = ('tag', 
            ('tag2', {'a':'<&>"\'\n\r\t'})
        )
        self.assertEqual(_encode_tag(tag),
                         '<tag>\n'
                         '  <tag2 a="&lt;&amp;&gt;&quot;\'&#10;&#13;&#9;"/>\n'
                         '</tag>')

    def test_encode_tag_with_one_nested(self):
        tag = ('tag', ('tag2', ))
        self.assertEqual(_encode_tag(tag), '<tag>\n'
                                          '  <tag2/>\n'
                                          '</tag>')

    def test_encode_tag_with_multiple_children(self):
        tag = ('tag', 
            ('tag2', ),
            ('tag3', 'text'),
        )
        self.assertEqual(_encode_tag(tag), '<tag>\n'
                                          '  <tag2/>\n'
                                          '  <tag3>text</tag3>\n'
                                          '</tag>')

    def test_encode_tag_with_two_nested(self):
        tag = ('tag', 
            ('tag2', 
                ('tag3', ),
            ),
        )
        self.assertEqual(_encode_tag(tag), '<tag>\n'
                                          '  <tag2>\n'
                                          '    <tag3/>\n'
                                          '  </tag2>\n'
                                          '</tag>')

    def test_namespace(self):
        xsd = namespace('http://www.w3.org/2001/XMLSchema', 'xsd')
        self.assertTrue(isinstance(xsd('element'), qname))
        self.assertTrue(isinstance(xsd('element'), unicode))
        self.assertEqual(xsd('element'), u'xsd:element')
        self.assertEqual(xsd.element, u'xsd:element')
        self.assertEqual(xsd('element').uri, 'http://www.w3.org/2001/XMLSchema')
        self.assertEqual(xsd('element').prefix, 'xsd')
        self.assertEqual(xsd(u'имя-тега'), u'xsd:имя-тега')
        self.assertEqual(repr(xsd('element')),
                         "<qname u'xsd:element' "
                         "uri='http://www.w3.org/2001/XMLSchema'>")

    def test_namespace_collector_with_tags(self):
        ns = namespace('ns', 'ns')
        ns1 = namespace('ns1', 'ns1')
        tag = (ns.tag, ('tag1',),
                         (ns1.tag2, (ns.tag3,)))
        self.assertEqual(NamespaceCollector().visit(tag).namespaces,
                {'xmlns:ns':'ns', 'xmlns:ns1':'ns1'})

    def test_namespace_collector_with_tags_and_attrs(self):
        ns = namespace('ns', 'ns')
        ns1 = namespace('ns1', 'ns1')
        ns3 = namespace('ns3', 'ns3')
        tag = (ns.tag,
                ('tag1',),
                'text',
                (ns1.tag2, {ns3.attr: 'value'},
                    (ns.tag3,)))
        self.assertEqual(NamespaceCollector().visit(tag).namespaces,
                         {'xmlns:ns':'ns',
                          'xmlns:ns1':'ns1',
                          'xmlns:ns3':'ns3'})

    def test_namespace_collector_with_overlaping_shortcuts(self):
        ns = namespace('ns', 'ns')
        ns1 = namespace('ns1', 'ns')
        tag = (ns.tag, ('tag1',),
                         (ns1.tag2, (ns.tag3,)))
        with self.assertRaises(ValueError) as err:
            NamespaceCollector().visit(tag).namespaces

    def test_encode_xml_with_namespaces(self):
        ns = namespace('ns', 'ns')
        ns1 = namespace('ns1', 'ns1')
        ns3 = namespace('ns3', 'ns3')
        tag = (ns.tag,
                ('tag1',),
                'text',
                (ns1.tag2, {ns3.attr: 'value'},
                    (ns.tag3,)))
        self.assertEqual(encode(tag, indent=2),
                         '<?xml version="1.0"?>\n'
                         '<ns:tag xmlns:ns="ns" xmlns:ns1="ns1" xmlns:ns3="ns3">\n'
                         '  <tag1/>text\n'
                         '  <ns1:tag2 ns3:attr="value">\n'
                         '    <ns:tag3/>\n'
                         '  </ns1:tag2>\n'
                         '</ns:tag>')

    def test_encode_with_zero_indent(self):
        tag = ('tag', 
            ('tag2', 
                ('tag3', ),
            ),
        )
        self.assertEqual(encode(tag), '<?xml version="1.0"?>\n'
                                      '<tag><tag2><tag3/></tag2></tag>')

    def assertEqualEtree(self, one, two):
        for a,b in zip(one.getiterator(), two.getiterator()):
            self.assertEqual(a.tag, b.tag)
            self.assertEqual(a.attrib, b.attrib)
            self.assertEqual(a.text, b.text)
            self.assertEqual(a.tail, b.tail)

    def test_to_etree_empty_tag(self):
        self.assertEqualEtree(to_etree(('a',)), ElementTree.fromstring('<a/>'))

    def test_to_etree_empty_tag_and_one_nested(self):
        self.assertEqualEtree(to_etree(('a', ('b',))),
                              ElementTree.fromstring('<a><b/></a>'))

    def test_to_etree_tag_with_attrs(self):
        self.assertEqualEtree(to_etree(('a', {'attr': 'value'})),
                              ElementTree.fromstring('<a attr="value"/>'))

    def test_to_etree_tag_with_text(self):
        self.assertEqualEtree(to_etree(('a', 'text')),
                              ElementTree.fromstring('<a>text</a>'))

    def test_to_etree_tag_with_mixed_text_and_tags(self):
        self.assertEqualEtree(to_etree(('a', 'text', ('b',), 'tail')),
                              ElementTree.fromstring('<a>text<b/>tail</a>'))

    def test_to_etree_tag_with_ns(self):
        ns = namespace('ns', 'ns')
        self.assertEqualEtree(to_etree((ns.a,)),
                              ElementTree.fromstring('<ns:a xmlns:ns="ns"/>'))

    def test_custom_impl_object(self):
        from xml.etree import cElementTree
        self.assertEqualEtree(to_etree(('a',), impl=cElementTree),
                              cElementTree.fromstring('<a/>'))

    def test_timestamp_from_datetime(self):
        self.assertEqual(timestamp(datetime.datetime(2000, 1, 1)),
                         '2000-01-01T00:00:00')

    def test_timestamp_from_utc_datetime(self):
        try:
            from dateutil.tz import tzutc
        except ImportError:
            raise unittest.SkipTest('no dateutil module')
        self.assertEqual(timestamp(datetime.datetime(2000, 1, 1,
                                                     tzinfo=tzutc())),
                         '2000-01-01T00:00:00+00:00')


class TypeConversionTests(unittest.TestCase):

    def assertEtreeStrEquals(self, struct, value):
        self.assertEqual(ElementTree.tostring(to_etree(struct)), value)

    def test_None(self):
        self.assertEtreeStrEquals(('a', None), '<a />')

    def test_str(self):
        self.assertEtreeStrEquals(('a', 'text'), '<a>text</a>')

    def test_unicode(self):
        self.assertEtreeStrEquals(('a', u'text'), '<a>text</a>')

    def test_int(self):
        self.assertEtreeStrEquals(('a', 1), '<a>1</a>')

    def test_float(self):
        self.assertEtreeStrEquals(('a', 1.0), '<a>1.0</a>')

    def test_bool(self):
        self.assertEtreeStrEquals(('a', True), '<a>true</a>')

    def test_basestring_child_class(self):
        class MyStr(str):
            pass
        self.assertIsInstance(MyStr(), basestring)
        self.assertEtreeStrEquals(('a', MyStr('a')), '<a>a</a>')

    def test_qname_using_ElementTree(self):
        ns = namespace('urn:n', 'ns0')
        with self.assertRaisesRegexp(ValueError, 'does not support'):
                ElementTree.tostring(to_etree(('a', ns.tag)))

    @unittest.skipIf(not has_lxml, 'need lxml')
    def test_qname_using_lxml(self):
        ns = namespace('urn:n', 'ns0')
        self.assertEqual(etree.tostring(to_etree(('a', ns.tag), impl=etree)),
                                        '<a xmlns:ns0="urn:n">ns0:tag</a>')


if __name__=='__main__':
    unittest.main()

