"""Read-only validation of the GR III 2.20 WLAN/BLE patch."""
import argparse
from pathlib import Path
import sys

STOCK_SHA256 = "5c53760b3b564c87239dbf7f5c94d0f6fd91accd156ec4ba672ebfd6b861793e"
SITE = 0x3ED7E4
CONTEXT = bytes.fromhex("b400d3e1 104f6fe1 a442a0e1 000054e3 0700001a")
REPLACEMENT = bytes.fromhex("0140a0e3")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codec", required=True, type=Path,
                        help="Root of the gr-custom-tool checkout documented in README")
    parser.add_argument("stock", type=Path)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.codec.resolve()))
    from gr4_editor.codec.container import inspect_container, sum32
    from gr4_editor.codec.frames import decode_payload, section_rows

    stock = args.stock.read_bytes()
    candidate = args.candidate.read_bytes()
    stock_info = inspect_container(stock)
    candidate_info = inspect_container(candidate)
    if stock_info["sha256"] != STOCK_SHA256:
        raise ValueError("Stock BIN SHA-256 does not match the documented GR III 2.20 image.")
    if stock[:128] != candidate[:128] or stock[-24:-12] != candidate[-24:-12]:
        raise ValueError("Container header or footer identity fields differ.")

    def decode(data, info):
        decoded, _ = decode_payload(data[128:info["payload_end"]], info["decoded_size"])
        if info["additive_sum32"] != 0 or sum32(decoded) != 0:
            raise ValueError("Container or decoded payload checksum failed.")
        return decoded

    original = decode(stock, stock_info)
    modified = decode(candidate, candidate_info)
    if original.count(CONTEXT) != 1 or original.find(CONTEXT) + 8 != SITE:
        raise ValueError("Stock instruction context is not unique at the documented offset.")
    if section_rows(original) != section_rows(modified):
        raise ValueError("Decoded section layout differs.")
    expected = original[:SITE] + REPLACEMENT + original[SITE + 4:-4]
    if modified[:-4] != expected:
        raise ValueError("Decoded candidate differs from the expected single-instruction patch.")
    print("PASS: stock hash, instruction context, payload diff, layout and checksums")
    print(f"Candidate SHA-256: {candidate_info['sha256']}")
    print("Offline verification only. Flashability and wireless recovery require a camera test.")


if __name__ == "__main__":
    try:
        main()
    except (ImportError, OSError, ValueError) as error:
        sys.exit(f"FAIL: {error}")
