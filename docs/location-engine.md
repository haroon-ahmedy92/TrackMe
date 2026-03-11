# Location Engine Guide

This document explains how TrackMe handles location.

The most important thing to understand is this:

TrackMe does not promise perfect or always-exact tracking.

Instead, it combines several lawful signals, scores how trustworthy they are, and labels the result honestly.

## Main Goal

The location engine is trying to answer:

"What is the best lawful location evidence we have right now?"

That is different from asking:

"Do we have any coordinates at all?"

## Where the Code Lives

Important files:

- [`LocationFusionEngine.kt`](../app/src/main/java/com/example/trackme/location/LocationFusionEngine.kt)
- [`LocationConfidenceScorer.kt`](../app/src/main/java/com/example/trackme/location/LocationConfidenceScorer.kt)
- [`LocationSpoofingDetector.kt`](../app/src/main/java/com/example/trackme/location/LocationSpoofingDetector.kt)
- [`FusedDeviceLocationProvider.kt`](../app/src/main/java/com/example/trackme/location/FusedDeviceLocationProvider.kt)
- [`NetworkContextCollector.kt`](../app/src/main/java/com/example/trackme/location/NetworkContextCollector.kt)
- [`MotionContextProvider.kt`](../app/src/main/java/com/example/trackme/location/MotionContextProvider.kt)
- [`GeofenceEventContextProvider.kt`](../app/src/main/java/com/example/trackme/location/GeofenceEventContextProvider.kt)
- [`IpApproximateLocationProvider.kt`](../app/src/main/java/com/example/trackme/location/IpApproximateLocationProvider.kt)
- [`WifiRttCapabilityChecker.kt`](../app/src/main/java/com/example/trackme/location/WifiRttCapabilityChecker.kt)

## Signals Used

The engine currently works with several lawful signals:

- fused location from Google Play Services
- last known GPS/provider location
- last known network-provider location
- recent geofence event context
- movement or activity context, when available
- network context such as connection type
- hashed Wi-Fi SSID/BSSID only when lawful and available
- approximate backend IP geolocation fallback

Each signal contributes evidence, but not all evidence is equal.

## Why Some Signals Are Stronger Than Others

### Fused and GPS location

These are usually the strongest candidates when:

- permissions are granted
- the sample is recent
- the reported accuracy is good

But even a GPS fix can be stale or suspicious, so it is not trusted blindly.

### Network-provider location

This can still be useful, but it is usually less precise than a strong GPS fix.

### Geofence events

A geofence event is not a full replacement for a location fix. It is supporting context.

Example:

- if the device recently exited a known geofence, that may make a nearby sample more believable

### Motion/activity context

Motion context helps explain whether the device appears:

- still
- walking
- in vehicle
- unknown

This does not directly give coordinates, but it helps interpret the evidence.

### Wi-Fi context

Wi-Fi details can provide useful network context, but they do not automatically mean a precise location. In this project, SSID/BSSID values are hashed when collected, and only used when lawful and available.

### IP geolocation

This is fallback evidence only.

It may reflect:

- a city
- a network region
- a carrier gateway

It must never be presented as exact device location.

## Precision Labels

TrackMe uses three precision classes:

- `precise`
- `moderate`
- `approximate`

This matters because a recovery operator should not have to guess how strong the evidence is.

Example:

- a fresh fused fix with good accuracy might be `precise`
- a weaker network fix may be `moderate`
- an IP-only estimate must remain `approximate`

## How Confidence Scoring Works

The confidence score answers:

"How much should we trust this sample compared with the other samples available right now?"

The score is influenced by:

- accuracy in meters
- freshness
- source type
- whether the sample is approximate
- geofence support
- motion support
- suspicious mock-location indicators
- integrity trust metadata

### Simple mental model

For a beginner, use this rule:

- fresh is better than stale
- accurate is better than vague
- multiple supporting signals are better than one weak signal
- approximate sources reduce confidence
- suspicious spoofing signs reduce confidence

## Why IP and Tower Methods Are Approximate

This point is important enough to repeat.

IP and tower-derived estimates do not directly measure where the device is standing. They infer an area from network infrastructure.

That means the result may describe:

- the city
- a district
- a carrier egress point
- a radio coverage area

It is useful context, but it is not exact recovery evidence.

## Stale Last Known Location

Last known location can help, but it can also mislead.

Example:

- yesterday the device had a strong GPS fix
- today the device is offline
- the old fix is still stored

That does not mean the device is still there.

So the engine reduces confidence when a sample is old.

## Mock Location and Spoofing Heuristics

The engine includes basic spoofing heuristics in:

- [`LocationSpoofingDetector.kt`](../app/src/main/java/com/example/trackme/location/LocationSpoofingDetector.kt)

Examples of suspicious signals:

- Android reports the sample as mock
- the timestamp appears to be from the future
- movement looks unrealistic for the claimed accuracy

These heuristics do not prove fraud. They lower trust and help the backend raise suspicious alerts.

## Normal Mode vs Lost Mode

### Normal mode

Normal mode is designed for:

- lower power consumption
- lower bandwidth use
- routine check-ins

This is the right default for day-to-day operation.

### Lost mode

Lost mode is designed for:

- a higher reporting rate
- fresher evidence during an incident
- better recovery support

But it is still time-boxed. The app does not stay in permanent high-frequency tracking mode.

## Why Android Background Limits Matter

Android background rules affect the location engine directly.

The app cannot rely on endless high-frequency background updates. That is why the design uses:

- periodic work
- visible permission requests
- battery-aware scheduling
- escalation windows instead of permanent escalation

This keeps the app realistic for production Android behavior.

## What the Engine Produces

A location sample can include:

- latitude and longitude when available
- accuracy in meters
- timestamp
- source types used
- confidence score
- precision label
- battery level
- network type
- motion state
- suspicious/mock indicators

The backend then stores and evaluates that evidence further.

## Student Takeaway

The location engine is best understood as an evidence-ranking system.

It does not ask only:

- "Do we have a location?"

It asks:

- "How did we get it?"
- "How fresh is it?"
- "How accurate is it?"
- "How suspicious is it?"
- "Should we present it as precise, moderate, or approximate?"
