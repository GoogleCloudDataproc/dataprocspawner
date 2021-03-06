# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

""" Replaces default JupyterHub.app to handle redirects. """

import re

from dataprocspawner.spawnable import DataprocHubServer
from jupyterhub.app import JupyterHub
from jupyterhub.handlers.base import UserUrlHandler
from jupyterhub.objects import Server


class DataprocHubUserUrlHandler(UserUrlHandler):
  """ Extends UserUrlHandler to redirect user once spawn is done. """

  async def _redirect_to_user_server(self, user, spawner):
    self.statsd.incr('redirects.user_after_login')
    redirect_url = None
    tmp_spawner = user.spawners[spawner.name]
    tmp_spawner_server = tmp_spawner.server
    self.log.debug(f'# spawners are {user.spawners}')
    self.log.info(f'# spawner.server value is {tmp_spawner_server}')
    if isinstance(tmp_spawner_server, DataprocHubServer):
      self.log.info('# Read component gateway url from DataprocHubServer.')
      redirect_url = tmp_spawner.component_gateway_url
    elif isinstance(tmp_spawner_server, Server):
      self.log.info('# Make component gateway url from Server url.')
      url_parts = re.search('(.+?)://(.+?)/(.+?)', tmp_spawner_server.url)
      redirect_url = f'{url_parts.group(1)}://{url_parts.group(2)}/jupyter/lab'
    else:
      self.log.info('# Can not type identify spawner server.')

    self.log.info(f'# Redirecting to notebook at {redirect_url}.')
    self.redirect(redirect_url)


class DataprocHub(JupyterHub):
  """ Extends JupyterHub mainly to handle redirect vs proxy.

  The order of the handlers is important, the handler with the lowest index in
  the list having the highest priority.

  This class inserts a new handler for the user at the lowest index (e.g highest
  priority) without changing the existing handlers.
  """

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    self.new_handlers = [
      (r'/user/(?P<user_name>[^/]+)(?P<user_path>/.*)?', DataprocHubUserUrlHandler),
    ]

    self.new_prefixed = self.add_url_prefix(self.hub_prefix, self.new_handlers.copy())

  def init_handlers(self):
    """ Modifies the default app handlers.

    Modifies the default behavior of JupyterHub user URL handler to use a custom
    handler and allow Dataproc Hub to do redirect instead of proxying.

    Handlers are tuples of the form (regex_path, handler_class).

    Order of the element in the handlers list matters!!!
    """
    super().init_handlers()
    self.handlers = self.new_prefixed + self.handlers
    self.log.debug(self.handlers)


main = DataprocHub.launch_instance

if __name__ == '__main__':
  main()
