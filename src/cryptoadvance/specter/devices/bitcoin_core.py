import os
from bip32 import BIP32
from mnemonic import Mnemonic
from ..descriptor import AddChecksum
from ..device import Device
from ..helpers import alias, convert_xpub_prefix, encode_base58_checksum, get_xpub_fingerprint
from ..key import Key

class BitcoinCore(Device):
    def __init__(self, name, alias, device_type, keys, fullpath, manager):
        Device.__init__(self, name, alias, device_type, keys, fullpath, manager)
        self.hwi_support = False
        self.exportable_to_wallet = False
        self.hot_wallet = True

    @staticmethod
    def generate_mnemonic():
        # Generate words list
        # TODO: Generate randomness with secrets library
        mnemo = Mnemonic("english")
        words = mnemo.generate(strength=256)
        return words
        

    def setup_device(self, mnemonic, wallet_manager):
        seed = Mnemonic.to_seed(mnemonic)
        mainnet_xprv = seed_to_hd_master_key(seed, testnet=False)
        testnet_xprv = seed_to_hd_master_key(seed, testnet=True)
        wallet_name = os.path.join(wallet_manager.cli_path + '_hotstorage', self.alias)
        wallet_manager.cli.createwallet(wallet_name, False, True)
        cli = wallet_manager.cli.wallet(wallet_name)
        # TODO: Maybe more than 1000? Maybe add mechanism to add more later.
        ## NOTE: This will work only on the network the device was added, so hot devices should be filtered out by network.
        cli.importmulti([
            { 'desc': AddChecksum('sh(wpkh({}/49h/0h/0h/0/*))'.format(mainnet_xprv)), 'range': 1000, 'timestamp': 'now'},
            { 'desc': AddChecksum('sh(wpkh({}/49h/0h/0h/1/*))'.format(mainnet_xprv)), 'range': 1000, 'timestamp': 'now'},
            { 'desc': AddChecksum('wpkh({}/84h/0h/0h/0/*)'.format(mainnet_xprv)), 'range': 1000, 'timestamp': 'now'},
            { 'desc': AddChecksum('wpkh({}/84h/0h/0h/1/*)'.format(mainnet_xprv)), 'range': 1000, 'timestamp': 'now'},
            { 'desc': AddChecksum('sh(wpkh({}/48h/0h/0h/1h/0/*))'.format(mainnet_xprv)), 'range': 1000, 'timestamp': 'now'},
            { 'desc': AddChecksum('sh(wpkh({}/48h/0h/0h/1h/1/*))'.format(mainnet_xprv)), 'range': 1000, 'timestamp': 'now'},
            { 'desc': AddChecksum('wpkh({}/48h/0h/0h/2h/0/*)'.format(mainnet_xprv)), 'range': 1000, 'timestamp': 'now'},
            { 'desc': AddChecksum('wpkh({}/48h/0h/0h/2h/1/*)'.format(mainnet_xprv)), 'range': 1000, 'timestamp': 'now'},
            { 'desc': AddChecksum('sh(wpkh({}/49h/1h/0h/0/*))'.format(testnet_xprv)), 'range': 1000, 'timestamp': 'now'},
            { 'desc': AddChecksum('sh(wpkh({}/49h/1h/0h/1/*))'.format(testnet_xprv)), 'range': 1000, 'timestamp': 'now'},
            { 'desc': AddChecksum('wpkh({}/84h/1h/0h/0/*)'.format(testnet_xprv)), 'range': 1000, 'timestamp': 'now'},
            { 'desc': AddChecksum('wpkh({}/84h/1h/0h/1/*)'.format(testnet_xprv)), 'range': 1000, 'timestamp': 'now'},
            { 'desc': AddChecksum('sh(wpkh({}/48h/1h/0h/1h/0/*))'.format(testnet_xprv)), 'range': 1000, 'timestamp': 'now'},
            { 'desc': AddChecksum('sh(wpkh({}/48h/1h/0h/1h/1/*))'.format(testnet_xprv)), 'range': 1000, 'timestamp': 'now'},
            { 'desc': AddChecksum('wpkh({}/48h/1h/0h/2h/0/*)'.format(testnet_xprv)), 'range': 1000, 'timestamp': 'now'},
            { 'desc': AddChecksum('wpkh({}/48h/1h/0h/2h/1/*)'.format(testnet_xprv)), 'range': 1000, 'timestamp': 'now'},
        ])

        bip32 = BIP32.from_seed(seed)
        xpubs = ""
        master_fpr = get_xpub_fingerprint(bip32.get_xpub_from_path('m/0h')).hex()
        # Nested Segwit
        xpub = bip32.get_xpub_from_path('m/49h/0h/0h')
        ypub = convert_xpub_prefix(xpub, b'\x04\x9d\x7c\xb2')
        xpubs += "[%s/49'/0'/0']%s\n" % (master_fpr, ypub)
        # native Segwit
        xpub = bip32.get_xpub_from_path('m/84h/0h/0h')
        zpub = convert_xpub_prefix(xpub, b'\x04\xb2\x47\x46')
        xpubs += "[%s/84'/0'/0']%s\n" % (master_fpr, zpub)
        # Multisig nested Segwit
        xpub = bip32.get_xpub_from_path('m/48h/0h/0h/1h')
        Ypub = convert_xpub_prefix(xpub, b'\x02\x95\xb4\x3f')
        xpubs += "[%s/48'/0'/0'/1']%s\n" % (master_fpr, Ypub)
        # Multisig native Segwit
        xpub = bip32.get_xpub_from_path('m/48h/0h/0h/2h')
        Zpub = convert_xpub_prefix(xpub, b'\x02\xaa\x7e\xd3')
        xpubs += "[%s/48'/0'/0'/2']%s\n" % (master_fpr, Zpub)
        # Testnet nested Segwit
        xpub = bip32.get_xpub_from_path('m/49h/1h/0h')
        upub = convert_xpub_prefix(xpub, b'\x04\x4a\x52\x62')
        xpubs += "[%s/49'/1'/0']%s\n" % (master_fpr, upub)
        # Testnet native Segwit
        xpub = bip32.get_xpub_from_path('m/84h/1h/0h')
        vpub = convert_xpub_prefix(xpub, b'\x04\x5f\x1c\xf6')
        xpubs += "[%s/84'/1'/0']%s\n" % (master_fpr, vpub)
        # Testnet multisig nested Segwit
        xpub = bip32.get_xpub_from_path('m/48h/1h/0h/1h')
        Upub = convert_xpub_prefix(xpub, b'\x02\x42\x89\xef')
        xpubs += "[%s/48'/1'/0'/1']%s\n" % (master_fpr, Upub)
        # Testnet multisig native Segwit
        xpub = bip32.get_xpub_from_path('m/48h/1h/0h/2h')
        Vpub = convert_xpub_prefix(xpub, b'\x02\x57\x54\x83')
        xpubs += "[%s/48'/1'/0'/2']%s\n" % (master_fpr, Vpub)
        keys, failed = Key.parse_xpubs(xpubs)
        if len(failed) > 0:
            # TODO: This should never occur, but just in case, we must make sure to catch it properly so it doesn't crash the app no matter what.
            raise Exception("Failed to parse these xpubs:\n" + "\n".join(failed))
        else:
            self.add_keys(keys)

    def _load_wallet(self, wallet_manager):
        existing_wallets = [w["name"] for w in wallet_manager.cli.listwalletdir()["wallets"]]
        loaded_wallets = wallet_manager.cli.listwallets()
        not_loaded_wallets = [w for w in existing_wallets if w not in loaded_wallets]
        if os.path.join(wallet_manager.cli_path + "_hotstorage", self.alias) in existing_wallets:
            if os.path.join(wallet_manager.cli_path + "_hotstorage", self.alias) in not_loaded_wallets:
                wallet_manager.cli.loadwallet(os.path.join(wallet_manager.cli_path + "_hotstorage", self.alias))

    def create_psbts(self, base64_psbt, wallet):
        # Load the wallet if not loaded
        self._load_wallet(wallet.manager)
        cli = wallet.manager.cli.wallet(os.path.join(wallet.manager.cli_path + "_hotstorage", self.alias))
        print(cli.walletprocesspsbt(base64_psbt))
        return { 'core': cli.walletprocesspsbt(base64_psbt)['psbt'] }


# From https://github.com/trezor/python-mnemonic/blob/ad06157e21fc2c2145c726efbfdcf69df1350061/mnemonic/mnemonic.py#L246
import hashlib, hmac
# Refactored code segments from <https://github.com/keis/base58>
def b58encode(v: bytes) -> str:
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

    p, acc = 1, 0
    for c in reversed(v):
        acc += p * c
        p = p << 8

    string = ""
    while acc:
        acc, idx = divmod(acc, 58)
        string = alphabet[idx : idx + 1] + string
    return string
# We need to copy it like this because HWI uses it as a dependency, but requires v0.18 which doesn't have this function.
def seed_to_hd_master_key(seed, testnet=False) -> str:
    if len(seed) != 64:
        raise ValueError("Provided seed should have length of 64")

    # Compute HMAC-SHA512 of seed
    seed = hmac.new(b"Bitcoin seed", seed, digestmod=hashlib.sha512).digest()

    # Serialization format can be found at: https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki#Serialization_format
    xprv = b"\x04\x88\xad\xe4"  # Version for private mainnet
    if testnet:
        xprv = b"\x04\x35\x83\x94"  # Version for private testnet
    xprv += b"\x00" * 9  # Depth, parent fingerprint, and child number
    xprv += seed[32:]  # Chain code
    xprv += b"\x00" + seed[:32]  # Master key

    # Double hash using SHA256
    hashed_xprv = hashlib.sha256(xprv).digest()
    hashed_xprv = hashlib.sha256(hashed_xprv).digest()

    # Append 4 bytes of checksum
    xprv += hashed_xprv[:4]

    # Return base58
    return b58encode(xprv)