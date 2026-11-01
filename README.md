# Local communication in the Philips Avent SCD923/26

**A short interoperability research note · 1 November 2026**

## Abstract

The SCD923/26 supports a local connection between its handheld parent unit and baby unit. Examination of a user-owned handheld's firmware, followed by an independent client implementation, enabled live video, room audio, intelligible talkback and device controls without a manufacturer account in the tested local setup. The connection combines proprietary session establishment with RTSP video and separate audio channels. A normal RTSP player cannot reproduce the complete exchange on its own.

These findings concern one paired SCD923/26 set and the firmware examined. They do not establish compatibility with every firmware version or other Avent models. This note publishes descriptions and an original diagram only: no recovered keys, passwords, device identifiers, firmware binaries, disassembly or manufacturer source code.

## Method and evidence

The investigation combined analysis of the handheld application's behavior, offline protocol comparisons, and local interoperability tests against the paired baby unit.

Evidence is distinguished below as **observed** for behavior exercised on the device, **reconstructed** for behavior inferred from the handheld firmware, and **unresolved** where the available evidence is insufficient. The diagram is a reconstruction of the original handheld's logical exchange, not a captured packet trace. Initial pairing and Wi-Fi provisioning are outside its scope.

## Handheld connection sequence

![Reconstructed handheld and baby unit communication, from discovery and session establishment to video, audio and optional talkback](figures/handheld-sequence.png)

The handheld loads its stored pairing material and prepares a 16-byte session key. It sends the session key protected by the pairing key over the control connection, then exchanges encrypted identity and device information. A login acknowledgement alone is insufficient to demonstrate that the key is correct; successfully decrypting a meaningful device-information reply provides a stronger interoperability check.

The media connections run alongside the control session. Video arrives as H.264 over RTP interleaved in a TCP RTSP connection. Selected blocks within video payloads are encrypted. The receiver must decrypt those blocks before reconstructing and decoding the H.264 stream. Room audio and talkback use ADPCM with their own framing and encryption handling.

| Channel | Transport | Role and evidence |
| --- | --- | --- |
| Discovery | UDP 6100 | Broadcast query containing the paired camera's SSID; reconstructed, with simulated tests only |
| Control | TCP 6000 | Session establishment, commands, replies and status events; observed |
| Video | TCP 554 | RTSP endpoint `/av2_0`, carrying H.264 over interleaved RTP; observed |
| Room audio | TCP 8687 | Separate incoming audio connection in the tested setup; observed |
| Talkback | TCP 8686 | Microphone audio sent to the baby unit; observed |
| Secondary connection | TCP 8684 | Additional authenticated exchange; reproduced, but its complete purpose remains unresolved |

Discovery is reconstructed as a UDP query to the local broadcast address. The handheld uses the reply's source address to update its camera destination. This discovers an address; it does not replace the subsequent pairing-key exchange. A new discovery implementation has passed synthetic tests, but its real broadcast behavior has not yet been verified on the device.

## Pairing material and encryption

In the examined pair, the stored direct-Wi-Fi password also supplies the 16-byte pairing key used to protect the session key. The session key then protects application traffic. The implementation uses an AES-derived variant; treating it as an ordinary AES-ECB interface was not sufficient for interoperability.

This is a distinction between a persistent pairing secret and a session key, not a claim that every camera shares one secret. How the pairing secret is originally generated or provisioned, whether any units reuse it, and the quality of the handheld's session-key randomness remain unverified. A 16-byte key representation alone does not establish 128 bits of entropy. No brute-force recovery was required for this work, and no universal key is claimed.

## Features and implementation lessons

The reconstructed controls cover the nightlight and brightness, built-in sounds and playback volume, timers, temperature reporting and alert settings, Wi-Fi reception, microphone sensitivity and talkback. A local Home Assistant prototype exposes these capabilities. Its image-change detector is calculated from decoded video; it must not be described as a recovered native camera motion event.

Several details materially affected interoperability:

- **Session setup is stateful.** Repeating the identity/device-information setup request as a polling operation caused media connections to close in the tested setup.
- **Silence is not necessarily a fault.** Native sensitivity settings can suppress quiet room audio. Closing an apparently idle audio connection also disrupted video during development.
- **Talkback needs the correct codec state.** The reconstructed format uses 16 kHz mono audio in 40 ms blocks with an IMA ADPCM step index carried between blocks. Offline packet comparisons and a listener's confirmation of intelligible speech supported the implementation. Simultaneous listening and speaking are not yet established as reliable full-duplex operation.
- **Native clients can compete.** The handheld and the independent client interfered with one another in testing. Simultaneous independent native sessions are not confirmed. Releasing all camera connections when no viewer is present is the proposed integration strategy; the prepared on-demand update has passed software tests but awaits deployment validation.
- **Privacy mode affects reachability.** Activating the native privacy setting made the baby unit unreachable on the LAN during a longer test. Remote reversal was then unavailable. It should not be presented as a harmless local display toggle.

## Scope and open questions

The local path worked without a manufacturer account or cloud connection being used by the independent client. This does not characterize every network connection made by the product or replace an audit of its cloud services.

Further work should establish discovery behavior on real networks, compatibility across firmware revisions, the purpose of the secondary connection, full-duplex audio behavior, and the conditions under which multiple native clients can coexist. Firmware-update distribution and the original provisioning of pairing secrets are outside the confirmed results.

The practical result is local interoperability with an already-paired device whose owner has its pairing material. It is not evidence of unauthenticated access to arbitrary cameras.

## Legal notice

This is independent interoperability research for educational and informational purposes. It is not affiliated with, endorsed by, or sponsored by Philips or any other product manufacturer. Philips, Avent and other product names are trademarks of their respective owners and are used only to identify the equipment discussed.

This publication contains original explanatory text and an original diagram. It does not distribute manufacturer firmware, manufacturer source code, extracted artwork, device credentials or recovered cryptographic keys. No rights to third-party software, trademarks or other protected material are granted by this publication.

Any implementation or testing based on these findings must be limited to equipment and networks that you own or are authorized to access, and must comply with applicable law and third-party rights. This publication does not authorize access to another person's devices or communications.

The findings are provided as is, without warranties of accuracy, completeness, compatibility, security or fitness for a particular purpose, to the extent permitted by applicable law. Experimental integrations should not be relied upon as the sole means of monitoring a child or for any safety-critical purpose.
