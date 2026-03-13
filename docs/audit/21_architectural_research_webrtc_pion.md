# Audit Report 21: Experimental Extraction - WebRTC & P2P Protocols

**Date:** 2026-03-13  
**Auditor:** AntiGravity Expert Systems (Doctoral Level Research & Core Architecture)  
**Module:** `internal/webrtc` (Future R&D)

## 1. Executive Summary
The era of `HTTP-FLV` and `HLS (M3U8)` is sunsetting for ultra-low latency streams. Douyin heavily pushes **WebRTC (Real-Time Communication)** for interactive 1-to-many broadcasts and P2P (Peer-to-Peer) offloading to reduce their CDN costs ($100s of millions annually). 

Our current `douyinstream-go` V2.0.0 parses JSON to find `.flv` strings. This is functional today, but as ByteDance forces clients onto proprietary WebRTC signaling channels, the project must be ready to intercept RTP/RTCP packets directly.

## 2. The Theoretical Barrier (SDP Handshakes)
To extract a WebRTC stream, we cannot simply `GET` a URL. WebRTC requires a complex multi-stage "Signaling" negotiation to traverse NAT firewalls (ICE, STUN, TURN) and establish symmetric cryptography (DTLS).

A standard Douyin WebRTC broadcast URL might look like: `webrtc://live.douyin.com/room/...`
The client and server exchange **SDP (Session Description Protocol)** packets via JSON-RPC or Protobuf WebSockets. After establishing the parameters, the actual video (VP8/H.264) flows as raw UDP packets (RTP) between the Douyin Media Server and our Go client.

## 3. Architecture for WebRTC Dump
Fortunately, Golang boasts the world's finest WebRTC implementation: **`github.com/pion/webrtc`**. We can construct a completely headless P2P receiver.

```go
package webrtc_dvr

import (
    "github.com/pion/webrtc/v3"
    "github.com/pion/webrtc/v3/pkg/media/ivfwriter"
    "github.com/pion/webrtc/v3/pkg/media/h264writer"
)

// Concept: Our Go client explicitly answers the Douyin Signaling Server's SDP
func ConnectWebRTCStream(sdpOffer webrtc.SessionDescription) error { 
    // 1. Configure Pion WebRTC to behave exactly like mobile Douyin app
    peerConnection, err := webrtc.NewPeerConnection(webrtc.Configuration{ ... })
    
    // 2. We hook into incoming video tracks
    peerConnection.OnTrack(func(track *webrtc.TrackRemote, receiver *webrtc.RTPReceiver) {
        codec := track.Codec()
        if codec.MimeType == webrtc.MimeTypeH264 {
            // Start dumping raw H.264 Network packets instantly into a file
            videoWriter, _ := h264writer.New("douyin_live.h264")
            for {
                rtpPacket, _, _ := track.ReadRTP()
                videoWriter.WriteRTP(rtpPacket)
            }
        }
    })

    // 3. Complete the handshake
    peerConnection.SetRemoteDescription(sdpOffer)
    answer, _ := peerConnection.CreateAnswer(nil)
    peerConnection.SetLocalDescription(answer)
    
    // --> Send 'answer' back to Douyin via WebSocket, and let the UDP packets rain!
}
```

## 4. Why This is "Next-Generation" Scraping
1. **Unblockable CDNs:** When we connect via WebRTC, we often bypass standard HTTP Load Balancers entirely. The WebRTC media servers are frequently unmetered for bots because they operate on pure UDP flows, assuming the client doing the SDP handshake holds a valid session.
2. **Sub-second Latency:** If we ever pipe `douyinstream-go` output to a player like `mpv`, WebRTC parsing drops the latency from ~5 seconds (FLV buffering) down to **200 milliseconds**. We see the stream exactly when the streamer's phone camera captures it.

## 5. Implementation Complexity (High)
Reversing the SDP payload and the WebSocket signaling JSON requires intercepting Android SSL packets initially. However, once the protocol wrapper is defined in Go, the `pion/webrtc` library will handle all the heavy lifting of decrypting the DTLS keys seamlessly.
