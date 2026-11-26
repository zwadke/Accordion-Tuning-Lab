# Accordion Tuning Lab — user guide

[Home](../README.md) · [Nederlands](Handleiding-NL.md)

## Getting started
Install the Windows release and launch the app. Use NL / EN to change language. Set a comfortable master volume and hold a test note at the bottom of the window. Choose Accordion for an accordion-like timbre or Sine + drawbars to adjust harmonics 2–5. Sine only resets the harmonic sliders.

## Profiles and reeds
Use Load next to one of the three slots to open a JSON profile; click its name to activate it. Celeste is a two-reed example. M is the reference reed, M+ and M− are independently adjustable. Enable Three-reed mode to reveal M− and the curve selector. Each reed has an on/off checkbox and level slider. The M− and M+ names do not restrict the sign of their tuning offsets.

## Editing
Select a curve and click or drag in the graph to edit it. For precise entry, select a note and enter its offset in Cents or Δ Hz, then press Enter. Arrow keys in the numerical fields move between notes. Copy copies the selected curve to the other adjustable reed; Mirror copies it with reversed sign. To convert a two-reed profile into a symmetric three-reed profile, select M+, click Mirror, and enable all three reeds.

The left axis shows signed cents relative to M; the right axis shows nonnegative beating rates in Hz. Show beating (Hz) toggles the pairwise curves. Δ Hz is a signed frequency offset, not necessarily the beating rate between two detuned reeds. F11 expands the graph; press again to restore controls.

## Reference pitch and saving
Enter A4 in Hz (400–480) and click Set. The first loaded profile supplies the initial reference; later profile changes retain the current reference. Save... creates a JSON profile. Update profile overwrites the active slot's file after confirmation. Save a separate copy before experimenting; switching slots can discard unsaved changes. Older two-reed JSON profiles can be loaded and saved in the newer format.

## MIDI
Connect a MIDI keyboard, click Refresh, choose its input port and click Connect. Close other MIDI applications if the port is unavailable. Alternatively, Open a MIDI file and use Play, Pause and Stop. All notes off silences stuck notes. Test buttons work without MIDI hardware.

## Examples
Measured_A435 contains two measured reed curves, with M disabled. The original measurements cover C4–B♭6; outside that range the endpoint offsets are repeated. Set A4 to 435 Hz to reproduce the intended reference if another profile was loaded first. The app is a simulator, not a microphone-based tuner.
