"""Constants for Govee H7172 BLE integration."""

DOMAIN = "govee_h7172_ble"

# BLE UUIDs (from APK reverse engineering)
SERVICE_UUID = "00010203-0405-0607-0809-0a0b0c0d1910"
WRITE_CHAR_UUID = "00010203-0405-0607-0809-0a0b0c0d2b11"  # write-without-response
NOTIFY_CHAR_UUID = "00010203-0405-0607-0809-0a0b0c0d2b10"  # read, notify

# BLE packet headers
HEADER_APP_TO_DEVICE = 0x33   # app → device
HEADER_DEVICE_TO_APP = 0xAA   # device → app (notifications)
PACKET_LEN = 20

# BLE command types (from BleProtocolConstants reverse engineering)
CMD_WORK_STATUS = 0x19   # work status query/notify
CMD_MODE = 0x05          # mode query/notify
CMD_ALARM = 0x17         # alarm/abnormal info
CMD_SWITCH_INFO = 0x1F   # switch states (ice full, power, etc.)

# Switch types (from BaseSwitchControllerKt)
SWITCH_TYPE_POWER = 0x06    # main power on/off
SWITCH_TYPE_ICE_FULL = 0x07 # ice full sensor

# Work status codes (from WorkStatus enum)
WORK_STATUS = {
    0: "idle",
    1: "ice_making",
    2: "ice_make_finish",
    3: "washing",
    4: "wash_finish",
    5: "reservation",
}

# Mode codes (from Mode enum)
MODE = {
    1: "large",
    2: "medium",
    3: "small",
}

# BLE advertising manufacturer ID (from live scan: bleak parses the 2-byte company ID
# as little-endian int; raw bytes [0x02, 0x88] → key 0x8802 = 34818)
GOVEE_MANUFACTURER_ID = 0x8802

# Config entry keys
CONF_ADDRESS = "address"

# Polling interval for connected BLE queries (seconds)
POLL_INTERVAL = 30
