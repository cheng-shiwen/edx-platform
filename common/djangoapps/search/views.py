"""
View functions and interface for search functionality
"""

import requests
import logging
import hashlib
import json

from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponse
from mitxmako.shortcuts import render_to_response
from django_future.csrf import ensure_csrf_cookie

from courseware.courses import get_course_with_access
from search.models import SearchResults
from search.es_requests import MongoIndexer


CONTENT_TYPES = ("transcript", "problem")
log = logging.getLogger(__name__)


@ensure_csrf_cookie
def search(request, course_id):
    """
    Returns search results within course_id from request.

    Request should contain the query string in the "s" parameter.

    If user doesn't have access to the course, get_course_with_access automatically 404s
    """

    page = int(request.GET.get("page", 1))
    filter = request.GET.get("filter", "all")
    course = get_course_with_access(request.user, course_id, 'load')
    context = _find(request, course_id, page, filter)
    context.update({"course": course})
    return render_to_response("search_templates/results.html", context)


@ensure_csrf_cookie
def index_course(request):
    """
    Indexes the searchable material currently within the course

    Is called via AJAX from Studio, and doesn't render any templates.
    """

    indexer = MongoIndexer("localhost", 27017)
    if "course" in request.POST:
        indexer.index_course(request.POST["course"])
        log.debug("Course indexed")
        return HttpResponse(status=204)
    else:
        return HttpResponseBadRequest()


def _find(request, course_id, page=1, filter="all", test_url=None):
    """
    Method in charge of getting search results and associated metadata
    """

    database = test_url or settings.ES_DATABASE
    full_query_data = {}
    query = request.GET.get("s", "*.*")
    full_query_data.update(
        {
            "query": {
                "query_string": {
                    "default_field": "searchable_text",
                    "query": query,
                    "analyzer": "standard"
                },
            },
            "size": "1000"
        }
    )
    index = ",".join(
        [content_type + "-index" for content_type in CONTENT_TYPES if request.GET.get(content_type, False)]
    )
    if len(index) == 0:
        index = ",".join([content + "-index" for content in CONTENT_TYPES])

    course_hash = hashlib.sha1(course_id).hexdigest()
    base_url = "/".join([database, index, course_hash])
    base_url += "/_search"
    context = {}
    response = requests.get(base_url, data=json.dumps(full_query_data))
    results = SearchResults(response, **request.GET)
    results.sort_results()
    course = course_id.split("/")[1]
    context.update({"results": len(results.entries) > 0})
    context.update({
        "result_start": (page - 1) * 10,
        "result_end": page * 10,
        "filter": filter,
        "data": results,
        "old_query": query,
        "course_id": course
    })
    return context
