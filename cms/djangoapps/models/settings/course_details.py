from xmodule.modulestore import Location
from xmodule.modulestore.exceptions import ItemNotFoundError
from xmodule.modulestore.inheritance import own_metadata
import json
from json.encoder import JSONEncoder
from contentstore.utils import get_modulestore
from models.settings import course_grading
from contentstore.utils import update_item
from xmodule.fields import Date
import re
import logging
import datetime


class CourseDetails(object):
    def __init__(self, location):
        self.course_location = location  # a Location obj
        self.start_date = None  # 'start'
        self.end_date = None  # 'end'
        self.enrollment_start = None
        self.enrollment_end = None
        self.syllabus = None  # a pdf file asset
        self.overview = ""  # html to render as the overview
        self.intro_video = None  # a video pointer
        self.effort = None  # int hours/week

    @classmethod
    def fetch(cls, course_location):
        """
        Fetch the course details for the given course from persistence and return a CourseDetails model.
        """
        if not isinstance(course_location, Location):
            course_location = Location(course_location)

        course = cls(course_location)

        descriptor = get_modulestore(course_location).get_item(course_location)

        course.start_date = descriptor.start
        course.end_date = descriptor.end
        course.enrollment_start = descriptor.enrollment_start
        course.enrollment_end = descriptor.enrollment_end

        temploc = course_location.replace(category='about', name='syllabus')
        try:
            course.syllabus = get_modulestore(temploc).get_item(temploc).data
        except ItemNotFoundError:
            pass

        temploc = temploc.replace(name='overview')
        try:
            course.overview = get_modulestore(temploc).get_item(temploc).data
        except ItemNotFoundError:
            pass

        temploc = temploc.replace(name='effort')
        try:
            course.effort = get_modulestore(temploc).get_item(temploc).data
        except ItemNotFoundError:
            pass

        temploc = temploc.replace(name='video')
        try:
            raw_video = get_modulestore(temploc).get_item(temploc).data
            course.intro_video = CourseDetails.parse_video_tag(raw_video)
        except ItemNotFoundError:
            pass

        return course

    @classmethod
    def update_from_json(cls, jsondict):
        """
        Decode the json into CourseDetails and save any changed attrs to the db
        """
        # TODO make it an error for this to be undefined & for it to not be retrievable from modulestore
        course_location = Location(jsondict['course_location'])
        # Will probably want to cache the inflight courses because every blur generates an update
        descriptor = get_modulestore(course_location).get_item(course_location)

        dirty = False

        # In the descriptor's setter, the date is converted to JSON using Date's to_json method.
        # Calling to_json on something that is already JSON doesn't work. Since reaching directly
        # into the model is nasty, convert the JSON Date to a Python date, which is what the
        # setter expects as input.
        date = Date()

        if 'start_date' in jsondict:
            converted = date.from_json(jsondict['start_date'])
        else:
            converted = None
        if converted != descriptor.start:
            dirty = True
            descriptor.start = converted

        if 'end_date' in jsondict:
            converted = date.from_json(jsondict['end_date'])
        else:
            converted = None

        if converted != descriptor.end:
            dirty = True
            descriptor.end = converted

        if 'enrollment_start' in jsondict:
            converted = date.from_json(jsondict['enrollment_start'])
        else:
            converted = None

        if converted != descriptor.enrollment_start:
            dirty = True
            descriptor.enrollment_start = converted

        if 'enrollment_end' in jsondict:
            converted = date.from_json(jsondict['enrollment_end'])
        else:
            converted = None

        if converted != descriptor.enrollment_end:
            dirty = True
            descriptor.enrollment_end = converted

        if dirty:
            # Save the data that we've just changed to the underlying
            # MongoKeyValueStore before we update the mongo datastore.
            descriptor.save()

            get_modulestore(course_location).update_metadata(course_location, own_metadata(descriptor))

        # NOTE: below auto writes to the db w/o verifying that any of the fields actually changed
        # to make faster, could compare against db or could have client send over a list of which fields changed.
        temploc = Location(course_location).replace(category='about', name='syllabus')
        update_item(temploc, jsondict['syllabus'])

        temploc = temploc.replace(name='overview')
        update_item(temploc, jsondict['overview'])

        temploc = temploc.replace(name='effort')
        update_item(temploc, jsondict['effort'])

        temploc = temploc.replace(name='video')
        recomposed_video_tag = CourseDetails.recompose_video_tag(jsondict['intro_video'])
        update_item(temploc, recomposed_video_tag)

        # Could just generate and return a course obj w/o doing any db reads, but I put the reads in as a means to confirm
        # it persisted correctly
        return CourseDetails.fetch(course_location)

    @staticmethod
    def parse_video_tag(raw_video):
        # return the intro-video url to intro course setting's page in cms
        if raw_video:
            keystring_matcher = re.search(r'&&([^"]*)', raw_video)
            if keystring_matcher:
                return keystring_matcher.group(1)
            else:
                return raw_video
        else:
            return None

    @staticmethod
    def recompose_video_tag(video_url):
        # return the intro-video frame to intro course page in lms
        result = None
        if video_url:
            video_type = 'video/mp4'
            if video_url.find('youtube') > -1:
                video_type = 'video/youtube'
            elif '.' in video_url:
                ext = video_url.rsplit('.', 1)[1].lower()
                if ext == 'ogv':
                    video_type = 'video/ogg'
                elif ext in ['webm', 'mov', 'wmv', 'flv', 'swf']:
                    video_type = 'video/' + ext
            result = '<iframe width="560" height="315" src="/static/player/introvideo.html?' + video_type + '&&' + video_url + '" frameborder="0" allowfullscreen=""></iframe>'
        return result


# TODO move to a more general util?
class CourseSettingsEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (CourseDetails, course_grading.CourseGradingModel)):
            return obj.__dict__
        elif isinstance(obj, Location):
            return obj.dict()
        elif isinstance(obj, datetime.datetime):
            return Date().to_json(obj)
        else:
            return JSONEncoder.default(self, obj)
