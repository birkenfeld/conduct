# *****************************************************************************
# conduct - CONvenient Construction Tool
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# Module authors:
#   Alexander Lenz <alexander.lenz@posteo.de>
#
# *****************************************************************************

import pprint
from os import path
from collections import OrderedDict

import conduct
from conduct.param import Parameter
from conduct.util import AttrStringifier, ObjectiveOrderedDict, Referencer


class Chain(object):
    def __init__(self, name, paramValues):
        self.name = name
        self.steps = OrderedDict()
        self.params = {}

        self._chainDef = {}

        self._loadChainFile()
        self._applyParamValues(paramValues)


    def build(self):
        for step in self.steps.values():
            step.build()

    @property
    def parameters(self):
        return self._chainDef['parameters']

    def _applyParamValues(self, values):
        for name, definition in self.parameters.iteritems():
            if name in values:
                self.params[name] = values[name]
            elif definition.default is not None:
                self.params[name] = definition.default
            else:
                raise RuntimeError('Mandatory parameter %s is missing' % name)

    def _loadChainFile(self):
        # determine chain file location
        chainDir = conduct.cfg['conduct']['chaindir']
        chainFile = path.join(chainDir, '%s.py' % self.name)

        if not path.exists(chainFile):
            raise IOError('Chain file for \'%s\' not found (Should be: %s)'
                          % (self.name, chainFile))

        content = open(chainFile).read()

        # prepare exection namespace
        ns = {
            'Parameter' : Parameter,
            'Step' : lambda cls, **params: ('step:%s' % cls, params),
            'Chain' : lambda cls, **params: ('chain:%s' % cls, params),
            'steps' : ObjectiveOrderedDict(),
            'ref' : lambda refAdr: Referencer(refAdr),
        }

        # execute and extract all the interesting data
        exec content in ns

        for entry in ['description', 'parameters']:
            self._chainDef[entry] = ns[entry]

        self._chainDef['steps'] = ns['steps'].entries

        # create build steps
        self._createSteps()

    def _createSteps(self):
        for name, definition in self._chainDef['steps'].iteritems():
            # name should be step:name or chain:name
            entryType, entryName = definition[0].split(':')

            if entryType == 'step':
                # for steps, the entryName should be a full path (mod.class)
                clsMod, _, clsName = entryName.rpartition('.')
                mod = __import__(clsMod)
                cls = getattr(mod, clsName)

                self.steps[name] = cls(name, definition[1], self)
            else:
                # TODO parameter forwarding
                self.steps[name] = Chain(entryName)


