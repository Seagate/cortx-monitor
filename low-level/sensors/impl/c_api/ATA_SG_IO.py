"""
 ****************************************************************************
 Filename:          ATA_SG_IO.py
 Description:       C data structures for creating ATA & SG_IO objects 
 Creation Date:     10/28/2015
 Author:            Jake Abernathy

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
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
