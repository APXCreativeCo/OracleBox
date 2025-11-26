# OracleBox FX Preset System

## Overview

The OracleBox now supports **named portal mode presets** in addition to manual FX slider control. This gives you one-tap access to curated audio processing profiles optimized for different use cases.

## Architecture

### Preset Categories

**SB7 Modes** - Optimized for external SB7 spirit box input:
- `SB7_CLASSIC` - The baseline balanced portal mode (your original settings)
- `SB7_DEEP_GATE` - Narrow band-pass, high contrast for tight gated sound
- `SB7_HALL_PORTAL` - Large reverb space with cavernous effect
- `SB7_WHISPER` - Soft gains, low contrast for subtle distant voices
- `SB7_ROUGH_SCAN` - Wider band-pass, higher contrast for raw noisy texture

**Built-In FM Modes** - Optimized for TEA5767 FM tuner sweep:
- `FM_RAW_PORTAL` - Moderate processing, good starting point
- `FM_DEEP_SPIRIT` - Narrow band-pass, heavy reverb for ethereal sound
- `FM_WIDE_OPEN` - Very wide band-pass, less reverb for raw radio content
- `FM_EVP_FOCUS` - Very narrow band-pass for short sharp EVP captures

### Custom Mode

When you manually adjust any FX slider via `FX SET` commands, the preset automatically changes to `CUSTOM`. This indicates the current settings don't match any named preset.

## Bluetooth Protocol Commands

### List Available Presets
```
FX PRESET LIST
```
**Response:**
```
OK FX PRESET LIST [{"name":"SB7_CLASSIC","category":"SB7","description":"..."},...}]
```

### Apply a Preset
```
FX PRESET SET <NAME>
```
**Example:**
```
FX PRESET SET SB7_CLASSIC
```
**Response:**
```
OK FX PRESET SET SB7_CLASSIC
```

### Get Current Preset Status
```
FX PRESET STATUS
```
**Response:**
```
OK FX PRESET STATUS {"enabled":true,"preset":"SB7_CLASSIC","bp_low":500,...}
```

### Existing Commands Still Work
All existing FX commands continue to work unchanged:
- `FX STATUS` - Now includes `"preset"` field
- `FX ENABLE` / `FX DISABLE`
- `FX SET <param> <value>` - Automatically sets preset to "CUSTOM"

## Android App Implementation Guide

### Recommended UI Layout

```
┌─────────────────────────────────────┐
│  FX Enable Toggle: [●━━━━━━━━] ON   │
├─────────────────────────────────────┤
│  [  SB7 Modes  ] [  FM Modes  ]     │  <- Tabs
├─────────────────────────────────────┤
│                                     │
│  SB7 MODES:                         │
│  ┌─────────────────┐                │
│  │  SB7 Classic    │ ← Currently    │
│  └─────────────────┘    selected    │
│  ┌─────────────────┐                │
│  │  Deep Gate      │                │
│  └─────────────────┘                │
│  ┌─────────────────┐                │
│  │  Hall Portal    │                │
│  └─────────────────┘                │
│  ┌─────────────────┐                │
│  │  Whisper        │                │
│  └─────────────────┘                │
│  ┌─────────────────┐                │
│  │  Rough Scan     │                │
│  └─────────────────┘                │
│                                     │
├─────────────────────────────────────┤
│  FINE TUNE (Manual Sliders)         │
│  ⚠ Adjusting sliders → CUSTOM mode │
│                                     │
│  Band-Pass Low:  [━━━●━━━━] 500 Hz │
│  Band-Pass High: [━━━━━●━━] 2600 Hz│
│  Reverb Room:    [━━●━━━━━] 35     │
│  Contrast:       [━━●━━━━━] 20     │
│  Post Gain:      [━━━━●━━━] 8 dB   │
│  (etc...)                           │
└─────────────────────────────────────┘
```

### State Management

**ViewModel State:**
```kotlin
data class FxPresetState(
    val currentPreset: String = "SB7_CLASSIC",  // or "CUSTOM"
    val availablePresets: List<PresetInfo> = emptyList(),
    val parameters: FxParameters = FxParameters()
)

data class PresetInfo(
    val name: String,
    val category: String,  // "SB7" or "FM"
    val description: String
)
```

**On App Launch:**
1. Send `FX PRESET LIST` to get available presets
2. Send `FX STATUS` to get current preset and parameters
3. Populate UI with preset buttons and slider values

**When User Taps Preset Button:**
1. Send `FX PRESET SET <NAME>\n`
2. On `OK` response, send `FX STATUS` to refresh UI
3. Update sliders to reflect new values
4. Highlight the selected preset button

**When User Adjusts Slider:**
1. Send `FX SET <PARAM> <VALUE>\n`
2. Preset automatically becomes "CUSTOM"
3. Update "Custom" indicator in UI
4. Un-highlight all preset buttons

**Preset Button Visual States:**
- **Selected:** Bold text, colored background
- **Available:** Normal text, default background
- **Custom Mode:** Special "Custom" badge visible, no preset highlighted

### Example Android Code Flow

```kotlin
// Loading presets
fun loadPresets() {
    viewModelScope.launch {
        val response = repository.sendCommand("FX PRESET LIST")
        if (response.isOk) {
            val json = response.raw.removePrefix("OK FX PRESET LIST")
            val presets = parsePresetList(json)
            _presetState.value = _presetState.value?.copy(
                availablePresets = presets
            )
        }
    }
}

// Applying preset
fun applyPreset(presetName: String) {
    viewModelScope.launch {
        val response = repository.sendCommand("FX PRESET SET $presetName")
        if (response.isOk) {
            // Refresh to get new parameter values
            loadFxStatus()
        }
    }
}

// Manual slider adjustment
fun updateBandpass(lowHz: Int, highHz: Int) {
    viewModelScope.launch {
        repository.fxSet("BP_LOW", lowHz)
        repository.fxSet("BP_HIGH", highHz)
        // Preset is now CUSTOM - refresh to confirm
        loadFxStatus()
    }
}
```

### UI Components

**Preset Button Click Handler:**
```kotlin
PresetButton(
    preset = presetInfo,
    isSelected = (currentPreset == presetInfo.name),
    onClick = { viewModel.applyPreset(presetInfo.name) }
)
```

**Slider Change Handler:**
```kotlin
Slider(
    value = bpLow.toFloat(),
    enabled = fxEnabled,  // Disable when FX is off
    onValueChange = { value ->
        viewModel.updateBandpass(value.toInt(), bpHigh)
    }
)
```

## Persistence

The current preset name is saved to `oraclebox_fx_config.json` along with all FX parameters:

```json
{
  "enabled": true,
  "preset": "SB7_CLASSIC",
  "bp_low": 500,
  "bp_high": 2600,
  ...
}
```

On OracleBox restart:
- FX system loads the last-used preset name and parameters
- If preset was "CUSTOM", it loads the custom values
- FX thread applies these settings when enabled

## Parameter Reference

Each preset defines these 9 parameters:

| Parameter | Range | Description |
|-----------|-------|-------------|
| `bp_low` | 100-2000 Hz | Band-pass filter low cutoff |
| `bp_high` | 1000-5000 Hz | Band-pass filter high cutoff |
| `reverb_room` | 0-100 | Reverb room size |
| `reverb_damping` | 0-100 | Reverb high-frequency damping |
| `reverb_wet` | 0-100 | Reverb wet signal level |
| `reverb_dry` | 0-100 | Reverb dry signal level |
| `contrast_amount` | 0-40 | Audio contrast enhancement |
| `pre_gain_db` | -24 to 0 dB | Pre-processing gain |
| `post_gain_db` | 0 to 18 dB | Post-processing gain |

## Migration Notes

**Backwards Compatibility:**
- All existing `FX` commands work exactly as before
- Existing apps that don't use presets will continue to function
- `FX STATUS` now includes `"preset"` field (defaults to "SB7_CLASSIC")
- Manual `FX SET` commands automatically set preset to "CUSTOM"

**Testing Checklist:**
1. ✅ Preset buttons apply correct values
2. ✅ Manual slider adjustment switches to CUSTOM
3. ✅ FX toggle disables sliders (existing behavior)
4. ✅ Preset persists across app restarts
5. ✅ Multiple preset switches work correctly
6. ✅ CUSTOM mode shows correct values
