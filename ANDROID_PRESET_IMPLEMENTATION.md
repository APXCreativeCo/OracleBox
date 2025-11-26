# Android App Preset Implementation Summary

## What Was Added

### Backend (Python - oraclebox_merged.py)
✅ Complete - See FX_PRESET_SYSTEM.md for details

### Frontend (Android App)

#### 1. BluetoothRepository.kt
Added three new methods:
```kotlin
suspend fun fxPresetList(): OracleBoxResponse
suspend fun fxPresetStatus(): OracleBoxResponse  
suspend fun fxPresetSet(presetName: String): OracleBoxResponse
```

#### 2. ControlViewModel.kt
**New State:**
- Added `preset: String` field to `FxUiState`
- Added `FxPreset` data class
- Added `_fxPresets` LiveData to hold available presets

**New Methods:**
- `loadFxPresets()` - Fetches preset list from OracleBox
- `applyFxPreset(presetName: String)` - Applies a preset and reloads FX status

**Updated Methods:**
- `loadFxStatus()` - Now reads and stores `preset` field from response

#### 3. activity_control.xml
**Added UI Elements:**
- `text_current_preset` (TextView) - Displays current preset name
- `button_select_preset` (Button) - Opens preset selection dialog

**Layout:**
```
[FX Enabled] [Switch]
[Current Preset:] [SB7_CLASSIC]  ← Shows current preset
[Select Preset...] ← Opens dialog
[Sliders...]
```

#### 4. ControlActivity.kt
**New Views:**
- `textCurrentPreset` - Shows current preset
- `buttonSelectPreset` - Triggers preset dialog

**New Logic:**
- `showPresetDialog()` - Displays categorized preset selection
  - Groups presets into "SB7 MODES" and "FM MODES"
  - Shows user-friendly names (e.g., "CLASSIC" instead of "SB7_CLASSIC")
  - Applies selected preset via ViewModel

**Updated Observers:**
- FX state observer now:
  - Updates preset display text
  - Disables preset button when FX is off
  - Colors "CUSTOM" preset orange to distinguish it

**Initialization:**
- Added `viewModel.loadFxPresets()` on startup

## How It Works

### User Flow

1. **App Startup:**
   - Loads FX status (includes current preset)
   - Loads available presets from OracleBox
   - Displays current preset name

2. **Selecting a Preset:**
   - User taps "Select Preset..." button
   - Dialog shows with two sections:
     - SB7 MODES (5 presets)
     - FM MODES (4 presets)
   - User selects a preset
   - App sends `FX PRESET SET <NAME>` command
   - OracleBox applies preset, restarts SoX
   - App reloads FX status to show new values
   - Sliders update to reflect new parameters

3. **Manual Slider Adjustment:**
   - User moves any FX slider
   - App sends `FX SET <PARAM> <VALUE>` command
   - OracleBox automatically sets preset to "CUSTOM"
   - Preset display updates to "CUSTOM" (shown in orange)

4. **FX Toggle Behavior:**
   - When FX is OFF:
     - Sliders are disabled (gray)
     - Preset button is disabled
     - Passthrough mode active (raw FM audio)
   - When FX is ON:
     - Sliders are enabled
     - Preset button is enabled
     - SoX processes audio with current preset/parameters

## Available Presets

### SB7 Modes (External Spirit Box)
1. **CLASSIC** - Baseline balanced mode
2. **DEEP GATE** - Narrow, gated, high contrast
3. **HALL PORTAL** - Large reverb space
4. **WHISPER** - Soft, subtle, distant
5. **ROUGH SCAN** - Wide, raw, noisy

### FM Modes (Built-In TEA5767)
1. **RAW PORTAL** - Balanced FM processing
2. **DEEP SPIRIT** - Narrow, heavy reverb
3. **WIDE OPEN** - Very wide band-pass
4. **EVP FOCUS** - Narrow for short EVPs

## Visual Indicators

- **Normal Preset:** Preset name shown in accent color
- **CUSTOM Mode:** Preset name shown in orange
- **Disabled State:** All controls grayed when FX is off

## Testing Checklist

- [ ] Preset list loads on app start
- [ ] Current preset displays correctly
- [ ] "Select Preset..." button opens dialog
- [ ] Dialog shows SB7 and FM sections
- [ ] Selecting a preset applies it
- [ ] Sliders update after preset applied
- [ ] Moving slider changes preset to "CUSTOM"
- [ ] CUSTOM shows in orange color
- [ ] Preset button disabled when FX is off
- [ ] Preset persists across app restarts
- [ ] All 9 presets are selectable

## Backwards Compatibility

- Existing FX slider functionality unchanged
- Manual parameter adjustment still works
- FX enable/disable still works
- Older OracleBox without presets will show "SB7_CLASSIC" as default
