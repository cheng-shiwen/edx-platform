"""
Graphical slider tool module is ungraded xmodule used by students to
understand functional dependencies.
"""

import json
import logging
from lxml import etree
from lxml import html
import xmltodict

from xmodule.editing_module import MetadataOnlyEditingDescriptor
from xmodule.xml_module import XmlDescriptor
from xmodule.x_module import XModule
from xmodule.stringify import stringify_children
from pkg_resources import resource_string
from xblock.core import String, Scope

log = logging.getLogger(__name__)

class LTIFields(object):
    provider_url = String(
        help="URL of the tool provider",
        default='',
        # TODO: Write a letter.
        scope=Scope.content
    )
    tool_id = String(
        help="The ID of the tool",
        default="",

        # TODO: Write a letter.
        scope=Scope.content        
    )


class LTIModule(LTIFields, XModule):
    ''' LTI Module
    '''

    js = {
        'js': [
            resource_string(__name__, 'js/src/lti/main.js')
        ]
    }
    css = {'scss': [resource_string(__name__, 'css/gst/display.scss')]}
    js_module_name = "LTI"

    def get_html(self):
        """ Renders parameters to template. """

        # these 3 will be used in class methods
        self.html_id = self.location.html_id()
        self.html_class = self.location.category

        params = {
            'lti_html': self.get_lti_html(),
            'element_id': self.html_id,
            'element_class': self.html_class,
        }
        content = self.system.render_template(
            'lti.html', params
        )
        return content

    def get_lti_html(self):
        return "<div>Hello, world!</div>"

class LTIModuleDescriptor(LTIFields, MetadataOnlyEditingDescriptor):
    module_class = LTIModule

   