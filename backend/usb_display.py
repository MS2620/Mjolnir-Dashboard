import usb.core
import usb.util
import struct
import time
import io
import sys
from PIL import Image

VID = 0x87AD
PID = 0x70DB

USB_TIMEOUT_MS = 2000
MAX_PACKET_SIZE = 512
HEADER_LEN = 64
CHUNK_SIZE = 16 * 1024
ZLP_MULTIPLE = 512

MAGIC = 0x78563412  # little-endian → bytes: 12 34 56 78
CMD_JPEG = 2


class MjolnirDisplay:
    def __init__(self):
        self.dev = None
        self.ep_out = None
        self.ep_in = None
        self.width = 640
        self.height = 480
        self.jpeg_quality = 85
        self.serial = None

    def open(self):
        self.dev = usb.core.find(idVendor=VID, idProduct=PID)
        if self.dev is None:
            raise RuntimeError("Mjolnir Vision device not found (87AD:70DB)")

        try:
            self.dev.set_configuration()
        except usb.core.USBError:
            pass

        cfg = self.dev.get_active_configuration()
        iface = None
        ep_out = ep_in = None

        for intf in cfg:
            ep_out_tmp = usb.util.find_descriptor(
                intf,
                custom_match=lambda e: (
                    usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
                    and usb.util.endpoint_type(e.bmAttributes) == usb.util.ENDPOINT_TYPE_BULK
                ),
            )
            if ep_out_tmp is None:
                continue
            ep_in_tmp = usb.util.find_descriptor(
                intf,
                custom_match=lambda e: (
                    usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
                    and usb.util.endpoint_type(e.bmAttributes) == usb.util.ENDPOINT_TYPE_BULK
                ),
            )
            iface = intf
            ep_out = ep_out_tmp
            ep_in = ep_in_tmp
            break

        if iface is None or ep_out is None:
            raise RuntimeError("No bulk OUT endpoint found")

        usb.util.claim_interface(self.dev, iface.bInterfaceNumber)

        try:
            self.serial = usb.util.get_string(self.dev, self.dev.iSerialNumber)
        except usb.core.USBError:
            pass

        self.ep_out = ep_out
        self.ep_in = ep_in

        print(f"Connected: serial={self.serial}  ep_out=0x{self.ep_out.bEndpointAddress:02x}  ep_in=0x{self.ep_in.bEndpointAddress:02x}")
        time.sleep(0.2)  # wait a bit before handshake
        self._handshake()

    def _handshake(self):
        hs = bytearray(HEADER_LEN)
        struct.pack_into("<I", hs, 0x00, MAGIC)
        struct.pack_into("<I", hs, 0x38, 1)

        print("Sending handshake (64 bytes)...")
        self.dev.write(self.ep_out.bEndpointAddress, hs, timeout=USB_TIMEOUT_MS)

        print("Reading handshake reply...")
        # Try 1024 first, then 64 if timeout
        reply = None
        for size in [1024, 64]:
            try:
                data = self.dev.read(self.ep_in.bEndpointAddress, size, timeout=USB_TIMEOUT_MS)
                reply = bytes(data)  # ensure bytes, not array
                print(f"Got {len(reply)} bytes")
                break
            except usb.core.USBTimeoutError:
                continue

        if reply is None:
            print("No handshake reply received")
            return

        print(f"Handshake reply: {len(reply)} bytes")
        if len(reply) >= 64:
            print(f"  first 64 bytes: {reply[:64].hex()}")
            if len(reply) >= 37:
                pm = reply[24]
                sub = reply[36]
                print(f"  PM={pm}  SUB={sub}")
        else:
            print(f"  short reply: {reply.hex()}")

    def send_frame(self, image: Image.Image):
        if image.size != (self.width, self.height):
            image = image.resize((self.width, self.height), Image.LANCZOS)

        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=self.jpeg_quality)
        payload = buf.getvalue()

        hdr = bytearray(HEADER_LEN)
        struct.pack_into("<I", hdr, 0x00, MAGIC)
        struct.pack_into("<I", hdr, 0x04, CMD_JPEG)
        struct.pack_into("<I", hdr, 0x08, self.width)
        struct.pack_into("<I", hdr, 0x0C, self.height)
        struct.pack_into("<I", hdr, 0x38, 2)
        struct.pack_into("<I", hdr, 0x3C, len(payload))

        packet = bytes(hdr) + payload
        total_len = len(packet)

        offset = 0
        while offset < total_len:
            chunk = packet[offset : offset + CHUNK_SIZE]
            self.dev.write(self.ep_out.bEndpointAddress, chunk, timeout=USB_TIMEOUT_MS)
            offset += len(chunk)

        if total_len % ZLP_MULTIPLE == 0:
            self.dev.write(self.ep_out.bEndpointAddress, b"", timeout=USB_TIMEOUT_MS)

    def close(self):
        try:
            usb.util.release_interface(self.dev, 0)
        except Exception:
            pass
        if self.dev is not None:
            try:
                usb.util.dispose_resources(self.dev)
            except Exception:
                pass
        self.dev = None