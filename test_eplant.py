# -*- coding: utf-8 -*-

import unittest
import datetime
from xml.etree import ElementTree
from eplant import (
        _encode_tag, Sample, to_etree, namespace, qname, timestamp,
        NamespaceCollector, EtreeModifier, encode)


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
        self.assertEqual(xsd/'element', u'xsd:element')
        self.assertEqual(xsd('element').uri, 'http://www.w3.org/2001/XMLSchema')
        self.assertEqual(xsd('element').shortcut, 'xsd')
        self.assertEqual(xsd(u'имя-тега'), u'xsd:имя-тега')
        self.assertEqual(repr(xsd('element')),
                         "<qname u'xsd:element' "
                         "uri='http://www.w3.org/2001/XMLSchema'>")

    def test_namespace_collector_with_tags(self):
        ns = namespace('ns', 'ns')
        ns1 = namespace('ns1', 'ns1')
        tag = (ns/'tag', ('tag1',),
                         (ns1/'tag2', (ns/'tag3',)))
        self.assertEqual(NamespaceCollector().visit(tag).namespaces,
                {'xmlns:ns':'ns', 'xmlns:ns1':'ns1'})

    def test_namespace_collector_with_tags_and_attrs(self):
        ns = namespace('ns', 'ns')
        ns1 = namespace('ns1', 'ns1')
        ns3 = namespace('ns3', 'ns3')
        tag = (ns/'tag',
                ('tag1',),
                'text',
                (ns1/'tag2', {ns3/'attr': 'value'},
                    (ns/'tag3',)))
        self.assertEqual(NamespaceCollector().visit(tag).namespaces,
                         {'xmlns:ns':'ns',
                          'xmlns:ns1':'ns1',
                          'xmlns:ns3':'ns3'})

    def test_namespace_collector_with_overlaping_shortcuts(self):
        ns = namespace('ns', 'ns')
        ns1 = namespace('ns1', 'ns')
        tag = (ns/'tag', ('tag1',),
                         (ns1/'tag2', (ns/'tag3',)))
        with self.assertRaises(ValueError) as err:
            NamespaceCollector().visit(tag).namespaces

    def test_encode_xml_with_namespaces(self):
        ns = namespace('ns', 'ns')
        ns1 = namespace('ns1', 'ns1')
        ns3 = namespace('ns3', 'ns3')
        tag = (ns/'tag',
                ('tag1',),
                'text',
                (ns1/'tag2', {ns3/'attr': 'value'},
                    (ns/'tag3',)))
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
        self.assertEqualEtree(to_etree((ns/'a',)),
                              ElementTree.fromstring('<ns:a xmlns:ns="ns"/>'))

    def test_custom_builder_object(self):
        self.assertEqualEtree(to_etree(('a',),
                                       builder=ElementTree.TreeBuilder()),
                              ElementTree.fromstring('<a/>'))

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

    def test_etree_modifier_set_text(self):
        tree = EtreeModifier(to_etree(('a', ('b',))))
        tree.set_text('b', 'text')
        self.assertEqual(tree.tree.find('b').text, 'text')

    def test_etree_modifier_set_text_with_invalid_path(self):
        tree = EtreeModifier(to_etree(('a', ('b',))))
        with self.assertRaises(ValueError):
            tree.set_text('bb', 'text')

    def test_etree_modifier_get_text(self):
        tree = EtreeModifier(to_etree(('a', ('b', 'text'))))
        self.assertEqual(tree.get_text('b'), 'text')

    def test_etree_modifier_get_text_with_invalid_path(self):
        tree = EtreeModifier(to_etree(('a', ('b',))))
        with self.assertRaises(ValueError):
            tree.get_text('bb')

    def test_etree_modifier_set_attr(self):
        tree = EtreeModifier(to_etree(('a', ('b',))))
        tree.set_attr('b', 'id', 'value')
        self.assertEqual(tree.tree.find('b').attrib, {'id': 'value'})

    def test_etree_modifier_set_attr_with_invalid_path(self):
        tree = EtreeModifier(to_etree(('a', ('b',))))
        with self.assertRaises(ValueError):
            tree.set_attr('bb', 'id', 'value')

    def test_etree_modifier_get_attr(self):
        tree = EtreeModifier(to_etree(('a', ('b', {'id': 'value'}))))
        self.assertEqual(tree.get_attr('b', 'id'), 'value')

    def test_etree_modifier_get_attr_with_invalid_path(self):
        tree = EtreeModifier(to_etree(('a', ('b',))))
        with self.assertRaises(ValueError):
            tree.get_attr('bb', 'id')


if __name__=='__main__':
    unittest.main()

