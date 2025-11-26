# Voice Announcements Needed for OracleBox

The following voice announcement files need to be created in the same voice as "welcome_to_oraclebox.wav" and uploaded to the Raspberry Pi:

## Required Voice Files

1. **choose_method.wav**
   - Text: "Choose Your Investigation Method"
   - Plays when: User reaches mode selection page after connection
   - Tone: Neutral, instructional

2. **spirit_box.wav**
   - Text: "Spirit Box"
   - Plays when: User taps Spirit Box card
   - Tone: Clear announcement

3. **rempod.wav**
   - Text: "REM Pod"
   - Plays when: User taps REM Pod card
   - Tone: Clear announcement

4. **music_box.wav**
   - Text: "Music Box"
   - Plays when: User taps Music Box card
   - Tone: Clear announcement

## Upload Instructions

1. Record all four voice files using the same voice actor and settings as the welcome sound
2. Save as .wav files with the exact names listed above
3. Upload to Raspberry Pi using the app's Device Settings page:
   - Go to Mode Selection → Device Settings
   - Use "UPLOAD SOUND" button for each file
   - Files will be stored in `/home/pi/oraclebox_sounds/` on the Pi

## App Flow with Voice

```
1. App Launch
   ↓
2. Connection Page → Auto-connect or manual selection
   ↓ (plays "welcome_to_oraclebox.wav")
3. Mode Selection Page
   ↓ (plays "choose_method.wav")
   User taps mode card
   ↓ (plays "spirit_box.wav", "rempod.wav", or "music_box.wav")
4. Mode Page
   ↓ User presses start button
   - Spirit Box: "START SPIRIT BOX" button → begins sweep
   - REM Pod: "ARM REM POD" button → arms sensor
   - Music Box: "START MUSIC BOX" button → activates detection
```

## Notes

- All voice files should match the vintage radio theme
- Keep announcements brief and clear
- Consistent volume levels across all files
- Sample rate: 44.1kHz recommended
- Format: WAV, mono or stereo
