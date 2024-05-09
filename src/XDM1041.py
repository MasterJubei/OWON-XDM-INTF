#!/usr/bin/env python3
# MIT License
#
# Copyright (c) 2021 TheHWcave
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
import serial
import serial.tools.list_ports
from enum import Enum
from time import sleep


class SCPI:
    """ Serial SCPI interface """

    _SIF: None

    def __init__(self, port_dev=None, speed=9600, timeout=2):
        self._SIF = serial.Serial(
            port=port_dev,
            baudrate=speed,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=timeout,
        )

    def __del__(self):
        try:
            self._SIF.close()
        except:
            pass

    def readdata(self):
        """ Read a SCPI response from the serial port terminated by CR LF
        any no-UTF8 characters are replaced by backslash-hex code """
        buf = bytearray(0)
        n = 0
        while True:
            data = self._SIF.read(64)
            if len(data) > 0:
                buf.extend(data)
                if len(buf) >= 2:
                    if buf[-2:] == b"\r\n":
                        break
            else:
                n = n + 1
                if n > 2:
                    buf = bytearray(0)
                    break

        # for b in buf: print(hex(b)+' ',end='')
        # print()
        res = buf.decode(errors="backslashreplace")
        x = res.find("\r\n")
        if x == len(res) - 2:
            res = res.strip()
        else:
            res = ""
        return res

    def sendcmd(self, msg, getdata=True):
        """ Sends a command over SCPI. If getdata is True, it waits for
        the response and returns it """
        msg = msg + "\n"
        self._SIF.write(msg.encode("ascii"))
        if getdata:
            res = self.readdata()
        else:
            res = None
        return res


class XdmMeter:
    class cmds(Enum):
        VOLT    =  ("VOLT",)
        VOLT_AC =  ("VOLT:AC",)
        CURR    =  ("CURR",)
        CURR_AC =  ("CURR:AC",)
        RES     =  ("RES",)
        CAP     =  ("CAP",)
        FREQ    =  ("FREQ",)
        PER     =  ("PER",)
        TEMP    =  ("TEMP",)
        DIODE   =  ("DIOD",)
        CONT    =  ("CONT",)

        def __str__(self):
            return self.name

    def __init__(self, port):
        self.MiniBM = SCPI(port, speed=115200, timeout=0.1)
        self.id = self.MiniBM.sendcmd("*IDN?")
        if self.id == "":
            self.MiniBM = None
            print("device at " + port + " does not respond")
        else:
            print(self.id)

    def get_response(self, cmd, Numeric=False):
        """ Sends a command (that will trigger a response) and returns
        that response

        Because of bugs in the XDM1041, it may sometimes timeout and
        sometimes return multiple responses. For timeouts, a "?" is
        returned. Multip le responses are discarded.

        It also translates some of the weird characters send by the
        XDM1041 for non-ASCII chars """
        Successful = False
        n = 0
        while not Successful:
            s = self.MiniBM.sendcmd(cmd)
            if s != "":
                if Numeric:
                    try:
                        v = float(s)
                        Successful = True
                        Res = v
                    except ValueError:
                        Successful = True
                        Res = 0
                else:
                    Successful = True
                    if s.endswith("\\xa6\\xb8"):
                        s = s[:-8] + "Ohm"
                    elif s.endswith("\\xa6\\xccF"):
                        s = s[:-9] + "uF"
                    elif s.endswith('"'):
                        s = s.strip('"')
                    Res = s
            else:
                sleep(0.1)
                n = n + 1
                if n > 5:
                    if Numeric:
                        Res = 0
                    else:
                        Res = "?"
                    break
        return Res

    def set_mode(self, mode: cmds):
        self.get_response(f"CONF:{mode}")

    def get_mode(self):
        return self.get_response("FUNC?", Numeric=False)

    def get_measurement(self):
        return self.get_response("MEAS?", Numeric=True)
    
    def close(self):
        self.MiniBM.__del__()


if __name__ == "__main__":
    # Search for the XDM1041/1241
    ports = serial.tools.list_ports.comports()
    port = ""

    for p in ports:
        if "CH340" in p.description in p.description:
            port = p.device
            print(f"XDM Found: {p.device} {p.description} {p.hwid}")

    if port == "":
        print("XDM not found")
        port = "COM23"

    xdm = XdmMeter(port)

    resp = xdm.get_mode()
    print(resp)

    print(xdm.cmds.VOLT)
    resp = xdm.set_mode(xdm.cmds.VOLT)

    resp = xdm.get_measurement()

    resp = xdm.get_response("MEAS?", Numeric=True)
    print(resp)
