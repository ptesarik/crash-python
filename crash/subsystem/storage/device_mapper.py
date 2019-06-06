# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb

from crash.util import container_of
from crash.util.symbols import Types
from crash.subsystem.storage import block_device_name
from crash.subsystem.storage.decoders import Decoder, decode_bio

class ClonedBioReqDecoder(Decoder):
    """
    Decodes a request-based device mapper cloned bio

    This decodes a cloned bio generated by request-based device mapper targets.

    Args:
        bio: A ``struct bio`` generated by a request-based device mapper
            target.  The value must be of type ``struct bio``.

    """
    _types = Types([ 'struct dm_rq_clone_bio_info *' ])
    __endio__ = 'end_clone_bio'
    _description = '{:x} bio: Request-based Device Mapper on {}'

    _get_clone_bio_rq_info = None

    def __init__(self, bio: gdb.Value):
        super().__init__()
        self.bio = bio
        if self._get_clone_bio_rq_info is None:
            if 'clone' in self._types.dm_rq_clone_bio_info_p_type.target():
                getter = self._get_clone_bio_rq_info_3_7
            else:
                getter = self._get_clone_bio_rq_info_old
            self._get_clone_bio_rq_info = getter

    def interpret(self):
        """Interprets the request-based device mapper bio to populate its
        attributes"""
        self.info = self._get_clone_bio_rq_info(self.bio)
        self.tio = self.info['tio']

    def __str__(self):
        self._description.format(int(self.bio),
                                block_device_name(self.bio['bi_bdev']))

    def __next__(self):
        return decode_bio(self.info['orig'])

    def _get_clone_bio_rq_info_old(self, bio):
        return bio['bi_private'].cast(self._types.dm_rq_clone_bio_info_p_type)

    def _get_clone_bio_rq_info_3_7(self, bio):
        return container_of(bio, self._types.dm_rq_clone_bio_info_p_type, 'clone')

ClonedBioReqDecoder.register()

class ClonedBioDecoder(Decoder):
    """
    Decodes a bio-based device mapper cloned bio

    This method decodes  cloned bio generated by request-based
    device mapper targets.

    Args:
        bio: A ``struct bio`` generated by a bio-based device mapper target.
            The value must be of type ``struct bio``.

    Attributes:
        bio (:obj:`gdb.Value`): A ``struct bio`` generated by a bio-based
            device mapper target.  The value is of type ``struct bio``.

        next_bio (:obj:`gdb.Value`): The struct bio that generated this one.
            The value is of type ``struct bio``.

        tio (:obj:`gdb.Value`): The dm target i/o operation for this bio.  The
            value is of type ``struct dm_target_io``.
    """
    _types = Types([ 'struct dm_target_io *' ])
    _get_clone_bio_tio = None
    __endio__ = 'clone_endio'
    _description = "{:x} bio: device mapper clone: {}[{}] -> {}[{}]"

    def __init__(self, bio: gdb.Value):
        super().__init__()
        self.bio = bio

        if self._get_clone_bio_tio is None:
            if 'clone' in self._types.dm_target_io_p_type.target():
                getter = self._get_clone_bio_tio_3_15
            else:
                getter = self._get_clone_bio_tio_old
            self._get_clone_bio_tio = getter

    def interpret(self):
        """Interprets the cloned device mapper bio to populate its
        attributes"""
        self.tio = self._get_clone_bio_tio(self.bio)
        self.next_bio = self.tio['io']['bio']

    def __str__(self):
        return self._description.format(
                                int(self.bio),
                                block_device_name(self.bio['bi_bdev']),
                                int(self.bio['bi_sector']),
                                block_device_name(self.next_bio['bi_bdev']),
                                int(self.next_bio['bi_sector']))

    def __next__(self):
        return decode_bio(self.next_bio)

    def _get_clone_bio_tio_old(self, bio):
        return bio['bi_private'].cast(self._types.dm_target_io_p_type)

    def _get_clone_bio_tio_3_15(self, bio):
        return container_of(bio['bi_private'],
                            self._types.dm_clone_bio_info_p_type, 'clone')

ClonedBioDecoder.register()
