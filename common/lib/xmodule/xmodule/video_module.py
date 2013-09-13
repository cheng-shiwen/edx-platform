# coding: utf-8
# pylint: disable=W0223
"""Video is ungraded Xmodule for support video content."""

import json
import logging

from lxml import etree
from pkg_resources import resource_string, resource_listdir

from django.http import Http404

from xmodule.x_module import XModule
from xmodule.raw_module import RawDescriptor
from xmodule.xml_module import is_pointer_tag, name_to_pathname
from xmodule.modulestore import Location
# from xmodule.modulestore.mongo import MongoModuleStore
# from xmodule.modulestore.django import modulestore
from xmodule.contentstore.content import StaticContent
from xblock.core import Integer, Scope, String

log = logging.getLogger(__name__)


class VideoFields(object):
    """Fields for `VideoModule` and `VideoDescriptor`."""
    data = String(help="通过编辑XML数据来给定视频参数和信息", scope=Scope.content, default="")
    position = Integer(help="当前视频中的位置", scope=Scope.user_state, default=0)
    source = String(help="视频的URL地址，支持mp4/m4v/webm/ogv/mov/wmv/flv", display_name="视频地址", scope=Scope.settings, default="")
    track_zh = String(help="中文字幕的上传路径，字幕将显示在视频底部，支持srt/vtt", display_name="视频字幕 (中文)", scope=Scope.settings, default="")
    track_en = String(help="英文字幕的上传路径，字幕将显示在视频底部，支持srt/vtt", display_name="视频字幕 (英文)", scope=Scope.settings, default="")

class VideoModule(VideoFields, XModule):
    """Video Xmodule."""
    video_time = 0
    icon_class = 'video'

    def __init__(self, *args, **kwargs):
        XModule.__init__(self, *args, **kwargs)
        if self.data:
            try:
                xml = etree.fromstring(self.data)
                if xml.tag == 'video':
                    if xml.get('display_name'):
                        self.display_name = xml.get('display_name')
                    if xml.findall('source'):
                        self.source = [ele.get('src') for ele in xml.findall('source')][0]
                    for ele in xml.findall('track'):
                        if ele.get('srclang') == 'zh' and ele.get('src'):
                            self.track_zh = ele.get('src')
                        if ele.get('srclang') == 'en' and ele.get('src'):
                            self.track_en = ele.get('src')
            except Exception as e:
                log.debug("error parsing video xml data")
                pass
        
        self.sourceType = self._get_source_type(self.source)

    def _get_source_type(self, source):
        if source.find('youtube') > -1:
            return 'video/youtube'
        elif '.' in source:
            ext = source.rsplit('.', 1)[1].lower()
            if ext in ['mp4', 'm4v']:
                return 'video/mp4'
            elif ext == 'ogv':
                return 'video/ogg'
            elif ext in ['webm', 'mov', 'wmv', 'flv', 'swf']:
                return 'video/' + ext
        return 'video/mp4'

    def handle_ajax(self, dispatch, data):
        """This is not being called right now and we raise 404 error."""
        log.debug(u"GET {0}".format(data))
        log.debug(u"DISPATCH {0}".format(dispatch))
        raise Http404()

    def get_instance_state(self):
        """Return information about state (position)."""
        return json.dumps({'position': self.position})

    def get_html(self):
        # if isinstance(modulestore(), MongoModuleStore):
        #     upload_asset_path = StaticContent.get_base_url_path_for_course_assets(self.location) + '/'
        # else:
        #     upload_asset_path = ''

        return self.system.render_template('video.html', {
            'id': self.location.html_id(),
            'position': self.position,
            # 'upload_asset_path': upload_asset_path,
            'source': self.source,
            'sourceType': self.sourceType,
            'track_zh': self.track_zh,
            'track_en': self.track_en,
            'display_name': self.display_name_with_default
        })


class VideoDescriptor(VideoFields, RawDescriptor):
    module_class = VideoModule
    template_dir_name = "video"

    def __init__(self, *args, **kwargs):
        super(VideoDescriptor, self).__init__(*args, **kwargs)

    @classmethod
    def from_xml(cls, xml_data, system, org=None, course=None):
        """
        Creates an instance of this descriptor from the supplied xml_data.
        This may be overridden by subclasses

        xml_data: A string of xml that will be translated into data and children for
            this module
        system: A DescriptorSystem for interacting with external resources
        org and course are optional strings that will be used in the generated modules
            url identifiers
        """
        xml_object = etree.fromstring(xml_data)
        url_name = xml_object.get('url_name', xml_object.get('slug'))
        location = Location('i4x', org, course, 'video', url_name)
        if is_pointer_tag(xml_object):
            filepath = cls._format_filepath(xml_object.tag, name_to_pathname(url_name))
            xml_data = etree.tostring(cls.load_file(filepath, system.resources_fs, location))
        
        upload_asset_path = VideoDescriptor._get_upload_asset_path(system.course_dir)
        model_data = {}
        xml = etree.fromstring(xml_data)

        display_name = xml.get('display_name')
        if display_name:
            model_data['display_name'] = display_name

        sources = xml.findall('source')
        if sources:
            model_data['source'] = [ele.get('src') for ele in sources][0]

        tracks = xml.findall('track')
        if tracks:
            for ele in tracks:
                if ele.get('srclang') == 'zh':
                    model_data['track_zh'] = upload_asset_path + ele.get('src').rsplit('/', 1)[1]
                elif ele.get('srclang') == 'en':
                    model_data['track_en'] = upload_asset_path + ele.get('src').rsplit('/', 1)[1]

        model_data['location'] = location
        video = cls(system, model_data)
        return video

    @staticmethod
    def _get_upload_asset_path(course_dir):
        if course_dir.find('/drafts') > -1:
            course_dir = course_dir.rsplit('/', 2)[1]
        _org = course_dir.split('-')[0]
        _course = course_dir.split('-')[1]
        return '/'.join(['/c4x', _org, _course, 'asset/'])

    def definition_to_xml(self, resource_fs):
        xml = etree.Element('video')

        xml.set('display_name', self.display_name)

        if self.source:
            ele = etree.Element('source')
            ele.set('src', self.source)
            xml.append(ele)

        if self.track_zh:
            ele = etree.Element('track')
            ele.set('src', self.track_zh)
            ele.set('srclang', 'zh')
            xml.append(ele)

        if self.track_en:
            ele = etree.Element('track')
            ele.set('src', self.track_en)
            ele.set('srclang', 'en')
            xml.append(ele)

        return xml
