# Copyright (c) 2001-2015 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program. If not, see <https://www.gnu.org/licenses/>. For any questions
# about this software or licensing, please email opensource@seagate.com or
# cortx-questions@seagate.com.

"""
 ****************************************************************************
  Description:       C data structures for creating ATA & SG_IO objects 
 ****************************************************************************
"""

import ctypes


class AtaCmd(ctypes.Structure):
  """ATA Command Pass-Through
     http://www.t10.org/ftp/t10/document.04/04-262r8.pdf"""

  _fields_ = [
      ('opcode', ctypes.c_ubyte),
      ('protocol', ctypes.c_ubyte),
      ('flags', ctypes.c_ubyte),
      ('features_filler', ctypes.c_ubyte),
      ('features', ctypes.c_ubyte),
      ('sector_count_filler', ctypes.c_ubyte),
      ('sector_count', ctypes.c_ubyte),
      ('lba_low_filler', ctypes.c_ubyte),
      ('lba_low', ctypes.c_ubyte),
      ('lba_mid_filler', ctypes.c_ubyte),
      ('lba_mid', ctypes.c_ubyte),
      ('lba_high_filler', ctypes.c_ubyte),
      ('lba_high', ctypes.c_ubyte),
      ('device', ctypes.c_ubyte),
      ('command', ctypes.c_ubyte),
      ('control', ctypes.c_ubyte) ]


class SgioHdr(ctypes.Structure):
  """<scsi/sg.h> sg_io_hdr_t."""

  _fields_ = [
      ('interface_id', ctypes.c_int),
      ('dxfer_direction', ctypes.c_int),
      ('cmd_len', ctypes.c_ubyte),
      ('mx_sb_len', ctypes.c_ubyte),
      ('iovec_count', ctypes.c_ushort),
      ('dxfer_len', ctypes.c_uint),
      ('dxferp', ctypes.c_void_p),
      ('cmdp', ctypes.c_void_p),
      ('sbp', ctypes.c_void_p),
      ('timeout', ctypes.c_uint),
      ('flags', ctypes.c_uint),
      ('pack_id', ctypes.c_int),
      ('usr_ptr', ctypes.c_void_p),
      ('status', ctypes.c_ubyte),
      ('masked_status', ctypes.c_ubyte),
      ('msg_status', ctypes.c_ubyte),
      ('sb_len_wr', ctypes.c_ubyte),
      ('host_status', ctypes.c_ushort),
      ('driver_status', ctypes.c_ushort),
      ('resid', ctypes.c_int),
      ('duration', ctypes.c_uint),
      ('info', ctypes.c_uint)]
