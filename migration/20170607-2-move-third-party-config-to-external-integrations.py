#!/usr/bin/env python
"""Move integration details from the Configuration file into the
database as ExternalIntegrations
"""
import os
import sys
import json
import logging
from nose.tools import set_trace

bin_dir = os.path.split(__file__)[0]
package_dir = os.path.join(bin_dir, "..")
sys.path.append(os.path.abspath(package_dir))

from core.model import (
    ConfigurationSetting,
    ExternalIntegration as EI,
    Library,
    get_one_or_create,
    production_session,
)

from api.config import Configuration

log = logging.getLogger(name="Circulation manager configuration import")

def log_import(integration_or_setting, is_new):
    if is_new:
        log.info("CREATED: %r" % integration_or_setting)
    else:
        log.info("%r already exists." % integration_or_setting)

try:
    Configuration.load()
    _db = production_session()
    LIBRARIES = _db.query(Library).all()

    # Import Circulation Manager base url.
    circ_manager_conf = Configuration.integration('Circulation Manager')
    if circ_manager_conf:
        url = circ_manager_conf.get('url')
        if url:
            setting = ConfigurationSetting.sitewide(_db, Configuration.BASE_URL_KEY)
            is_new = setting.value == None
            setting.value = unicode(url)
            log_import(setting, is_new)

    # Import Metadata Wrangler configuration.
    metadata_wrangler_conf = Configuration.integration('Metadata Wrangler')

    if metadata_wrangler_conf:
        url = metadata_wrangler_conf.get('url')
        username = metadata_wrangler_conf.get('client_id')
        password = metadata_wrangler_conf.get('client_secret')

        integration, is_new = get_one_or_create(
            _db, EI, protocol=EI.METADATA_WRANGLER, goal=EI.METADATA_GOAL,
            url=url, username=username, password=password
        )
        log_import(integration, is_new)

    # Import NoveList Select configuration.
    novelist = Configuration.integration('NoveList Select')
    if novelist:
        username = novelist.get('profile')
        password = novelist.get('password')

        integration, is_new = get_one_or_create(
            _db, EI, protocol=EI.NOVELIST, goal=EI.METADATA_GOAL,
            username=username, password=password
        )
        integration.libraries.extend(LIBRARIES)
        log_import(integration, is_new)

    # Import NYT configuration.
    nyt_conf = Configuration.integration(u'New York Times')
    if nyt_conf:
        password = nyt_conf.get('best_sellers_api_key')

        integration, is_new = get_one_or_create(
            _db, EI, protocol=EI.NYT, goal=EI.METADATA_GOAL,
            password=password
        )
        log_import(integration, is_new)

    # Import Adobe Vendor ID configuration.
    adobe_conf = Configuration.integration('Adobe Vendor ID')
    if adobe_conf:
        integration, is_new = get_one_or_create(
            _db, EI, protocol=EI.ADOBE_VENDOR_ID, goal=EI.DRM_GOAL
        )

        integration.username = adobe_conf.get('vendor_id')
        integration.password = adobe_conf.get('node_value')

        other_libraries = adobe_conf.get('other_libraries')
        if other_libraries:
            other_libraries = unicode(json.dumps(other_libraries))
        integration.set_setting(u'other_libraries', other_libraries)
        integration.libraries.extend(LIBRARIES)

    # Import Google OAuth configuration.
    google_oauth_conf = Configuration.integration('Google OAuth')
    if google_oauth_conf:
        integration, is_new = get_one_or_create(
            _db, EI, protocol=EI.GOOGLE_OAUTH, goal=EI.ADMIN_AUTH_GOAL,
        )

        integration.url = google_oauth_conf.get("web", {}).get("auth_uri")
        integration.username = google_oauth_conf.get("web", {}).get("client_id")
        integration.password = google_oauth_conf.get("web", {}).get("client_secret")

        auth_domain = Configuration.policy('admin_authentication_domain')
        if auth_domain:
            integration.set_setting(u'domains', json.dumps([auth_domain]))

        log_import(integration, is_new)

    # Import Patron Web Client configuration.
    patron_web_client_conf = Configuration.integration(u'Patron Web Client', {})
    patron_web_client_url = patron_web_client_conf.get('url')
    if patron_web_client_url:
        setting = ConfigurationSetting.sitewide(
            _db, ExternalIntegration.PATRON_WEB_CLIENT)
        is_new = setting.value == None
        setting.value = patron_web_client_url
        log_import(setting, is_new)
finally:
    _db.commit()
    _db.close()
