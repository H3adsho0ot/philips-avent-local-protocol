# Experimental SCD973 handshake diagnostic

[Download the Python script](https://raw.githubusercontent.com/H3adsho0ot/philips-avent-scd923-26-local-protocol/main/tools/avent_handshake_diagnostic.py)
and save it as `avent_handshake_diagnostic.py`. This one file is sufficient.
It requires **Python 3.10 or newer**, with no additional packages or Home Assistant.

The profile is based on the contributor report in [issue #1](https://github.com/H3adsho0ot/philips-avent-scd923-26-local-protocol/issues/1).
It is a diagnostic aid, **not working SCD973 support**. Its key wrapping still
uses the legacy SCD923 cipher as an unverified hypothesis. A login reply or
an observed message does not validate the pairing key.

## Run a test

Choose a suitable time: a new session may interrupt the handheld or another
viewer. Run against a camera you own or are authorised to test, from a computer
that can reach it on the local network. The tool does not configure Wi-Fi.

Open a terminal in the folder containing the downloaded file:

```console
python avent_handshake_diagnostic.py CAMERA_IP
```

On Windows, `py -3` can be used in place of `python`. On systems where Python 3
is named `python3`, use that command instead.

Enter `base64:` followed by the QR code's `pd` value at the hidden prompt.
The decoded key must be exactly 16 bytes. Existing 16-character ASCII keys and
`hex:` followed by the hexadecimal encoding of 16 bytes are also accepted.
Do not put the key in a command argument or a public issue. The tool refuses
to continue if the terminal cannot provide hidden key entry.

The default `scd973-001` profile uses the reported `0010` plus NUL login trailer.
For an explicit, separate comparison with the legacy `0` plus NUL trailer:

```console
python avent_handshake_diagnostic.py CAMERA_IP --profile legacy
```

Each run opens one TCP-6000 connection and sends **one login**. It then only
receives; there are no guessed challenge answers, setting changes, discovery,
media, microphone, light, music, reset or update requests. The receive phase
ends after both reported message types are seen, 64 frames, an eight-second
deadline, or a connection/protocol error. Socket connection establishment has
a separate five-second timeout; idle reads can end the run sooner.

## Share the result

The JSON report contains only direction, complete 16-bit opcode, sequence
number, frame/body lengths, message order, and fixed outcome labels. It
contains no packet bodies, pairing/session keys, challenge values, camera
addresses or device identifiers. The key is not printed or written to disk.
`authenticated` is **always false**.

Copy the generated JSON report into the issue. Share any separate native
captures or keys only through an agreed private channel, not with this report.
An empty result or missing marker does not prove that the key is wrong.

Exit codes:

- `0`: at least one reported SCD973 marker was observed; **not authentication success**.
- `1`: no such marker was observed, including timeout or connection failure.
- `2`: invalid key input, unavailable hidden input, or cancellation at the prompt.

This diagnostic cannot reconstruct a native handheld handshake or determine
the unknown response/key derivation from header metadata alone.

## Offline checks and license

From a repository checkout, run the synthetic tests without contacting a camera:

```console
python -m unittest discover -s tests -p test_handshake_diagnostic.py -v
```

The script is an independent Python implementation derived from the local
Avent local 0.5.3b1 diagnostic modules. It includes no manufacturer source code,
firmware or real credentials. The tool is provided under the [MIT license](LICENSE).
