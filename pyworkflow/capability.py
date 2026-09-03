# **************************************************************************
# *
# * Unidad de  Bioinformatica of Centro Nacional de Biotecnologia , CSIC
# *
# * This program is free software; you can redistribute it and/or modify
# * it under the terms of the GNU General Public License as published by
# * the Free Software Foundation; either version 3 of the License, or
# * (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program; if not, write to the Free Software
# * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
# * 02111-1307  USA
# *
# *  All comments concerning this program package may be sent to the
# *  e-mail address 'scipion@cnb.csic.es'
# *
# **************************************************************************
"""
This module defines CapabilityProvider, the base class a plugin subclasses
to register that it implements a capability (import, or any future one) for
one or more protocol classes, contributing its own form fields dynamically.

See .ai/capability-providers.md for the full contract and discovery details.
"""


class CapabilityProvider:
    """ Base class for a plugin-contributed implementation of a capability
    for one or more protocol classes.

    Subclasses declare, as class attributes:

    - CAPABILITY: identifies the family of capability this provider
      implements (e.g. 'import'). Each capability family defines its own
      CapabilityProvider subclass adding whatever execution method(s) it
      needs (see ImportCapabilityProvider below) -- CapabilityProvider
      itself stays deliberately minimal so new capability families never
      require changes to the discovery/registration machinery.
    - TARGET_PROTOCOLS: list of protocol class names (plain class name,
      not fully-qualified -- same convention as Wizard._targets) this
      provider applies to.
    - KEY: stable string identity for this provider's choice. Persisted
      as the value of the protocol's selector param (see
      pyworkflow.protocol.params.KeyedEnumParam) and used in `condition=`
      expressions -- must never change once released, and must never be a
      plain list position (unlike the legacy EnumParam-ordinal pattern
      this replaces).
    - LABEL: text shown for this choice in the UI.

    Discovered via the 'pyworkflow.capability_provider' entry-point group
    -- see Domain.getCapabilityProviders/findCapabilityProviders in
    pyworkflow.plugin.
    """

    CAPABILITY = None
    TARGET_PROTOCOLS = []
    KEY = None
    LABEL = None

    def defineParams(self, form, condition):
        """ Override to add the form fields this provider needs.
        Every param added here must be gated by `condition` (the exact
        string to pass as `condition=` to form.addParam) so the fields
        only show up once this provider is the selected choice.
        """
        pass


class ImportCapabilityProvider(CapabilityProvider):
    """ CapabilityProvider specialization for import protocols. """

    CAPABILITY = 'import'

    # Expected extension(s) of the input file this provider's form
    # field(s) point to, e.g. ['cs']. Used for validation instead of the
    # legacy positional importExts[importFrom.get() - 1] lookup.
    FILE_EXTENSIONS = []

    def getFilePath(self, protocol):
        """ Return the raw input file path this provider's form field(s)
        point to on `protocol` (e.g. protocol.csFile.get()). Called by the
        base import protocol before validating/running the import. """
        raise NotImplementedError

    def validate(self, protocol):
        """ Return a list of validation error strings for `protocol`
        (empty list if valid), same convention as Protocol._validate(). """
        return []

    def importFrom(self, protocol):
        """ Perform the import for `protocol` using this provider's format.
        Replaces the logic that today lives inline in each import
        protocol's getImportClass()-style dispatch.
        """
        raise NotImplementedError
