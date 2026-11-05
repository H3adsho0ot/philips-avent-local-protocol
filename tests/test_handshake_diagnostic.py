"""Standard-library-only checks with synthetic data; no network or devices."""
import base64
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

PATH=Path(__file__).resolve().parents[1]/'tools/avent_handshake_diagnostic.py'
spec=importlib.util.spec_from_file_location('avent_diagnostic_test',PATH)
tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)
KEY=bytes(range(16))
PAYLOAD=b'SYNTHETIC_SECRET'


class Peer:
    def __init__(self,mode='markers'):
        self.mode=mode;self.pending=bytearray();self.sent=[];self.closed=False;self.timeouts=[]
    def __enter__(self):return self
    def __exit__(self,*args):self.closed=True
    def settimeout(self,value):self.timeouts.append(value)
    def sendall(self,packet):
        self.sent.append(packet)
        ack=bytearray(tool.frame(0x8001,0,bytes(8)+packet[11:27]))
        if self.mode=='crc':ack[4]^=1
        self.pending.extend(ack)
        if self.mode=='markers':
            self.pending.extend(tool.frame(0x0930,1,PAYLOAD)+tool.frame(0x0931,2,PAYLOAD))
        if self.mode=='flood':self.pending.extend(tool.frame(0x092d,3,PAYLOAD)*100)
    def recv(self,size):
        if not self.pending:
            if self.mode=='timeout':raise TimeoutError
            return b''
        n=min(size,3,len(self.pending));data=bytes(self.pending[:n]);del self.pending[:n];return data


class DiagnosticTests(unittest.TestCase):
    def test_key_encodings(self):
        self.assertEqual(tool.parse_pairing_key('base64:'+base64.b64encode(KEY).decode()),KEY)
        self.assertEqual(tool.parse_pairing_key('hex:'+KEY.hex()),KEY)
        self.assertEqual(tool.parse_pairing_key('0123456789abcdef'),b'0123456789abcdef')
        for value in ('short','base64:!','base64:AA==','hex:ff','base64:ä'):
            with self.subTest(value=value),self.assertRaises(ValueError):tool.parse_pairing_key(value)

    def test_one_login_profiles_fragmentation_and_redaction(self):
        for profile,trailer in [('legacy',b'0\0'),('scd973-001',b'0010\0')]:
            peer=Peer()
            with self.subTest(profile=profile),patch.object(tool.socket,'create_connection',return_value=peer) as connect:
                report=tool.diagnose_handshake('synthetic-camera.test',KEY,profile)
            connect.assert_called_once_with(('synthetic-camera.test',6000),timeout=5)
            self.assertEqual(len(peer.sent),1);self.assertEqual(peer.sent[0][27:],trailer)
            self.assertEqual(report['scd973_markers_seen'],['0x0930','0x0931'])
            self.assertEqual(report['outcome'],'scd973_markers_observed')
            self.assertFalse(report['authenticated']);self.assertTrue(report['login_ack_seen'])
            self.assertTrue(peer.closed)
            for row in report['frames']:
                self.assertEqual(set(row),{'direction','opcode','sequence','frame_bytes','body_bytes'})
            for private in ('SYNTHETIC_SECRET','synthetic-camera.test',KEY.hex(),peer.sent[0][11:27].hex()):
                self.assertNotIn(private,json.dumps(report))

    def test_error_and_frame_limits_never_authenticate(self):
        for mode,outcome in [('crc','invalid_frame'),('timeout','timeout'),('closed','peer_closed'),('flood','frame_limit')]:
            peer=Peer(mode)
            with self.subTest(mode=mode),patch.object(tool.socket,'create_connection',return_value=peer):
                report=tool.diagnose_handshake('synthetic-camera.test',KEY)
            self.assertEqual(report['outcome'],outcome);self.assertFalse(report['authenticated'])
            self.assertLessEqual(len(report['frames']),65)
            self.assertEqual(len(peer.sent),1);self.assertTrue(peer.closed)

    def test_network_error_details_are_not_exported(self):
        with patch.object(tool.socket,'create_connection',side_effect=OSError('PRIVATE_HOST')):
            report=tool.diagnose_handshake('synthetic-camera.test',KEY)
        self.assertEqual(report['outcome'],'network_error');self.assertNotIn('PRIVATE_HOST',json.dumps(report))

    def test_invalid_parameters_do_not_connect(self):
        with patch.object(tool.socket,'create_connection') as connect:
            for key,profile,timeout in [(b'short','legacy',8),(KEY,'unknown',8),(KEY,'legacy',0)]:
                with self.assertRaises(ValueError):tool.diagnose_handshake('synthetic-camera.test',key,profile,timeout)
            connect.assert_not_called()

    def test_slow_partial_frame_deadline(self):
        peer=Peer();peer.pending.extend(tool.frame(0x8001,0,PAYLOAD))
        with patch.object(tool.time,'monotonic',side_effect=[0,1,2]),self.assertRaises(TimeoutError):
            tool.ControlWire(peer).read(deadline=2)
        self.assertEqual(peer.timeouts,[2,1])

    def test_cli_report_and_hidden_key(self):
        out=io.StringIO();err=io.StringIO();peer=Peer()
        entered='base64:'+base64.b64encode(KEY).decode()
        with patch.object(tool.socket,'create_connection',return_value=peer),patch.object(tool.getpass,'getpass',return_value=entered),contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            self.assertEqual(tool.main(['synthetic-camera.test']),0)
        self.assertFalse(json.loads(out.getvalue())['authenticated'])
        self.assertNotIn(entered,out.getvalue()+err.getvalue())

    def test_no_echo_fallback(self):
        with patch.object(tool.socket,'create_connection') as connect,patch.object(tool.getpass,'getpass',side_effect=tool.getpass.GetPassWarning),contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(tool.main(['synthetic-camera.test']),2)
            connect.assert_not_called()


if __name__=='__main__':unittest.main()
