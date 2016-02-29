from functools import partial
from ubuntui.ev import EventLoop
from conjure.async import AsyncPool
from conjure.juju import Juju
from conjure.api.models import model_info
from conjure.charm import get_bundle
from conjure.models.charm import CharmModel
from conjure.ui.views.deploy import DeployView
from conjure.controllers.finish import FinishController

from bundleplacer.config import Config
from bundleplacer.fixtures.maas import FakeMaasState
from bundleplacer.placerview import PlacerView
from bundleplacer.controller import PlacementController
import q


class DeployController:

    def __init__(self, common, controller):
        self.common = common
        self.controller = controller
        self.controller_info = model_info(self.controller)

    def finish(self, *args):
        """ handles deployment
        """
        FinishController(self.common).render()

    def render(self):
        # Grab bundle and deploy or render placement if MAAS
        if self.model_info['ProviderType'] == 'maas':
            bundle = get_bundle(CharmModel.to_entity())
            bundleplacer_cfg = Config(
                'bundle-placer',
                {'bundle': bundle,
                 'metadata': self.common['config']['metadata']})
            placement_controller = PlacementController(
                config=bundleplacer_cfg,
                maas_state=FakeMaasState())
            mainview = PlacerView(placement_controller,
                                  bundleplacer_cfg,
                                  self.finish)
            self.common['ui'].set_header(
                title="Bundle Editor: {}".format(
                    self.common['config']['summary']),
                excerpt="Choose where your services should be "
                "placed in your available infrastructure"
            )
            self.common['ui'].set_subheader("Machine Placement")
            self.common['ui'].set_body(mainview)
            mainview.update()
        else:
            view = DeployView(self.common, self.finish)
            self.common['ui'].set_header(
                title="Deploying: {}".format(CharmModel.to_path())
            )
            self.common['ui'].set_body(view)

            def read_status(*args):
                services = Juju.client.Client(request="FullStatus")
                services = "\n".join(services.keys())
                view.set_status(services)
                EventLoop.set_alarm_in(3, read_status)

            def error(*args):
                print(args)
            AsyncPool.submit(
                partial(Juju.deploy_bundle, CharmModel.to_path()))
            EventLoop.set_alarm_in(1, read_status)
