# Philips Avent SCD923/26 baby monitor: local protocol and QR pairing

Independent interoperability research · 1 November 2026

This paper describes how the Philips Avent SCD923/26 baby monitor pairs over Wi-Fi, establishes an encrypted local session and streams video over RTSP. It documents the handheld's QR pairing screen and the protocol behavior observed during development of a local Home Assistant prototype.

## Abstract

The SCD923/26 supports a local connection between its handheld parent unit and baby unit. Examination of a user-owned handheld's firmware, followed by an independent client implementation, enabled live video, room audio, intelligible talkback and device controls without a manufacturer account in the tested local setup. The connection combines proprietary session establishment with RTSP video and separate audio channels. A normal RTSP player cannot reproduce the complete exchange on its own.

On the same handheld, a pairing dialog displays a QR code containing newly generated direct Wi-Fi credentials. A photograph of the display yielded both the network name and the 16-character password. Presenting the code to the baby unit produced no visible response in the owner's attempt. Camera acceptance and a complete new pairing remain open questions. These findings concern one SCD923/26 set and the firmware examined.

## Method and evidence

The investigation combined analysis of the handheld application's behavior, offline protocol comparisons, and local interoperability tests against the paired baby unit. For the pairing dialog, isolated ARM emulation exercised the handheld's button and UI routines with synthetic credentials. Device I/O, networking and persistent writes were intercepted. A separate observation used a photograph of the real handheld display.

Evidence is distinguished below as **observed** for behavior exercised on the device, **reconstructed** for behavior inferred from the handheld firmware, and **unresolved** where the available evidence is insufficient. The diagram is a reconstruction of the original handheld's logical exchange, not a captured packet trace. Initial pairing and Wi-Fi provisioning are outside its scope.

## Handheld connection sequence

![Reconstructed handheld and baby unit communication, from discovery and session establishment to video, audio and optional talkback](figures/handheld-sequence.png)

The handheld loads its stored pairing material and prepares a 16-byte session key. It sends the session key protected by the pairing key over the control connection, then exchanges encrypted identity and device information. A login acknowledgement alone is insufficient to demonstrate that the key is correct; successfully decrypting a meaningful device-information reply provides a stronger interoperability check.

The media connections run alongside the control session. Video arrives as H.264 over RTP interleaved in a TCP RTSP connection. Selected blocks within video payloads are encrypted. The receiver must decrypt those blocks before reconstructing and decoding the H.264 stream. Room audio and talkback use ADPCM with their own framing and encryption handling.

| Channel | Transport | Role and evidence |
| --- | --- | --- |
| Discovery | UDP 6100 | Broadcast query containing the paired camera's SSID. Reconstructed and tested with simulated replies. Live PC queries received no reply. |
| Control | TCP 6000 | Session establishment, commands, replies and status events; observed |
| Video | TCP 554 | RTSP endpoint `/av2_0`, carrying H.264 over interleaved RTP; observed |
| Room audio | TCP 8687 | Separate incoming audio connection in the tested setup; observed |
| Talkback | TCP 8686 | Microphone audio sent to the baby unit; observed |
| Secondary connection | TCP 8684 | Additional authenticated exchange; reproduced, but its complete purpose remains unresolved |

Discovery is reconstructed as a UDP query to the local broadcast address. The handheld uses the reply's source address to update its camera destination before the pairing-key exchange. Live queries from a PC yielded no response with either automatic interface selection or an explicit Ethernet binding. Rediscovery after an address change remains unverified.

## Pairing material and encryption

In the examined pair, the stored direct-Wi-Fi password also supplies the 16-byte pairing key used to protect the session key. The session key then protects application traffic. The implementation uses an AES-derived variant; treating it as an ordinary AES-ECB interface was not sufficient for interoperability.

The handheld has a separate path for **re-pairing**. It generates a new direct network name from a modified representation of the WLAN MAC address and produces a 16-character password using a clock-seeded pseudorandom generator. It uses that password to wrap the session key. The session-key generator also uses clock-seeded randomness. The analysis does not quantify entropy or demonstrate practical key prediction. The source of the original factory pairing and possible secret reuse across units remain unknown.

## Re-pairing from the handheld display

![Handheld photograph with a synthetic QR on the display. The MODE button has a rectangular symbol on the housing edge. The round Menu button has three horizontal lines below the directional pad.](figures/handheld-pairing.jpg)

**Observed on the handheld.** The owner photographed the pairing screen and identified both physical controls. Decoding the original photograph locally yielded a JSON object. Its three fields were `dev` (the handheld type, `pu`), `ssid` (the newly generated direct network name) and `passwd` (the new 16-character password). The figure uses the owner's photograph with the display replaced. Scanning the published figure returns the values in the [synthetic JSON example](examples/handheld-qr.json).

**Reconstructed on the handheld.** From the video or mode view, holding **MODE and Menu together for about ten seconds** opens the pairing dialog. MODE is the elongated edge button beside a rectangle. Menu is the separate round button marked ≡ below the directional pad. The ten-second threshold comes from the application and was reproduced with simulated button presses.

| Stage | Effect on the handheld |
| --- | --- |
| Dialog opens | The handheld generates new credentials, requests a switch to direct Wi-Fi if needed and starts connecting with the new values. Monitoring can therefore be interrupted as soon as the code appears. |
| Pairing succeeds | After an initial five-second delay, the dialog checks both WLAN connection status and a success flag set during device-information reply handling. When both conditions hold, it copies the new values into the saved pairing settings and requests persistent writes. |
| Pairing is still pending | A short press and release of **OK**, or expiry of the **five-minute** timeout, restores the old handheld credentials and starts a connection attempt with them. Reopening the dialog generates a fresh pair. |

**Observed at the baby unit, outcome unresolved.** The owner reported no visible response when presenting the QR code to the camera. This leaves open how the baby unit enters a scanning state, whether it read the code in that attempt, and when it would save new credentials. The recovery path above was reconstructed on the handheld only. Whether the camera retains its home-network connection after successful re-pairing is also unknown.

A photograph therefore provides the credentials for the **current pairing attempt**. An end-to-end Home Assistant setup from that photograph would also require the camera to adopt those credentials, remain reachable, and complete an authenticated device-information exchange with the client. That sequence has yet to be demonstrated.

## Features and implementation lessons

The reconstructed controls cover the nightlight and brightness, built-in sounds and playback volume, timers, temperature reporting and alert settings, Wi-Fi reception, microphone sensitivity and talkback. A local Home Assistant prototype exposes these capabilities. Its image-change detector is calculated from decoded video; it must not be described as a recovered native camera motion event.

Several details materially affected interoperability:

- **Session setup is stateful.** Repeating the identity/device-information setup request as a polling operation caused media connections to close in the tested setup.
- **Silence is not necessarily a fault.** Native sensitivity settings can suppress quiet room audio. Closing an apparently idle audio connection also disrupted video during development.
- **Talkback needs the correct codec state.** The reconstructed format uses 16 kHz mono audio in 40 ms blocks with an IMA ADPCM step index carried between blocks. Offline packet comparisons and a listener's confirmation of intelligible speech supported the implementation. Simultaneous listening and speaking are not yet established as reliable full-duplex operation.
- **Native clients can compete.** The handheld and the independent client interfered with one another in testing. In the installed integration, multiple Home Assistant views share one native session. Device testing confirmed that the integration releases its native connections ten seconds after the last viewer leaves. Simultaneous operation with the handheld remains unverified.
- **Privacy mode affects reachability.** Activating the native privacy setting made the baby unit unreachable on the LAN during a longer test. Remote reversal was then unavailable. It should not be presented as a harmless local display toggle.

## Scope and open questions

The local path worked without a manufacturer account or cloud connection being used by the independent client. This does not characterize every network connection made by the product or replace an audit of its cloud services.

Further work should establish discovery behavior on real networks, compatibility across firmware revisions, the purpose of the secondary connection, full-duplex audio behavior, and the conditions under which multiple native clients can coexist. Firmware-update distribution and the original provisioning of pairing secrets are outside the confirmed results.

The practical result is local interoperability with an already-paired device whose owner has its pairing material. It is not evidence of unauthenticated access to arbitrary cameras.

## Legal notice

This is independent interoperability research for educational and informational purposes. It is not affiliated with, endorsed by, or sponsored by Philips or any other product manufacturer. Philips, Avent and other product names are trademarks of their respective owners and are used only to identify the equipment discussed.

The publication includes original explanatory text and diagrams, an owner-supplied photograph with a substituted display, independently drawn button symbols and synthetic example data. It does not distribute manufacturer firmware, manufacturer source code, extracted artwork, actual device credentials or recovered cryptographic keys. No rights to third-party software, trademarks or other protected material are granted by this publication.

Any implementation or testing based on these findings must be limited to equipment and networks that you own or are authorized to access, and must comply with applicable law and third-party rights. This publication does not authorize access to another person's devices or communications.

The findings are provided as is, without warranties of accuracy, completeness, compatibility, security or fitness for a particular purpose, to the extent permitted by applicable law. Experimental integrations should not be relied upon as the sole means of monitoring a child or for any safety-critical purpose.
