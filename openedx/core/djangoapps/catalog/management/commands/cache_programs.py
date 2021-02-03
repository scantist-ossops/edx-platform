""""Management command to add program information to the cache."""


import logging
import sys
from collections import defaultdict

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.management import BaseCommand
from six import text_type

from openedx.core.djangoapps.catalog.cache import (
    COURSE_PROGRAMS_CACHE_KEY_TPL,
    CATALOG_COURSE_PROGRAMS_CACHE_KEY_TPL,
    PATHWAY_CACHE_KEY_TPL,
    PROGRAM_CACHE_KEY_TPL,
    PROGRAMS_BY_ORGANIZATION_CACHE_KEY_TPL,
    PROGRAMS_BY_TYPE_CACHE_KEY_TPL,
    PROGRAMS_BY_TYPE_SLUG_CACHE_KEY_TPL,
    SITE_PATHWAY_IDS_CACHE_KEY_TPL,
    SITE_PROGRAM_UUIDS_CACHE_KEY_TPL
)
from openedx.core.djangoapps.catalog.models import CatalogIntegration
from openedx.core.djangoapps.catalog.utils import (
    course_run_keys_for_program,
    course_uuids_for_program,
    create_catalog_api_client,
    normalize_program_type
)

logger = logging.getLogger(__name__)
User = get_user_model()  # pylint: disable=invalid-name


class Command(BaseCommand):
    """Management command used to cache program data.

    This command requests every available program from the discovery
    service, writing each to its own cache entry with an indefinite expiration.
    It is meant to be run on a scheduled basis and should be the only code
    updating these cache entries.
    """
    help = "Rebuild the LMS' cache of program data."

    # lint-amnesty, pylint: disable=bad-option-value, unicode-format-string
    def handle(self, *args, **options):  # lint-amnesty, pylint: disable=too-many-statements
        failure = False
        logger.info('populate-multitenant-programs switch is ON')

        catalog_integration = CatalogIntegration.current()
        username = catalog_integration.service_username

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            logger.exception(
                u'Failed to create API client. Service user {username} does not exist.'.format(username=username)
            )
            raise

        programs = {}
        pathways = {}
        courses = {}
        catalog_courses = {}
        programs_by_type = {}
        programs_by_type_slug = {}
        organizations = {}
        for site in Site.objects.all():
            site_config = getattr(site, 'configuration', None)
            if site_config is None or not site_config.get_value('COURSE_CATALOG_API_URL'):
                logger.info(u'Skipping site {domain}. No configuration.'.format(domain=site.domain))
                cache.set(SITE_PROGRAM_UUIDS_CACHE_KEY_TPL.format(domain=site.domain), [], None)
                cache.set(SITE_PATHWAY_IDS_CACHE_KEY_TPL.format(domain=site.domain), [], None)
                continue

            client = create_catalog_api_client(user, site=site)
            uuids, program_uuids_failed = self.get_site_program_uuids(client, site)
            new_programs, program_details_failed = self.fetch_program_details(client, uuids)
            new_pathways, pathways_failed = self.get_pathways(client, site)
            new_pathways, new_programs, pathway_processing_failed = self.process_pathways(
                site, new_pathways, new_programs
            )

            failure = any([
                program_uuids_failed,
                program_details_failed,
                pathways_failed,
                pathway_processing_failed,
            ])

            programs.update(new_programs)
            pathways.update(new_pathways)
            courses.update(self.get_courses(new_programs))
            catalog_courses.update(self.get_catalog_courses(new_programs))
            programs_by_type.update(self.get_programs_by_type(site, new_programs))
            programs_by_type_slug.update(self.get_programs_by_type_slug(site, new_programs))
            organizations.update(self.get_programs_by_organization(new_programs))

            logger.info(u'Caching UUIDs for {total} programs for site {site_name}.'.format(
                total=len(uuids),
                site_name=site.domain,
            ))
            cache.set(SITE_PROGRAM_UUIDS_CACHE_KEY_TPL.format(domain=site.domain), uuids, None)

            pathway_ids = list(new_pathways.keys())
            logger.info(u'Caching ids for {total} pathways for site {site_name}.'.format(
                total=len(pathway_ids),
                site_name=site.domain,
            ))
            cache.set(SITE_PATHWAY_IDS_CACHE_KEY_TPL.format(domain=site.domain), pathway_ids, None)

        logger.info(u'Caching details for {} programs.'.format(len(programs)))
        cache.set_many(programs, None)

        logger.info(u'Caching details for {} pathways.'.format(len(pathways)))
        cache.set_many(pathways, None)

        logger.info(u'Caching programs uuids for {} courses.'.format(len(courses)))
        cache.set_many(courses, None)

        logger.info(u'Caching programs uuids for {} catalog courses.'.format(len(catalog_courses)))
        cache.set_many(catalog_courses, None)

        logger.info(text_type('Caching program UUIDs by {} program types.'.format(len(programs_by_type))))
        cache.set_many(programs_by_type, None)

        logger.info(text_type('Caching program UUIDs by {} program type slugs.'.format(len(programs_by_type_slug))))
        cache.set_many(programs_by_type_slug, None)

        logger.info(u'Caching programs uuids for {} organizations'.format(len(organizations)))
        cache.set_many(organizations, None)

        if failure:
            sys.exit(1)

    def get_site_program_uuids(self, client, site):  # lint-amnesty, pylint: disable=missing-function-docstring
        failure = False
        uuids = []
        try:
            querystring = {
                'exclude_utm': 1,
                'status': ('active', 'retired'),
                'uuids_only': 1,
            }

            logger.info(u'Requesting program UUIDs for {domain}.'.format(domain=site.domain))
            uuids = client.programs.get(**querystring)
        except:  # pylint: disable=bare-except
            logger.exception(u'Failed to retrieve program UUIDs for site: {domain}.'.format(domain=site.domain))
            failure = True

        logger.info(u'Received {total} UUIDs for site {domain}'.format(
            total=len(uuids),
            domain=site.domain
        ))
        return uuids, failure

    def fetch_program_details(self, client, uuids):  # lint-amnesty, pylint: disable=missing-function-docstring
        programs = {}
        failure = False
        for uuid in uuids:
            try:
                cache_key = PROGRAM_CACHE_KEY_TPL.format(uuid=uuid)
                logger.info(u'Requesting details for program {uuid}.'.format(uuid=uuid))
                program = client.programs(uuid).get(exclude_utm=1)
                # pathways get added in process_pathways
                program['pathway_ids'] = []
                programs[cache_key] = program
            except:  # pylint: disable=bare-except
                logger.exception(u'Failed to retrieve details for program {uuid}.'.format(uuid=uuid))
                failure = True
                continue
        return programs, failure

    def get_pathways(self, client, site):
        """
        Get all pathways for the current client
        """
        pathways = []
        failure = False
        logger.info(u'Requesting pathways for {domain}.'.format(domain=site.domain))
        try:
            next_page = 1
            while next_page:
                new_pathways = client.pathways.get(exclude_utm=1, page=next_page)
                pathways.extend(new_pathways['results'])
                next_page = next_page + 1 if new_pathways['next'] else None

        except:  # pylint: disable=bare-except
            logger.exception(
                msg=u'Failed to retrieve pathways for site: {domain}.'.format(domain=site.domain),
            )
            failure = True

        logger.info(u'Received {total} pathways for site {domain}'.format(
            total=len(pathways),
            domain=site.domain
        ))

        return pathways, failure

    def process_pathways(self, site, pathways, programs):
        """
        For each program, add references to each pathway it is a part of.
        For each pathway, replace the "programs" dict with "program_uuids",
        which only contains uuids (since program data is already cached)
        """
        processed_pathways = {}
        failure = False
        for pathway in pathways:
            try:
                pathway_id = pathway['id']
                pathway_cache_key = PATHWAY_CACHE_KEY_TPL.format(id=pathway_id)
                processed_pathways[pathway_cache_key] = pathway
                uuids = []

                for program in pathway['programs']:
                    program_uuid = program['uuid']
                    program_cache_key = PROGRAM_CACHE_KEY_TPL.format(uuid=program_uuid)
                    programs[program_cache_key]['pathway_ids'].append(pathway_id)
                    uuids.append(program_uuid)

                del pathway['programs']
                pathway['program_uuids'] = uuids
            except:  # pylint: disable=bare-except
                logger.exception(u'Failed to process pathways for {domain}'.format(domain=site.domain))
                failure = True
        return processed_pathways, programs, failure

    def get_courses(self, programs):
        """
        Get all course runs for programs.

        TODO: when course discovery can handle it, use that instead. That will allow us to put all course runs
        in the cache not just the course runs in a program. Therefore, a cache miss would be different from a
        course not in a program.
        """
        course_runs = defaultdict(list)

        for program in programs.values():
            for course_run_key in course_run_keys_for_program(program):
                course_run_cache_key = COURSE_PROGRAMS_CACHE_KEY_TPL.format(course_run_id=course_run_key)
                course_runs[course_run_cache_key].append(program['uuid'])
        return course_runs

    def get_catalog_courses(self, programs):
        """
        Get all catalog courses for the programs.
        """
        courses = defaultdict(list)

        for program in programs.values():
            for course_uuid in course_uuids_for_program(program):
                course_cache_key = CATALOG_COURSE_PROGRAMS_CACHE_KEY_TPL.format(course_uuid=course_uuid)
                courses[course_cache_key].append(program['uuid'])
        return courses

    def get_programs_by_type(self, site, programs):
        """
        Returns a dictionary mapping site-aware cache keys corresponding to program types
        to lists of program uuids with that type.
        """
        programs_by_type = defaultdict(list)
        for program in programs.values():
            program_type = normalize_program_type(program.get('type'))
            cache_key = PROGRAMS_BY_TYPE_CACHE_KEY_TPL.format(site_id=site.id, program_type=program_type)
            programs_by_type[cache_key].append(program['uuid'])
        return programs_by_type

    def get_programs_by_type_slug(self, site, programs):
        """
        Returns a dictionary mapping site-aware cache keys corresponding to program types
        to lists of program uuids with that type.
        """
        programs_by_type_slug = defaultdict(list)
        for program in programs.values():
            program_slug = program.get('type_attrs', {}).get('slug')
            cache_key = PROGRAMS_BY_TYPE_SLUG_CACHE_KEY_TPL.format(site_id=site.id, program_slug=program_slug)
            programs_by_type_slug[cache_key].append(program['uuid'])
        return programs_by_type_slug

    def get_programs_by_organization(self, programs):
        """
        Returns a dictionary mapping organization keys to lists of program uuids authored by that org
        """
        organizations = defaultdict(list)
        for program in programs.values():
            for org in program['authoring_organizations']:
                org_cache_key = PROGRAMS_BY_ORGANIZATION_CACHE_KEY_TPL.format(org_key=org['key'])
                organizations[org_cache_key].append(program['uuid'])
        return organizations
