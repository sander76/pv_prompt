from enum import Enum


class Nd(Enum):
    # these keys cannot be changed as they are hard wired into the keypad
    # component.
    open = b'\x00\x03RU\x00'
    close = b'\x00\x03RD\x00'
    tiltopen = b'\x00\x03RR\x00'
    tiltclose = b'\x00\x03RL\x00'
    stop = b'\x00\x03RS\x00'

    JOG = b'\x00\x03cj\x01'
    CONNECT = b'\x00\x01N\x00\x01A'
    NETWORKADD = b'\x00\x01N'
    GROUP_ADD = b'\x00\x01A'
    RESET = b'\x00\x03#@r'
    STARTPROGRAM = b'\x00\x04#LPE'
    SAVE_POSITION_TOP = b'\x00\x04#LPO'
    SAVE_POSITION_BOTTOM = b'\x00\x04#LPC'
    ENABLE_SLAT = b'\x00\x04#LPr'
    SAVE_SLAT_OPEN = b'\x00\x04#LTO'
    REVERSE = b'\x00\x02#x'  # old

    TO_HUB_ID = b'\x00\x01z'
    NETWORK_RESET = b'\x00\x04@r?\x01'
    SET_DONGLE_ID = b'set_id'

    SAVE_VENETIAN_SLAT = b'\x00\x04#LPR'

    # motor types.
    M25S_PLEATED_FREE = b'\x00\x04#DS\x11'
    M25S_PLEATED_TENSIONED = b'\x00\x04#DSQ'
    M25S_DUETTE_FREE = b'\x00\x04#DS\x06'
    M25S_DUETTE_TENSIONED = b'\x00\x04#DSF'
    M25S_VVB_LEFT_STACK = b'\x00\x04#DS6'
    M25S_VVB_RIGHT_STACK = b'\x00\x04#DS7'
    M25S_VVB_SPLIT_STACK = b'\x00\x04#DS8'
    M25S_VVB_CENTER_STACK = b'\x00\x04#DS?'
    M25S_VENETIAN_16MM = b'\x00\x04#DS>'
    M25S_VENETIAN_25MM = b'\x00\x04#DS~'
    M25T_ROLLER = b'\x00\x04#DS*'
    TWIST = b'\x00\x04#DS,'

    # motor orientations.
    ORIENT_VVB_LEFT = b'\x00\x03#dR'
    ORIENT_VVB_RIGHT = b'\x00\x03#dL'
    ORIENT_VVB_CENTER = b'\x00\x03#dC'
    ORIENT_VVB_UPRIGHT_LEFT = b'\x00\x03#d\xB6'
    ORIENT_VVB_UPRIGHT_RIGHT = b'\x00\x03#d\xB0'
    ORIENT_VVB_UPRIGHT_CENTER = b'\x00\x03#d\xA7'
    ORIENT_BACKROLLER_LEFT = b'\x00\x03#dL'  # works with venetian M25S too
    ORIENT_BACKROLLER_RIGHT = b'\x00\x03#dR'  # works with venetian M25S too

    ORIENT_M25S_DUETTE_LEFT = b'\x00\x03#dR'
    ORIENT_M25S_DUETTE_RIGHT = b'\x00\x03#dL'
